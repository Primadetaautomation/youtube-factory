"""Extract highlights from longer videos for shorts creation."""

import json
import subprocess
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY, OUTPUT_DIR

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-3.1-pro"


def extract_highlights(
    video_path: Path,
    target_count: int = 5,
) -> list[dict]:
    """Analyze a video and extract key moments as highlight clips.

    Uses FFmpeg scene detection as a pre-filter, then GPT-4o to
    select the most interesting moments for shorts.
    """
    # Step 1: FFmpeg scene detection to find scene changes
    scene_times = _detect_scenes(video_path)

    # Step 2: Use AI to select best highlights from scene timestamps
    highlights = _select_highlights(scene_times, target_count)

    # Step 3: Extract each highlight clip
    for i, h in enumerate(highlights):
        clip_path = OUTPUT_DIR / f"highlight_{i:03d}.mp4"
        _extract_clip(video_path, h["start"], h["end"], clip_path)
        h["clip_path"] = str(clip_path) if clip_path.exists() else None

    return highlights


def _detect_scenes(video_path: Path, threshold: float = 0.4) -> list[float]:
    """Detect scene changes in a video using FFmpeg."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", f"frame=pts_time",
                "-select_streams", "v",
                "-of", "csv=p=0",
                "-f", "lavfi",
                f"movie={video_path},select=gt(scene\\,{threshold})",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        times = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Handle both "pts_time=12.5" and plain "12.5" formats
            if "pts_time=" in line:
                for part in line.split(","):
                    if "pts_time=" in part:
                        try:
                            times.append(float(part.split("=")[1]))
                        except (ValueError, IndexError):
                            continue
            else:
                try:
                    times.append(float(line))
                except ValueError:
                    continue

        return sorted(times)

    except (subprocess.TimeoutExpired, Exception):
        return []


def _select_highlights(
    scene_times: list[float],
    target_count: int,
) -> list[dict]:
    """Use Gemini to select the best highlights from scene timestamps."""
    prompt = f"""Given these scene change timestamps (in seconds) from a video:
{json.dumps(scene_times[:50])}

Select the {target_count} most interesting moments for creating viral short clips.
For each moment, define a 3-5 second window around the scene change.

Return JSON:
{{
    "highlights": [
        {{"start": 10.0, "end": 15.0, "description": "Brief description of likely content"}}
    ]
}}
Return ONLY valid JSON, no markdown.
"""

    try:
        response = _client.models.generate_content(model=_MODEL, contents=[prompt])
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()
        data = json.loads(text)
        return data.get("highlights", [])
    except Exception:
        return []


def _extract_clip(
    video_path: Path,
    start: float,
    end: float,
    output_path: Path,
) -> None:
    """Extract a clip from a video between start and end timestamps."""
    duration = end - start
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(video_path),
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, Exception):
        pass
