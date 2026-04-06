"""Analyze video clips with Gemini and match to script scenes."""
import json
import time
from pathlib import Path

from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-pro"

# Simple in-memory cache: clip_path -> analysis result
_analysis_cache: dict[str, dict] = {}


def analyze_clip(clip_path: Path) -> dict:
    """Upload a clip to Gemini and get a visual description + tags.

    Returns {"path": str, "description": str, "tags": [str]}
    """
    cache_key = str(clip_path)
    if cache_key in _analysis_cache:
        return _analysis_cache[cache_key]

    if not clip_path.exists():
        return {"path": cache_key, "description": "Bestand niet gevonden", "tags": []}

    try:
        video_file = client.files.upload(file=clip_path)

        # Wait for file processing to complete
        while video_file.state.name == "PROCESSING":
            time.sleep(1)
            video_file = client.files.get(name=video_file.name)

        if video_file.state.name == "FAILED":
            return {"path": cache_key, "description": "Video upload mislukt", "tags": []}

        response = client.models.generate_content(
            model=MODEL,
            contents=[
                video_file,
                (
                    "Describe what you see in this video clip in 2-3 sentences. "
                    "Focus on the main subject, action, and setting. "
                    "Also list 5-10 relevant single-word tags.\n\n"
                    "Respond in this exact JSON format:\n"
                    '{"description": "...", "tags": ["tag1", "tag2", ...]}'
                ),
            ],
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        data = json.loads(text)
        result = {
            "path": cache_key,
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
        }

        # Clean up uploaded file
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass

        _analysis_cache[cache_key] = result
        return result

    except json.JSONDecodeError:
        # Gemini returned non-JSON; extract what we can
        result = {
            "path": cache_key,
            "description": response.text.strip()[:300] if response else "Analyse mislukt",
            "tags": [],
        }
        _analysis_cache[cache_key] = result
        return result
    except Exception as e:
        return {"path": cache_key, "description": f"Fout bij analyse: {e}", "tags": []}


def match_clips_to_scenes(clips: list[dict], scenes: list[dict]) -> list[dict]:
    """Use Gemini to find the optimal clip-to-scene matching.

    Args:
        clips: List of analyzed clips with "path", "description", "tags".
        scenes: List of script scenes with "visuals" containing "line", "description".

    Returns:
        List of {"scene_index": int, "clip_path": str, "confidence": float, "reason": str}
    """
    if not clips or not scenes:
        return []

    # Build the prompt with scene descriptions and clip analyses
    scene_lines = []
    for i, scene in enumerate(scenes):
        visuals = scene.get("visuals", [])
        lines = [v.get("line", "") for v in visuals]
        descs = [v.get("description", "") for v in visuals]
        scene_lines.append(
            f"Scene {i}: lines={lines}, visual_descriptions={descs}"
        )

    clip_lines = []
    for j, clip in enumerate(clips):
        clip_lines.append(
            f"Clip {j} ({Path(clip['path']).name}): {clip['description']} | tags: {clip['tags']}"
        )

    prompt = (
        "You are matching downloaded video clips to script scenes for a YouTube video.\n\n"
        "SCENES:\n" + "\n".join(scene_lines) + "\n\n"
        "AVAILABLE CLIPS:\n" + "\n".join(clip_lines) + "\n\n"
        "For each scene, pick the single best matching clip based on visual content similarity. "
        "A clip can only be assigned to one scene. If there are more scenes than clips, "
        "some scenes may share clips.\n\n"
        "Respond with a JSON array. Each element:\n"
        '{"scene_index": <int>, "clip_index": <int>, "confidence": <0.0-1.0>, "reason": "<short Dutch explanation>"}\n\n'
        "Return ONLY valid JSON, no markdown."
    )

    try:
        response = client.models.generate_content(model=MODEL, contents=[prompt])
        text = response.text.strip()

        # Strip code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        raw_matches = json.loads(text)

        # Map clip_index back to clip_path
        matches = []
        for m in raw_matches:
            ci = m.get("clip_index", 0)
            if 0 <= ci < len(clips):
                matches.append({
                    "scene_index": m.get("scene_index", 0),
                    "clip_path": clips[ci]["path"],
                    "clip_index": ci,
                    "confidence": round(float(m.get("confidence", 0.5)), 2),
                    "reason": m.get("reason", ""),
                })

        return matches

    except Exception as e:
        print(f"Match error: {e}")
        # Fallback: assign clips sequentially
        return [
            {
                "scene_index": i,
                "clip_path": clips[i % len(clips)]["path"],
                "clip_index": i % len(clips),
                "confidence": 0.3,
                "reason": "Automatische toewijzing (matching mislukt)",
            }
            for i in range(len(scenes))
        ]


def analyze_and_match(clips_dir: Path, scenes: list[dict]) -> dict:
    """Analyze all clips in a directory and match them to scenes.

    Returns {"clips": [...analyzed...], "matches": [...matched...]}
    """
    clip_paths = sorted(clips_dir.glob("clip_*.mp4"))
    if not clip_paths:
        return {"clips": [], "matches": [], "error": "Geen clips gevonden in de map"}

    # Analyze each clip
    analyzed = []
    for cp in clip_paths:
        result = analyze_clip(cp)
        analyzed.append(result)

    # Match to scenes
    matches = match_clips_to_scenes(analyzed, scenes)

    return {"clips": analyzed, "matches": matches}
