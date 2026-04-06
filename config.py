import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Voice presets: 3 male + 4 female, diverse origins
VOICE_PRESETS = [
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "gender": "man", "accent": "Brits", "desc": "Warm verteller"},
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "gender": "man", "accent": "Australisch", "desc": "Diep, energiek"},
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "man", "accent": "Brits", "desc": "Rustige nieuwslezer"},
    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice", "gender": "vrouw", "accent": "Brits", "desc": "Helder, educatief"},
    {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica", "gender": "vrouw", "accent": "Amerikaans", "desc": "Speels, warm"},
    {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "gender": "vrouw", "accent": "Brits", "desc": "Fluweelzacht, actrice"},
    {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda", "gender": "vrouw", "accent": "Amerikaans", "desc": "Professioneel, kundig"},
]
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

# Proxy URL for local app to reach Railway server
PROXY_URL = os.getenv("PROXY_URL", "https://youtube-factory-production.up.railway.app")

# Defaults
DEFAULT_VIDEO_DURATION = 240  # 4 minutes
MAX_CLIP_DURATION = 3  # seconds per clip
CLIPS_PER_VIDEO = 12

# Resolution presets: name -> (width, height) for 16:9
RESOLUTION_MAP = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}

# Aspect ratio presets
ASPECT_RATIO_MAP = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "1:1": (1, 1),
}

# Encoding quality presets: name -> (crf, preset)
QUALITY_PRESETS = {
    "draft": {"crf": 28, "preset": "ultrafast", "label": "Draft (720p snel)"},
    "standard": {"crf": 23, "preset": "fast", "label": "Standaard (1080p)"},
    "high": {"crf": 18, "preset": "medium", "label": "Hoog (4K)"},
}


def get_project_dir(topic: str) -> Path:
    """Get or create a per-topic project directory."""
    safe_name = topic.lower().replace(" ", "_")[:30]
    project_dir = OUTPUT_DIR / safe_name
    project_dir.mkdir(exist_ok=True)
    (project_dir / "clips").mkdir(exist_ok=True)
    return project_dir
