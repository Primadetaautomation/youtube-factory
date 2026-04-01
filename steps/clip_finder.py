"""Find and download video clips from YouTube using yt-dlp."""
import subprocess
import json
from pathlib import Path
from config import TEMP_DIR, MAX_CLIP_DURATION


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Search YouTube via yt-dlp (no API key needed)."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--flat-playlist",
                "--quiet",
                "--no-warnings",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        results = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                vid = data.get("id", "")
                results.append({
                    "video_id": vid,
                    "title": data.get("title", "Untitled"),
                    "channel": data.get("channel", data.get("uploader", "Unknown")),
                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                    "url": data.get("url", f"https://www.youtube.com/watch?v={vid}"),
                })
            except json.JSONDecodeError:
                continue

        return results

    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"  Search error: {e}")
        return []


def download_clip(
    video_url: str,
    clip_index: int,
    max_duration: int | float = MAX_CLIP_DURATION,
    clips_dir: Path | None = None,
    *,
    config=None,
) -> Path | None:
    """Download a short clip from a YouTube video."""
    if config is not None:
        max_duration = config.max_clip_duration
    dest = clips_dir or TEMP_DIR
    output_path = dest / f"clip_{clip_index:03d}.mp4"

    try:
        subprocess.run(
            [
                "yt-dlp",
                video_url,
                "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                "--merge-output-format", "mp4",
                "--download-sections", f"*0-{max_duration}",
                "--output", str(output_path),
                "--quiet",
                "--no-warnings",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if output_path.exists():
            return output_path

    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"  Error downloading clip {clip_index}: {e}")

    return None


def search_clips_for_scenes(scenes: list[dict], results_per_query: int = 5) -> list[dict]:
    """Search YouTube for each visual in each scene, return options per visual."""
    all_visuals = []

    for scene in scenes:
        for visual in scene.get("visuals", []):
            query = visual.get("search_query", "")
            if not query:
                continue

            results = search_youtube(query, max_results=results_per_query)
            all_visuals.append({
                "line": visual.get("line", ""),
                "description": visual.get("description", ""),
                "search_query": query,
                "options": results,
                "selected_index": 0,
            })

    return all_visuals
