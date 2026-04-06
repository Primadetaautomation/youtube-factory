"""YouTube Factory — Local App Server.

Runs on user's PC. Handles yt-dlp downloads and FFmpeg processing locally.
AI calls (OpenAI, ElevenLabs, Gemini) are proxied through the Railway server.
"""
import asyncio
import base64
import logging
import sys
import json
import shutil
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import OUTPUT_DIR, TEMP_DIR

app = FastAPI(title="YouTube Factory")

# ── Proxy config ──────────────────────────────────────
PROXY_URL = os.getenv("PROXY_URL", "https://youtube-factory-production.up.railway.app")
_proxy_token: str | None = None


async def proxy_request(path: str, data: dict | None = None, method: str = "POST",
                        files: dict | None = None, form_data: dict | None = None):
    """Forward a request to the Railway proxy server."""
    import httpx

    headers = {}
    if _proxy_token:
        headers["Authorization"] = f"Bearer {_proxy_token}"

    url = f"{PROXY_URL}{path}"

    async with httpx.AsyncClient(timeout=180) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        elif files:
            resp = await client.post(url, headers=headers, files=files, data=form_data or {})
        else:
            resp = await client.post(url, headers=headers, json=data)

        if resp.status_code != 200:
            detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        return resp.json()


# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


# ── Auth (authenticates against proxy) ─────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
async def login_endpoint(req: LoginRequest):
    global _proxy_token
    result = await proxy_request("/api/auth/login", req.model_dump())
    _proxy_token = result["token"]
    return result


@app.get("/login")
async def login_page():
    return FileResponse(str(STATIC_DIR / "index.html"), headers={"Cache-Control": "no-cache"})


# ── Models ──────────────────────────────────────────────
class TopicRequest(BaseModel):
    topic: str
    duration: int = 4
    config: dict = {}

class RefineRequest(BaseModel):
    script: str
    feedback: str

class VoiceoverRequest(BaseModel):
    script: str
    name: str = "voiceover"
    speed: float = 1.0
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    voice_id: str = ""
    config: dict = {}

class ClipSelection(BaseModel):
    url: str
    title: str
    index: int

class DownloadRequest(BaseModel):
    clips: list[ClipSelection]
    topic: str = ""
    config: dict = {}

class ThumbnailRequest(BaseModel):
    topic: str
    title: str
    name: str = "thumbnail"
    config: dict = {}

class AnalyzeClipsRequest(BaseModel):
    topic: str
    scenes: str  # JSON string of scenes array

class MetadataRequest(BaseModel):
    topic: str
    script: str
    config: dict = {}


# ── Routes ──────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/api/status")
async def api_status():
    return await proxy_request("/api/proxy/status", method="GET")


@app.get("/api/voices")
async def voices_endpoint():
    return await proxy_request("/api/proxy/voices", method="GET")


class VoicePreviewRequest(BaseModel):
    voice_id: str
    text: str


@app.post("/api/preview-voice")
async def preview_voice_endpoint(req: VoicePreviewRequest):
    return await proxy_request("/api/proxy/preview-voice", req.model_dump())


# ── Script (proxied to Railway) ────────────────────────
@app.post("/api/generate-script")
async def generate_script_endpoint(req: TopicRequest):
    return await proxy_request("/api/proxy/generate-script", req.model_dump())


@app.post("/api/refine-script")
async def refine_script_endpoint(req: RefineRequest):
    return await proxy_request("/api/proxy/refine-script", req.model_dump())


# ── Voiceover (proxied, audio saved locally) ───────────
@app.post("/api/generate-voiceover")
async def generate_voiceover_endpoint(req: VoiceoverRequest):
    result = await proxy_request("/api/proxy/generate-voiceover", req.model_dump())

    # Save audio locally
    audio_bytes = base64.b64decode(result["audio_base64"])
    output_path = OUTPUT_DIR / f"{req.name}.mp3"
    output_path.write_bytes(audio_bytes)

    return {
        "path": output_path.name,
        "duration": result["duration"],
        "word_timestamps": result["word_timestamps"],
    }


# ── Clips (LOCAL — yt-dlp) ────────────────────────────
@app.post("/api/search-clips")
async def search_clips_endpoint(req: TopicRequest):
    from steps.clip_finder import search_clips_for_scenes
    try:
        scenes = json.loads(req.topic)
        visuals = await asyncio.to_thread(search_clips_for_scenes, scenes, 5)
        return {"visuals": visuals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-clips")
async def download_clips_endpoint(req: DownloadRequest):
    from steps.clip_finder import download_clip
    from config import get_project_dir

    if req.topic:
        project_dir = get_project_dir(req.topic)
        clips_dir = project_dir / "clips"
    else:
        clips_dir = TEMP_DIR

    def _download_all():
        from concurrent.futures import ThreadPoolExecutor, as_completed

        for f in clips_dir.glob("clip_*.mp4"):
            f.unlink()

        def _one(clip):
            path = download_clip(clip.url, clip.index, clips_dir=clips_dir)
            if path:
                return {"index": clip.index, "file": path.name, "title": clip.title}
            return None

        downloaded = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_one, c) for c in req.clips]
            for fut in as_completed(futures):
                result = fut.result()
                if result:
                    downloaded.append(result)

        downloaded.sort(key=lambda x: x["index"])
        return downloaded

    downloaded = await asyncio.to_thread(_download_all)
    return {"clips": downloaded, "count": len(downloaded), "clips_dir": str(clips_dir)}


