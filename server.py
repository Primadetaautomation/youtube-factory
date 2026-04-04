"""YouTube Factory — FastAPI backend."""
import asyncio
import logging
import sys, json, shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import OUTPUT_DIR, TEMP_DIR
from steps.pipeline_config import PipelineConfig
from steps.auth import verify_credentials, create_token, verify_token

from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="YouTube Factory")


# ── Auth middleware ────────────────────────────
AUTH_EXEMPT = {"/api/auth/login", "/api/status", "/", "/login"}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Skip auth for static files, login, and exempt paths
        if (path.startswith("/static") or path.startswith("/output")
                or path in AUTH_EXEMPT or not path.startswith("/api")):
            return await call_next(request)

        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        if not token or not verify_token(token):
            return JSONResponse(status_code=401, content={"detail": "Niet ingelogd"})

        return await call_next(request)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api") is False:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)
app.add_middleware(AuthMiddleware)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


# ── Auth ────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login_endpoint(req: LoginRequest):
    if verify_credentials(req.email, req.password):
        token = create_token(req.email)
        return {"token": token, "email": req.email}
    raise HTTPException(status_code=401, detail="Ongeldige inloggegevens")

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

class UploadRequest(BaseModel):
    video_file: str
    title: str
    description: str
    tags: list[str]
    thumbnail_file: str | None = None
    privacy: str = "private"
    publish_at: str | None = None


