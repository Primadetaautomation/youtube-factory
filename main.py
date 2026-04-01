"""YouTube Factory - Automated video creation pipeline."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from steps.script_generator import generate_script
from steps.voiceover import generate_voiceover, get_audio_duration
from steps.clip_finder import download_all_clips
from steps.video_editor import combine_clips, add_audio_to_video
from steps.thumbnail import generate_thumbnail
from steps.metadata import generate_metadata
from steps.uploader import upload_video


def run_pipeline(topic: str, upload: bool = True, privacy: str = "private"):
    """Run the full video creation pipeline."""
    safe_name = topic.lower().replace(" ", "_")[:30]

    print(f"\n{'='*50}")
    print(f"  YouTube Factory: {topic}")
    print(f"{'='*50}\n")

    # Step 1: Generate script
    print("[1/7] Generating script...")
    script_data = generate_script(topic)
    script_text = script_data["script"]
    scenes = script_data["scenes"]
    print(f"  Script: {len(script_text)} chars, {len(scenes)} scenes")

    # Step 2: Generate voiceover
    print("[2/7] Generating voiceover...")
    audio_path = generate_voiceover(script_text, safe_name)
    audio_duration = get_audio_duration(audio_path)
    print(f"  Audio: {audio_duration:.1f}s")

    # Step 3: Download clips
    print("[3/7] Downloading clips...")
    clips = download_all_clips(scenes)
    print(f"  Downloaded: {len(clips)} clips")

    if not clips:
        print("ERROR: No clips downloaded. Cannot continue.")
        return

    # Step 4: Combine clips
    print("[4/7] Combining clips...")
    combined_video = combine_clips(clips, audio_duration)
    print(f"  Combined: {combined_video}")

    # Step 5: Add voiceover
    print("[5/7] Adding voiceover...")
    final_video = add_audio_to_video(combined_video, audio_path, safe_name)
    print(f"  Final: {final_video}")

    # Step 6: Thumbnail
    print("[6/7] Generating thumbnail...")
    metadata = generate_metadata(topic, script_text)
    thumb_path = generate_thumbnail(topic, metadata["title"], safe_name)
    print(f"  Thumbnail: {thumb_path}")

    # Step 7: Upload
    if upload:
        print("[7/7] Uploading to YouTube...")
        video_id = upload_video(
            final_video,
            metadata["title"],
            metadata["description"],
            metadata["tags"],
            thumb_path,
            privacy,
        )
        print(f"  Uploaded: https://youtu.be/{video_id}")
    else:
        print("[7/7] Skipping upload (--no-upload)")
        print(f"\n  Video: {final_video}")
        print(f"  Thumbnail: {thumb_path}")
        print(f"  Title: {metadata['title']}")

    print(f"\n{'='*50}")
    print("  Done!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Factory")
    parser.add_argument("topic", help="Video topic (e.g. 'Carlos Alcaraz')")
    parser.add_argument("--no-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = parser.parse_args()

    run_pipeline(args.topic, upload=not args.no_upload, privacy=args.privacy)
