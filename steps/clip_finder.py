"""Find and download video clips from YouTube using yt-dlp."""
import logging
import os
import subprocess
import json
from pathlib import Path
from config import TEMP_DIR, MAX_CLIP_DURATION

logger = logging.getLogger(__name__)


def _ytdlp_extra_args() -> list[str]:
    """Extra yt-dlp flags from env (proxy, cookies, user-agent).

    Set these in Railway / .env to bypass YouTube IP blocks:
      YTDLP_PROXY=http://user:pass@proxy.example.com:8080
      YTDLP_COOKIES_FILE=/app/cookies.txt
      YTDLP_USER_AGENT=Mozilla/5.0 ...
    """
    # Always enable EJS challenge solver (needed for YouTube JS signatures)
    args: list[str] = ["--remote-components", "ejs:github"]
    proxy = os.getenv("YTDLP_PROXY", "").strip()
    if proxy:
        args.extend(["--proxy", proxy])
    cookies = os.getenv("YTDLP_COOKIES_FILE", "").strip()
    if cookies and Path(cookies).exists():
        args.extend(["--cookies", cookies])
    user_agent = os.getenv("YTDLP_USER_AGENT", "").strip()
    if user_agent:
        args.extend(["--user-agent", user_agent])
    return args


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Search YouTube via yt-dlp (no API key needed)."""
    try:
        cmd = [
            "yt-dlp",
            f"ytsearch{max_results}:{query}",
            "--dump-json",
            "--flat-playlist",
            "--quiet",
            "--no-warnings",
        ] + _ytdlp_extra_args()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else ""
            print(f"[SEARCH] yt-dlp search failed (exit {result.returncode}): {stderr}")
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

    def _find_output():
        """Check if output file exists, also check alternative extensions."""
        if output_path.exists():
            return output_path
        for alt in dest.glob(f"clip_{clip_index:03d}.*"):
            if alt.suffix in (".mp4", ".mkv", ".webm"):
                alt.rename(output_path)
                return output_path
        return None

    def _run_download(extra_args=None):
        # Remove stale file
        if output_path.exists():
            output_path.unlink()

        cmd = [
            "yt-dlp",
            video_url,
            "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "--output", str(output_path),
            "--force-overwrites",
        ] + _ytdlp_extra_args()
        if extra_args:
            cmd.extend(extra_args)

        print(f"[DOWNLOAD] Clip {clip_index}: running yt-dlp for {video_url}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "(no stderr)"
            stdout = result.stdout.strip() if result.stdout else ""
            print(f"[DOWNLOAD] Clip {clip_index} yt-dlp failed (exit {result.returncode}): {stderr}")
            if stdout:
                print(f"[DOWNLOAD] Clip {clip_index} stdout: {stdout[-500:]}")
        else:
            print(f"[DOWNLOAD] Clip {clip_index}: yt-dlp succeeded")

        return result

    import time
    import random

    def _attempt_with_retry(extra_args, label: str) -> bool:
        """Run yt-dlp with retry on 429 (rate limit)."""
        for attempt in range(3):
            result = _run_download(extra_args)
            if _find_output():
                return True
            stderr = (result.stderr or "") + (result.stdout or "")
            if "429" in stderr or "Too Many Requests" in stderr:
                wait = 5 * (attempt + 1) + random.uniform(0, 3)
                print(f"[DOWNLOAD] Clip {clip_index}: 429 rate limit on {label}, waiting {wait:.1f}s...")
                time.sleep(wait)
                continue
            # Non-429 error: give up on this attempt type
            return False
        return False

    try:
        # Attempt 1: with --download-sections for speed
        if _attempt_with_retry(["--download-sections", f"*0-{max_duration}"], "sections"):
            return _find_output()

        # Attempt 2: without --download-sections (some videos don't support it)
        print(f"[DOWNLOAD] Clip {clip_index}: retrying without --download-sections...")
        if _attempt_with_retry(None, "full"):
            return _find_output()

        print(f"[DOWNLOAD] Clip {clip_index}: all download attempts failed for {video_url}")

    except subprocess.TimeoutExpired:
        print(f"[DOWNLOAD] Clip {clip_index}: download timed out for {video_url}")
    except Exception as e:
        print(f"[DOWNLOAD] Clip {clip_index}: unexpected error: {e}")

    return None


def search_single_visual(
    query: str,
    exclude_ids: list[str] | None = None,
    count: int = 5,
) -> list[dict]:
    """Search YouTube for a single visual, filtering out blacklisted video_ids.

    Requests 4x the desired count so the blacklist filter has room to operate,
    then returns the top `count` non-excluded results.
    """
    if not query:
        return []
    excluded = set(exclude_ids or [])
    raw = search_youtube(query, max_results=count * 4)
    filtered = [r for r in raw if r.get("video_id") not in excluded]
    return filtered[:count]


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