# ── Clip Analysis (proxied — uploads clips to Railway) ─
@app.post("/api/analyze-clips")
async def analyze_clips_endpoint(req: AnalyzeClipsRequest):
    from config import get_project_dir

    try:
        clips_dir = get_project_dir(req.topic) / "clips"

        if not clips_dir.exists() or not list(clips_dir.glob("clip_*.mp4")):
            raise HTTPException(
                status_code=400,
                detail="Geen gedownloade clips gevonden. Download eerst clips.",
            )

        clip_paths = sorted(clips_dir.glob("clip_*.mp4"))

        # Upload clips to proxy for Gemini analysis
        import httpx
        headers = {}
        if _proxy_token:
            headers["Authorization"] = f"Bearer {_proxy_token}"

        files_list = [
            ("clips", (cp.name, cp.read_bytes(), "video/mp4"))
            for cp in clip_paths
        ]
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{PROXY_URL}/api/proxy/analyze-clips",
                headers=headers,
                files=files_list,
                data={"scenes": req.scenes},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Video Combine (LOCAL — FFmpeg) ─────────────────────
class CombineWithSubsRequest(BaseModel):
    audio_duration: float
    name: str
    topic: str = ""
    script: str = ""
    word_timestamps: list[dict] | None = None
    config: dict = {}


