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

from fastapi.responses import HTMLResponse

app = FastAPI(title="YouTube Factory Proxy")

# CORS — allow local apps to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth middleware ────────────────────────────
AUTH_EXEMPT = {"/api/auth/login", "/api/proxy/status", "/health", "/download/mac", "/download/windows"}


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


DOWNLOAD_PAGE_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YouTube Factory — Download</title>
<style>
:root{--bg:#0a0a0f;--surface:#12121a;--border:#1e1e2e;--text:#e4e4e7;--text-dim:#71717a;--accent:#7c3aed;--accent-hover:#6d28d9;--green:#22c55e}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center}
.container{max-width:580px;width:100%;padding:2rem}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:2.5rem}
h1{font-size:1.75rem;margin-bottom:0.25rem}
.subtitle{color:var(--text-dim);margin-bottom:2rem;font-size:0.95rem}
.login-form{display:none}.login-form.active{display:block}
.download-content{display:none}.download-content.active{display:block}
.form-group{margin-bottom:1rem}
label{display:block;font-size:0.85rem;color:var(--text-dim);margin-bottom:0.35rem}
input{width:100%;padding:0.65rem 0.85rem;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:0.95rem}
input:focus{outline:none;border-color:var(--accent)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:0.5rem;padding:0.85rem 1.5rem;border-radius:10px;font-size:1rem;font-weight:600;cursor:pointer;border:none;text-decoration:none;text-align:center;transition:all 0.2s;width:100%}
.btn-primary{background:var(--accent);color:white}.btn-primary:hover{background:var(--accent-hover);transform:translateY(-1px)}
.btn-secondary{background:transparent;border:1px solid var(--border);color:var(--text)}.btn-secondary:hover{border-color:var(--accent);background:rgba(124,58,237,0.08)}
.btn-block{width:100%}
.error-msg{background:#2d1215;color:#fca5a5;padding:0.75rem 1rem;border-radius:8px;margin-bottom:1rem;display:none}
.download-grid{display:flex;flex-direction:column;gap:0.75rem;margin-bottom:1.5rem}
.divider{display:flex;align-items:center;gap:1rem;margin:1.5rem 0;color:var(--text-dim);font-size:0.8rem}
.divider::before,.divider::after{content:'';flex:1;border-top:1px solid var(--border)}
.step{display:flex;gap:0.75rem;align-items:flex-start;margin-bottom:1rem;padding:0.75rem;background:var(--bg);border-radius:8px;border:1px solid var(--border)}
.step-num{min-width:28px;height:28px;border-radius:50%;background:var(--accent);color:white;display:flex;align-items:center;justify-content:center;font-size:0.8rem;font-weight:700}
.step p{margin:0;font-size:0.9rem;line-height:1.4}.step p.dim{color:var(--text-dim);font-size:0.8rem;margin-top:0.25rem}
.icon{font-size:1.2rem}
.badge{display:inline-block;padding:0.15rem 0.5rem;border-radius:4px;font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}
.badge-auto{background:rgba(34,197,94,0.15);color:var(--green)}
</style>
</head>
<body>
<div class="container"><div class="card">
<h1>YouTube Factory</h1>
<p class="subtitle">Maak AI-video's op je eigen PC. Download, dubbelklik, klaar.</p>
<div class="login-form active" id="loginForm">
  <div class="error-msg" id="loginError"></div>
  <div class="form-group"><label>Email</label><input type="email" id="email" placeholder="je@email.com"></div>
  <div class="form-group"><label>Wachtwoord</label><input type="password" id="password" placeholder="Wachtwoord" onkeydown="if(event.key==='Enter')doLogin()"></div>
  <button class="btn btn-primary" onclick="doLogin()" style="margin-top:1rem">Inloggen</button>
</div>
<div class="download-content" id="downloadContent">
  <p style="color:var(--green);margin-bottom:0.25rem;font-weight:600;font-size:0.9rem">Ingelogd!</p>
  <p style="color:var(--text-dim);margin-bottom:1.5rem;font-size:0.9rem">Download het bestand voor jouw systeem en dubbelklik erop.</p>
  <div class="download-grid">
    <a class="btn btn-primary" href="/download/mac" download="YouTube Factory Installer.command">
      <span class="icon">&#63743;</span> Download voor Mac
    </a>
    <a class="btn btn-secondary" href="/download/windows" download="YouTube Factory Installer.bat">
      <span class="icon">&#8862;</span> Download voor Windows
    </a>
  </div>
  <div class="divider">Hoe werkt het?</div>
  <div class="step">
    <span class="step-num">1</span>
    <div><p>Dubbelklik op het gedownloade bestand</p><p class="dim">Alles wordt automatisch geinstalleerd <span class="badge badge-auto">automatisch</span></p></div>
  </div>
  <div class="step">
    <span class="step-num">2</span>
    <div><p>De app opent in je browser</p><p class="dim">Op <strong>localhost:3333</strong> — werkt altijd, ook zonder internet</p></div>
  </div>
  <div class="step">
    <span class="step-num">3</span>
    <div><p>Log in en maak video's</p><p class="dim">Gebruik dezelfde login als hier. Je video's worden op je PC opgeslagen.</p></div>
  </div>
  <div class="divider">De volgende keer</div>
  <p style="color:var(--text-dim);font-size:0.85rem;text-align:center">Dubbelklik op <strong>YouTube Factory.command</strong> (Mac) of <strong>start.bat</strong> (Windows) in je youtube-factory map.</p>
</div>
</div></div>
<script>
async function doLogin(){
  const email=document.getElementById('email').value;
  const password=document.getElementById('password').value;
  const errEl=document.getElementById('loginError');
  errEl.style.display='none';
  try{
    const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
    if(!res.ok){const data=await res.json();throw new Error(data.detail||'Login mislukt')}
    document.getElementById('loginForm').classList.remove('active');
    document.getElementById('downloadContent').classList.add('active');
  }catch(e){errEl.textContent=e.message;errEl.style.display='block'}
}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def download_page():
    return DOWNLOAD_PAGE_HTML


@app.get("/download/mac")
async def download_mac():
    """Serve the Mac .command installer as a download."""
    from fastapi.responses import Response
    installer_path = Path(__file__).parent / "YouTube Factory Installer.command"
    if not installer_path.exists():
        raise HTTPException(status_code=404, detail="Installer niet gevonden")
    return Response(
        content=installer_path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="YouTube Factory Installer.command"'},
    )


@app.get("/download/windows")
async def download_windows():
    """Serve the Windows .bat installer as a download."""
    from fastapi.responses import Response
    installer_path = Path(__file__).parent / "install.bat"
    if not installer_path.exists():
        raise HTTPException(status_code=404, detail="Installer niet gevonden")
    return Response(
        content=installer_path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="YouTube Factory Installer.bat"'},
    )


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
