"""Run the full pipeline for multiple topics (batch/week planner)."""
from datetime import datetime, timedelta
from pathlib import Path
from config import get_project_dir, OUTPUT_DIR


def run_batch_pipeline(
    topics: list[dict],
    start_date: str,
    publish_time: str = "09:00",
) -> list[dict]:
    """Run pipeline for each topic with scheduled publishing.

    topics: list of {"topic": str, "duration": int}
    start_date: ISO date string (e.g. '2026-03-30')
    publish_time: time to publish each day (e.g. '09:00')

    Returns list of results per topic.
    """
    from steps.script_generator import generate_script
    from steps.voiceover import generate_voiceover_with_timestamps
    from steps.clip_finder import search_clips_for_scenes, download_clip
    from steps.video_editor import combine_clips, add_audio_to_video, burn_subtitles
    from steps.subtitle_generator import generate_srt_from_timestamps
    from steps.thumbnail import generate_thumbnail
    from steps.metadata import generate_metadata

    base_date = datetime.fromisoformat(start_date)
    results = []

    for i, item in enumerate(topics):
        topic = item["topic"]
        duration = item.get("duration", 4)
        safe_name = topic.lower().replace(" ", "_")[:30]
        publish_dt = base_date + timedelta(days=i)
        publish_at = f"{publish_dt.strftime('%Y-%m-%d')}T{publish_time}:00Z"

        result = {
            "topic": topic,
            "day": i + 1,
            "publish_at": publish_at,
            "status": "pending",
            "error": None,
            "video_file": None,
            "thumbnail_file": None,
        }

        try:
            project_dir = get_project_dir(topic)
            clips_dir = project_dir / "clips"

            # 1. Script
            script_data = generate_script(topic, duration)

            # 2. Voiceover with timestamps
            vo_result = generate_voiceover_with_timestamps(script_data["script"], safe_name)
            audio_duration = vo_result["duration"]
            word_timestamps = vo_result["word_timestamps"]

            # 3. Search & download clips (auto-select first result)
            visuals = search_clips_for_scenes(script_data["scenes"], results_per_query=1)
            for vi, visual in enumerate(visuals):
                options = visual.get("options", [])
                if options:
                    download_clip(options[0]["url"], vi, clips_dir=clips_dir)

            # 4. Combine clips
            clip_paths = sorted(clips_dir.glob("clip_*.mp4"))
            if not clip_paths:
                result["status"] = "error"
                result["error"] = "No clips downloaded"
                results.append(result)
                continue

            combined = combine_clips(clip_paths, audio_duration)
            audio_path = OUTPUT_DIR / f"{safe_name}.mp3"
            final = add_audio_to_video(combined, audio_path, safe_name)

            # 5. Subtitles
            if word_timestamps:
                srt_path = generate_srt_from_timestamps(word_timestamps, safe_name)
                final = burn_subtitles(final, srt_path, safe_name)

            # 6. Thumbnail & metadata
            meta = generate_metadata(topic, script_data["script"])
            thumb = generate_thumbnail(topic, meta["title"], safe_name)

            result["status"] = "ready"
            result["video_file"] = final.name
            result["thumbnail_file"] = thumb.name
            result["title"] = meta["title"]
            result["description"] = meta["description"]
            result["tags"] = meta["tags"]

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        results.append(result)

    return results
