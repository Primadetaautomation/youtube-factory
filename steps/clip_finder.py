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

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            print(f"  yt-dlp search failed (exit {result.returncode}): {stderr}")
            return []

        stdout = result.stdout.strip()
        if not stdout:
            print(f"  No results for query: {query}")
            return []

        results = []
        for line in stdout.split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                vid = data.get("id", "")
                if not vid:
                    continue
                raw_url = data.get("url", "")
                url = raw_url if raw_url and "youtube.com" in raw_url else f"https://www.youtube.com/watch?v={vid}"
                results.append({
                    "video_id": vid,
                    "title": data.get("title", "Untitled"),
                    "channel": data.get("channel", data.get("uploader", "Unknown")),
                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                    "url": url,
                })
            except json.JSONDecodeError:
                continue

        return results

    except subprocess.TimeoutExpired:
        print(f"  Search timed out for query: {query}")
        return []
    except Exception as e:
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
        # Remove stale file to avoid yt-dlp skipping download
        if output_path.exists():
            output_path.unlink()

        result = subprocess.run(
            [
                "yt-dlp",
                video_url,
                "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                "--merge-output-format", "mp4",
                "--download-sections", f"*0-{max_duration}",
                "--output", str(output_path),
                "--force-overwrites",
                "--quiet",
                "--no-warnings",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if output_path.exists():
            return output_path

        stderr = result.stderr.strip() if result.stderr else ""
        print(f"  Download failed for clip {clip_index} (exit {result.returncode}): {stderr}")

    except subprocess.TimeoutExpired:
        print(f"  Download timed out for clip {clip_index}: {video_url}")
    except Exception as e:
        print(f"  Error downloading clip {clip_index}: {e}")

    return None


def search_clips_for_scenes(scenes: list, results_per_query: int = 5) -> list[dict]:
    """Search YouTube for each visual in each scene, return options per visual."""
    all_visuals = []

    for scene in scenes:
        # Guard against scenes being strings instead of dicts
        if isinstance(scene, str):
            print(f"  Skipping non-dict scene: {scene[:80]}")
            continue

        visuals = scene.get("visuals", [])
        for visual in visuals:
            # Guard against visuals being strings instead of dicts
            if isinstance(visual, str):
                query = visual
                description = visual
                line = ""
            elif isinstance(visual, dict):
                query = visual.get("search_query", "")
                description = visual.get("description", "")
                line = visual.get("line", "")
            else:
                continue

            if not query:
                continue

            results = search_youtube(query, max_results=results_per_query)
            all_visuals.append({
                "line": line,
                "description": description,
                "search_query": query,
                "options": results,
                "selected_index": 0,
            })

    return all_visuals
