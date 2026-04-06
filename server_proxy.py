"""YouTube Factory — API Proxy Server for Railway.

Handles all AI API calls (OpenAI, ElevenLabs, Gemini) and authentication.
Local apps connect to this proxy to use AI features without needing API keys.
"""
import asyncio
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import OUTPUT_DIR, TEMP_DIR
from steps.auth import verify_credentials, create_token, verify_token
from steps.pipeline_config import PipelineConfig

from starlette.middleware.base import BaseHTTPMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="YouTube Factory Proxy")

# CORS — allow local apps to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (download page, installer scripts)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Auth middleware ────────────────────────────
AUTH_EXEMPT = {"/api/auth/login", "/api/proxy/status", "/health"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path in AUTH_EXEMPT or not path.startswith("/api"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

        if not token or not verify_token(token):
            return JSONResponse(status_code=401, content={"detail": "Niet ingelogd"})

        return await call_next(request)


app.add_middleware(AuthMiddleware)


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


@app.get("/")
async def download_page():
    return FileResponse(str(STATIC_DIR / "download.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Status ──────────────────────────────────────────────
@app.get("/api/proxy/status")
async def status_endpoint():
    from config import OPENAI_API_KEY, ELEVENLABS_API_KEY, GEMINI_API_KEY
    return {
        "openai": bool(OPENAI_API_KEY),
        "elevenlabs": bool(ELEVENLABS_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
    }


# ── Script Generation (OpenAI) ─────────────────────────
class TopicRequest(BaseModel):
    topic: str
    duration: int = 4
    config: dict = {}


class RefineRequest(BaseModel):
    script: str
    feedback: str


@app.post("/api/proxy/generate-script")
async def generate_script_endpoint(req: TopicRequest):
    from steps.script_generator import generate_script
    try:
        cfg = PipelineConfig.from_dict(req.config)
        data = generate_script(req.topic, req.duration, config=cfg)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/refine-script")
async def refine_script_endpoint(req: RefineRequest):
    from steps.script_generator import refine_script
    try:
        data = refine_script(req.script, req.feedback)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Voiceover (ElevenLabs) ──────────────────────────────
class VoiceoverRequest(BaseModel):
    script: str
    name: str = "voiceover"
    speed: float = 1.0
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    voice_id: str = ""
    config: dict = {}


@app.post("/api/proxy/generate-voiceover")
async def generate_voiceover_endpoint(req: VoiceoverRequest):
    from steps.voiceover import generate_voiceover_with_timestamps
    try:
        result = generate_voiceover_with_timestamps(
            req.script, req.name, speed=req.speed,
            stability=req.stability, similarity_boost=req.similarity_boost,
            style=req.style, voice_id=req.voice_id,
        )
        audio_path = result["audio_path"]
        audio_b64 = base64.b64encode(audio_path.read_bytes()).decode()
        # Clean up server-side file
        audio_path.unlink(missing_ok=True)
        ts_path = OUTPUT_DIR / f"{req.name}_timestamps.json"
        ts_path.unlink(missing_ok=True)

        return {
            "audio_base64": audio_b64,
            "duration": result["duration"],
            "word_timestamps": result["word_timestamps"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VoicePreviewRequest(BaseModel):
    voice_id: str
    text: str


@app.post("/api/proxy/preview-voice")
async def preview_voice_endpoint(req: VoicePreviewRequest):
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


@app.get("/api/proxy/voices")
async def voices_endpoint():
    from config import VOICE_PRESETS
    return {"voices": VOICE_PRESETS}


# ── Metadata (OpenAI) ──────────────────────────────────
class MetadataRequest(BaseModel):
    topic: str
    script: str
    config: dict = {}


@app.post("/api/proxy/generate-metadata")
async def generate_metadata_endpoint(req: MetadataRequest):
    from steps.metadata import generate_metadata
    try:
        return generate_metadata(req.topic, req.script)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/viral-titles")
async def viral_titles_endpoint(req: MetadataRequest):
    from steps.metadata import generate_viral_titles
    try:
        return generate_viral_titles(req.topic, req.script)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/viral-descriptions")
async def viral_descriptions_endpoint(req: MetadataRequest):
    from steps.metadata import generate_viral_descriptions
    try:
        return generate_viral_descriptions(req.topic, req.script)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Clip Analysis (Gemini) ──────────────────────────────
@app.post("/api/proxy/analyze-clips")
async def analyze_clips_endpoint(
    scenes: str = Form(...),
    clips: list[UploadFile] = File(...),
):
    """Accept clip uploads from local app, analyze with Gemini, return matches."""
    from steps.clip_analyzer import analyze_and_match

    try:
        scenes_data = json.loads(scenes)

        # Save uploaded clips to temp dir
        clips_dir = TEMP_DIR / f"analyze_{int(time.time())}"
        clips_dir.mkdir(parents=True, exist_ok=True)

        for i, clip_file in enumerate(clips):
            clip_path = clips_dir / f"clip_{i:03d}.mp4"
            clip_path.write_bytes(await clip_file.read())

        result = await asyncio.to_thread(analyze_and_match, clips_dir, scenes_data)

        # Clean up temp clips
        import shutil
        shutil.rmtree(clips_dir, ignore_errors=True)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ongeldig scenes JSON formaat")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Thumbnails (DALL-E / Gemini) ────────────────────────
class ThumbnailRequest(BaseModel):
    topic: str
    title: str
    name: str = "thumbnail"
    config: dict = {}


@app.post("/api/proxy/generate-thumbnail")
async def generate_thumbnail_endpoint(req: ThumbnailRequest):
    from steps.thumbnail import generate_thumbnail
    try:
        path = generate_thumbnail(req.topic, req.title, req.name)
        img_b64 = base64.b64encode(path.read_bytes()).decode()
        path.unlink(missing_ok=True)
        return {"image_base64": img_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/generate-thumbnail-ai")
async def generate_thumbnail_ai_endpoint(
    prompt: str = Form(...),
    name: str = Form("thumbnail"),
    base_image: UploadFile | None = File(None),
):
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

        if base_path:
            base_path.unlink(missing_ok=True)

        img_b64 = base64.b64encode(path.read_bytes()).decode()
        path.unlink(missing_ok=True)
        return {"image_base64": img_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Niche Analysis (OpenAI — search data provided by local app) ─
class NicheRequest(BaseModel):
    topic: str
    titles: list[str] = []
    channels: list[str] = []


@app.post("/api/proxy/analyze-niche")
async def analyze_niche_endpoint(req: NicheRequest):
    """Analyze niche potential. Local app provides yt-dlp search data."""
    from openai import OpenAI
    from config import OPENAI_API_KEY

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""Analyze this YouTube niche/topic for a content creator: "{req.topic}"

Here are the top {len(req.titles)} search results:
Titles: {json.dumps(req.titles, ensure_ascii=False)}
Channels: {json.dumps(req.channels, ensure_ascii=False)}

Based on these results, analyze:
1. Volume estimate (how much content exists): "low", "medium", "high"
2. Competition level (how established are the channels): "low", "medium", "high"
3. Is this topic currently trending?
4. Overall niche score (1-10, where 10 = great opportunity)
5. 3-5 specific recommendations for a new creator in this niche
6. Top channels dominating this niche

Return JSON:
{{
    "volume_estimate": "low|medium|high",
    "competition": "low|medium|high",
    "trending": true|false,
    "score": 8.5,
    "recommendations": ["recommendation 1", "recommendation 2"],
    "top_channels": ["channel1", "channel2"]
}}
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        analysis = json.loads(response.choices[0].message.content)
        analysis["topic"] = req.topic
        analysis["search_results_count"] = len(req.titles)
        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Prompt Templates ────────────────────────────────────
@app.get("/api/proxy/prompt-templates")
async def prompt_templates_endpoint():
    from steps.prompt_templates import get_prompt_templates
    return {"templates": get_prompt_templates()}


# ── Run ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3333"))
    uvicorn.run(app, host="0.0.0.0", port=port)