# ── Routes ──────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/api/status")
async def api_status():
    from config import OPENAI_API_KEY, ELEVENLABS_API_KEY, YOUTUBE_API_KEY, GEMINI_API_KEY
    return {
        "openai": bool(OPENAI_API_KEY),
        "elevenlabs": bool(ELEVENLABS_API_KEY),
        "youtube": bool(YOUTUBE_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
    }


@app.get("/api/voices")
async def voices_endpoint():
    from config import VOICE_PRESETS
    return {"voices": VOICE_PRESETS}


class VoicePreviewRequest(BaseModel):
    voice_id: str
    text: str


@app.post("/api/preview-voice")
async def preview_voice_endpoint(req: VoicePreviewRequest):
    import base64
    from elevenlabs import ElevenLabs
    from config import ELEVENLABS_API_KEY
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio_gen = client.text_to_speech.convert(
            voice_id=req.voice_id,
            text=req.text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_gen)
        b64 = base64.b64encode(audio_bytes).decode()
        return {"audio_base64": b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-script")
async def generate_script_endpoint(req: TopicRequest):
    from steps.script_generator import generate_script
    try:
        cfg = PipelineConfig.from_dict(req.config)
        data = generate_script(req.topic, req.duration, config=cfg)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refine-script")
async def refine_script_endpoint(req: RefineRequest):
    from steps.script_generator import refine_script
    try:
        data = refine_script(req.script, req.feedback)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-voiceover")
async def generate_voiceover_endpoint(req: VoiceoverRequest):
    from steps.voiceover import generate_voiceover_with_timestamps
    try:
        result = generate_voiceover_with_timestamps(
            req.script, req.name, speed=req.speed,
            stability=req.stability, similarity_boost=req.similarity_boost, style=req.style,
            voice_id=req.voice_id,
        )
        return {
            "path": result["audio_path"].name,
            "duration": result["duration"],
            "word_timestamps": result["word_timestamps"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search-clips")
async def search_clips_endpoint(req: TopicRequest):
    """Search YouTube clips for all scenes."""
    from steps.clip_finder import search_clips_for_scenes
    try:
        # req.topic is actually the scenes JSON string
        scenes = json.loads(req.topic)
        # Run synchronous yt-dlp searches in a thread to avoid blocking the event loop
        visuals = await asyncio.to_thread(search_clips_for_scenes, scenes, 5)
        return {"visuals": visuals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-clips")
async def download_clips_endpoint(req: DownloadRequest):
    from steps.clip_finder import download_clip
    from config import get_project_dir

    # Use per-project clips folder
    if req.topic:
        project_dir = get_project_dir(req.topic)
        clips_dir = project_dir / "clips"
    else:
        clips_dir = TEMP_DIR

    def _download_all():
        # Clean old clips
        for f in clips_dir.glob("clip_*.mp4"):
            f.unlink()

        downloaded = []
        for clip in req.clips:
            path = download_clip(clip.url, clip.index, clips_dir=clips_dir)
            if path:
                downloaded.append({"index": clip.index, "file": path.name, "title": clip.title})
        return downloaded

    # Run synchronous yt-dlp downloads in a thread to avoid blocking the event loop
    downloaded = await asyncio.to_thread(_download_all)
    return {"clips": downloaded, "count": len(downloaded), "clips_dir": str(clips_dir)}


@app.post("/api/analyze-clips")
async def analyze_clips_endpoint(req: AnalyzeClipsRequest):
    """Analyze downloaded clips with Gemini and match them to script scenes."""
    from steps.clip_analyzer import analyze_and_match
    from config import get_project_dir

    try:
        scenes = json.loads(req.scenes)
        clips_dir = get_project_dir(req.topic) / "clips"

        if not clips_dir.exists() or not list(clips_dir.glob("clip_*.mp4")):
            raise HTTPException(
                status_code=400,
                detail="Geen gedownloade clips gevonden. Download eerst clips.",
            )

        result = await asyncio.to_thread(analyze_and_match, clips_dir, scenes)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ongeldig scenes JSON formaat")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    from config import get_project_dir
    try:
        # Find clips in project folder or temp
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

        # Generate and burn subtitles
        if req.word_timestamps:
            srt_path = generate_srt_from_timestamps(req.word_timestamps, req.name)
            final = burn_subtitles(final, srt_path, req.name, config=cfg)
        elif req.script:
            srt_path = generate_srt(req.script, req.audio_duration, req.name)
            final = burn_subtitles(final, srt_path, req.name, config=cfg)

        return {"video": final.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-thumbnail")
async def generate_thumbnail_endpoint(req: ThumbnailRequest):
    from steps.thumbnail import generate_thumbnail
    try:
        path = generate_thumbnail(req.topic, req.title, req.name)
        return {"thumbnail": path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-thumbnail")
async def upload_thumbnail_endpoint(file: UploadFile = File(...)):
    """Accept a user-uploaded thumbnail image."""
    try:
        import uuid
        ext = Path(file.filename).suffix or ".png"
        safe_name = f"thumb_upload_{uuid.uuid4().hex[:8]}{ext}"
        dest = OUTPUT_DIR / safe_name
        contents = await file.read()
        dest.write_bytes(contents)

        # Resize to standard YouTube thumbnail size
        from PIL import Image
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


class NanoBananaRequest(BaseModel):
    prompt: str
    name: str = "thumbnail"
    base_image: str | None = None  # filename in output dir


@app.post("/api/generate-thumbnail-ai")
async def generate_thumbnail_ai_endpoint(
    prompt: str = Form(...),
    name: str = Form("thumbnail"),
    base_image: UploadFile | None = File(None),
):
    """Generate or edit a thumbnail using Gemini image generation (Nano Banana)."""
    from steps.thumbnail import generate_thumbnail_nanobanana
    try:
        base_path = None
        if base_image and base_image.filename:
            import uuid
            ext = Path(base_image.filename).suffix or ".png"
            temp_name = f"nb_base_{uuid.uuid4().hex[:8]}{ext}"
            base_path = OUTPUT_DIR / temp_name
            base_path.write_bytes(await base_image.read())

        path = generate_thumbnail_nanobanana(prompt, name, base_path)

        # Clean up temp base image
        if base_path:
            base_path.unlink(missing_ok=True)

        return {"thumbnail": path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-metadata")
async def generate_metadata_endpoint(req: MetadataRequest):
    from steps.metadata import generate_metadata
    try:
        data = generate_metadata(req.topic, req.script)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/viral-titles")
async def viral_titles_endpoint(req: MetadataRequest):
    from steps.metadata import generate_viral_titles
    try:
        data = generate_viral_titles(req.topic, req.script)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/viral-descriptions")
async def viral_descriptions_endpoint(req: MetadataRequest):
    from steps.metadata import generate_viral_descriptions
    try:
        data = generate_viral_descriptions(req.topic, req.script)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NicheRequest(BaseModel):
    topic: str

@app.post("/api/analyze-niche")
async def analyze_niche_endpoint(req: NicheRequest):
    from steps.niche_analyzer import analyze_niche
    try:
        data = await asyncio.to_thread(analyze_niche, req.topic)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/prompt-templates")
async def prompt_templates_endpoint():
    from steps.prompt_templates import get_prompt_templates
    return {"templates": get_prompt_templates()}


class ThumbnailEditRequest(BaseModel):
    base_image: str  # filename in output dir
    edits: dict  # {crop, text_overlays, filters}

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


@app.post("/api/upload")
async def upload_endpoint(req: UploadRequest):
    from steps.uploader import upload_video
    try:
        video_path = OUTPUT_DIR / req.video_file
        thumb_path = OUTPUT_DIR / req.thumbnail_file if req.thumbnail_file else None
        publish_at = req.publish_at if hasattr(req, 'publish_at') else None
        video_id = upload_video(video_path, req.title, req.description, req.tags, thumb_path, req.privacy, publish_at)
        return {"video_id": video_id, "url": f"https://youtu.be/{video_id}"}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="client_secret.json niet gevonden. Maak OAuth credentials aan in Google Cloud Console.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchTopicItem(BaseModel):
    topic: str
    duration: int = 4

class BatchRequest(BaseModel):
    topics: list[BatchTopicItem]
    start_date: str
    publish_time: str = "09:00"
    auto_upload: bool = False
    config: dict = {}


@app.post("/api/batch")
async def batch_endpoint(req: BatchRequest):
    """Run pipeline for multiple topics with scheduled publishing."""
    from steps.batch_runner import run_batch_pipeline
    try:
        results = run_batch_pipeline(
            [t.model_dump() for t in req.topics],
            req.start_date,
            req.publish_time,
        )

        # Auto-upload if requested and client_secret exists
        if req.auto_upload:
            from steps.uploader import upload_video
            for r in results:
                if r["status"] == "ready" and r.get("video_file"):
                    try:
                        video_path = OUTPUT_DIR / r["video_file"]
                        thumb_path = OUTPUT_DIR / r["thumbnail_file"] if r.get("thumbnail_file") else None
                        video_id = upload_video(
                            video_path, r["title"], r["description"], r["tags"],
                            thumb_path, "private", r["publish_at"],
                        )
                        r["status"] = "uploaded"
                        r["video_id"] = video_id
                        r["url"] = f"https://youtu.be/{video_id}"
                    except Exception as e:
                        r["upload_error"] = str(e)

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset_endpoint():
    """Clean temp and output dirs."""
    for f in TEMP_DIR.glob("clip_*.mp4"):
        f.unlink()
    for f in TEMP_DIR.glob("*.txt"):
        f.unlink()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "3333"))
    uvicorn.run(app, host="0.0.0.0", port=port)