@app.post("/api/combine-video")
async def combine_video_endpoint(req: CombineWithSubsRequest):
    from steps.video_editor import combine_clips, add_audio_to_video, burn_subtitles
    from steps.subtitle_generator import generate_srt_from_timestamps, generate_srt
    from steps.pipeline_config import PipelineConfig
    from config import get_project_dir
    try:
        if req.topic:
            clips_dir = get_project_dir(req.topic) / "clips"
        else:
            clips_dir = TEMP_DIR

        clip_paths = sorted(clips_dir.glob("clip_*.mp4"))
        if not clip_paths:
            raise HTTPException(status_code=400, detail=f"No clips found in {clips_dir}")

        cfg = PipelineConfig.from_dict(req.config)
        combined = combine_clips(clip_paths, req.audio_duration, config=cfg)
        audio_path = OUTPUT_DIR / f"{req.name}.mp3"
        final = add_audio_to_video(combined, audio_path, req.name)

        if req.word_timestamps:
            srt_path = generate_srt_from_timestamps(req.word_timestamps, req.name)
            final = burn_subtitles(final, srt_path, req.name, config=cfg)
        elif req.script:
            srt_path = generate_srt(req.script, req.audio_duration, req.name)
            final = burn_subtitles(final, srt_path, req.name, config=cfg)

        return {"video": final.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Thumbnails (proxied, images saved locally) ─────────
@app.post("/api/generate-thumbnail")
async def generate_thumbnail_endpoint(req: ThumbnailRequest):
    result = await proxy_request("/api/proxy/generate-thumbnail", req.model_dump())
    img_bytes = base64.b64decode(result["image_base64"])
    output_path = OUTPUT_DIR / f"{req.name}.png"
    output_path.write_bytes(img_bytes)
    return {"thumbnail": output_path.name}


@app.post("/api/upload-thumbnail")
async def upload_thumbnail_endpoint(file: UploadFile = File(...)):
    try:
        import uuid
        from PIL import Image
        ext = Path(file.filename).suffix or ".png"
        safe_name = f"thumb_upload_{uuid.uuid4().hex[:8]}{ext}"
        dest = OUTPUT_DIR / safe_name
        contents = await file.read()
        dest.write_bytes(contents)

        img = Image.open(dest)
        img = img.resize((1280, 720), Image.LANCZOS)
        png_name = dest.with_suffix(".png").name
        png_path = OUTPUT_DIR / png_name
        img.save(str(png_path), quality=95)
        if ext != ".png":
            dest.unlink(missing_ok=True)

        return {"thumbnail": png_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-thumbnail-ai")
async def generate_thumbnail_ai_endpoint(
    prompt: str = Form(...),
    name: str = Form("thumbnail"),
    base_image: UploadFile | None = File(None),
):
    import httpx
    headers = {}
    if _proxy_token:
        headers["Authorization"] = f"Bearer {_proxy_token}"

    files_list = []
    if base_image and base_image.filename:
        files_list.append(("base_image", (base_image.filename, await base_image.read(), base_image.content_type or "image/png")))

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{PROXY_URL}/api/proxy/generate-thumbnail-ai",
            headers=headers,
            files=files_list or None,
            data={"prompt": prompt, "name": name},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        result = resp.json()

    img_bytes = base64.b64decode(result["image_base64"])
    output_path = OUTPUT_DIR / f"{name}.png"
    output_path.write_bytes(img_bytes)
    return {"thumbnail": output_path.name}


# ── Metadata (proxied) ────────────────────────────────
@app.post("/api/generate-metadata")
async def generate_metadata_endpoint(req: MetadataRequest):
    return await proxy_request("/api/proxy/generate-metadata", req.model_dump())


@app.post("/api/viral-titles")
async def viral_titles_endpoint(req: MetadataRequest):
    return await proxy_request("/api/proxy/viral-titles", req.model_dump())


@app.post("/api/viral-descriptions")
async def viral_descriptions_endpoint(req: MetadataRequest):
    return await proxy_request("/api/proxy/viral-descriptions", req.model_dump())


# ── Niche Analysis (local yt-dlp search + proxied OpenAI) ─
class NicheRequest(BaseModel):
    topic: str


@app.post("/api/analyze-niche")
async def analyze_niche_endpoint(req: NicheRequest):
    from steps.clip_finder import search_youtube
    try:
        # Local yt-dlp search
        results = await asyncio.to_thread(search_youtube, req.topic, 10)
        titles = [r.get("title", "") for r in results]
        channels = [r.get("channel", "") for r in results]

        # Proxy to Railway for OpenAI analysis
        return await proxy_request("/api/proxy/analyze-niche", {
            "topic": req.topic,
            "titles": titles,
            "channels": channels,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Copyright Check (LOCAL — yt-dlp) ──────────────────
class CopyrightRequest(BaseModel):
    url: str


@app.post("/api/check-copyright")
async def check_copyright_endpoint(req: CopyrightRequest):
    from steps.copyright_checker import check_clip_copyright
    try:
        data = await asyncio.to_thread(check_clip_copyright, req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Prompt Templates (proxied) ─────────────────────────
@app.get("/api/prompt-templates")
async def prompt_templates_endpoint():
    return await proxy_request("/api/proxy/prompt-templates", method="GET")


# ── Thumbnail Edit (LOCAL — PIL) ───────────────────────
class ThumbnailEditRequest(BaseModel):
    base_image: str
    edits: dict


@app.post("/api/edit-thumbnail")
async def edit_thumbnail_endpoint(req: ThumbnailEditRequest):
    from steps.thumbnail import apply_thumbnail_edits
    try:
        base_path = OUTPUT_DIR / req.base_image
        if not base_path.exists():
            raise HTTPException(status_code=400, detail="Base image niet gevonden")
        path = apply_thumbnail_edits(base_path, req.edits)
        return {"thumbnail": path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Hook Preview (LOCAL — FFmpeg) ──────────────────────
class HookPreviewRequest(BaseModel):
    video_file: str
    duration: float = 3.0


@app.post("/api/render-hook")
async def render_hook_endpoint(req: HookPreviewRequest):
    from steps.video_editor import render_hook_preview
    try:
        video_path = OUTPUT_DIR / req.video_file
        if not video_path.exists():
            raise HTTPException(status_code=400, detail="Video bestand niet gevonden")
        path = await asyncio.to_thread(render_hook_preview, video_path, req.duration)
        return {"hook_video": path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Highlight Extraction (LOCAL — FFmpeg) ──────────────
@app.post("/api/extract-highlights")
async def extract_highlights_endpoint(file: UploadFile = File(...), count: int = Form(5)):
    from steps.highlight_extractor import extract_highlights
    import uuid
    try:
        ext = Path(file.filename).suffix or ".mp4"
        temp_name = f"hl_upload_{uuid.uuid4().hex[:8]}{ext}"
        temp_path = TEMP_DIR / temp_name
        temp_path.write_bytes(await file.read())

        highlights = await asyncio.to_thread(extract_highlights, temp_path, count)
        temp_path.unlink(missing_ok=True)

        return {"highlights": highlights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Reset (LOCAL) ──────────────────────────────────────
@app.post("/api/reset")
async def reset_endpoint():
    for f in TEMP_DIR.glob("clip_*.mp4"):
        f.unlink()
    for f in TEMP_DIR.glob("*.txt"):
        f.unlink()
    return {"status": "ok"}


# ── Run ────────────────────────────────────────────────
def main():
    """CLI entry point for youtube-factory command."""
    import uvicorn
    import webbrowser
    port = int(os.getenv("PORT", "3333"))
    print(f"\n  YouTube Factory draait op http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
