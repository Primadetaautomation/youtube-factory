"""Combine clips + voiceover + subtitles into final video using FFmpeg."""
import subprocess
import struct
import tempfile
from pathlib import Path
from config import OUTPUT_DIR, TEMP_DIR
from steps.pipeline_config import PipelineConfig
from steps.style_registry import get_ffmpeg_filters


def combine_clips(clip_paths: list[Path], target_duration: float, *, config=None) -> Path:
    """Concatenate clips into a single video matching target duration."""
    if not clip_paths:
        raise ValueError("No clips to combine")

    if config is None:
        config = PipelineConfig()

    w, h = config.dimensions
    clip_duration = target_duration / len(clip_paths)
    combined = TEMP_DIR / "combined_clips.mp4"

    # Get style color grading filters
    style_filters = get_ffmpeg_filters(config.style, config.sub_style)

    filter_parts = []
    inputs = []
    for i, clip in enumerate(clip_paths):
        inputs.extend(["-i", str(clip)])
        base_filter = (
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,trim=0:{clip_duration},setpts=PTS-STARTPTS"
        )
        if style_filters:
            base_filter += f",{style_filters}"
        base_filter += f"[v{i}]"
        filter_parts.append(base_filter)

    concat_inputs = "".join(f"[v{i}]" for i in range(len(clip_paths)))
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[outv]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", config.quality_preset, "-crf", str(config.quality_crf),
        str(combined),
    ]

    subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if not combined.exists():
        raise RuntimeError("Failed to combine clips")

    return combined


def add_audio_to_video(video_path: Path, audio_path: Path, output_name: str) -> Path:
    """Merge video with voiceover audio."""
    output_path = OUTPUT_DIR / f"{output_name}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if not output_path.exists():
        raise RuntimeError("Failed to merge audio with video")

    return output_path


def burn_subtitles(video_path: Path, srt_path: Path, output_name: str, *, config=None) -> Path:
    """Burn subtitles into video by generating overlay frames with Pillow.

    Creates a transparent PNG per subtitle, overlays each via FFmpeg concat + overlay.
    Works without libass/drawtext/freetype.
    """
    from PIL import Image, ImageDraw, ImageFont

    if config is None:
        config = PipelineConfig()

    w, h = config.dimensions
    font_size = config.subtitle_font_size

    # Parse SRT
    srt_text = srt_path.read_text(encoding="utf-8")
    subs = _parse_srt(srt_text)

    if not subs:
        return video_path

    # Get video duration & fps
    duration = _get_video_duration(video_path)
    if duration <= 0:
        return video_path

    fps = 30
    total_frames = int(duration * fps)

    # Generate subtitle overlay frames as raw video
    overlay_dir = TEMP_DIR / "sub_frames"
    overlay_dir.mkdir(exist_ok=True)

    # Clean old frames
    for f in overlay_dir.glob("*.png"):
        f.unlink()

    # Find a font
    font = None
    for font_path in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Create a subtitle video using frame-by-frame approach with pipes
    output_path = OUTPUT_DIR / f"{output_name}_sub.mp4"

    # Build FFmpeg command that reads raw RGBA frames from stdin
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{w}x{h}",
        "-r", str(fps),
        "-i", "pipe:0",
        "-i", str(video_path),
        "-filter_complex", "[1:v][0:v]overlay=0:0[outv]",
        "-map", "[outv]",
        "-map", "1:a?",
        "-c:v", "libx264", "-preset", config.quality_preset, "-crf", str(config.quality_crf),
        "-c:a", "copy",
        "-shortest",
        str(output_path),
    ]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Compute subtitle Y position based on config
    line_height = int(font_size * 1.15)
    max_wrap_width = int(w * 0.85)

    try:
        for frame_num in range(total_frames):
            t = frame_num / fps

            # Find active subtitle
            text = ""
            for sub in subs:
                if sub["start"] <= t < sub["end"]:
                    text = sub["text"]
                    break

            # Create transparent frame
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

            if text:
                draw = ImageDraw.Draw(img)
                lines = _wrap_text(text, font, max_wrap_width, draw)
                total_text_height = len(lines) * line_height

                # Position based on config
                if config.subtitle_position == "center":
                    y_start = (h - total_text_height) // 2
                elif config.subtitle_position == "top":
                    y_start = 80
                else:  # bottom (default)
                    y_start = h - 120 - total_text_height

                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (w - tw) // 2

                    # Background box
                    pad = 10
                    draw.rectangle(
                        [x - pad, y_start - pad, x + tw + pad, y_start + line_height - pad],
                        fill=(0, 0, 0, 180),
                    )
                    # Text
                    draw.text((x, y_start), line, fill=(255, 255, 255, 255), font=font)
                    y_start += line_height

            # Write raw RGBA bytes
            proc.stdin.write(img.tobytes())

        proc.stdin.close()
        proc.wait(timeout=120)

    except Exception as e:
        print(f"  Subtitle burn error: {e}")
        proc.kill()
        if output_path.exists():
            output_path.unlink()
        return video_path

    if output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    return video_path


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT text into list of {start, end, text}."""
    subs = []
    blocks = srt_text.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            times = lines[1].split(" --> ")
            if len(times) == 2:
                subs.append({
                    "start": _srt_to_seconds(times[0].strip()),
                    "end": _srt_to_seconds(times[1].strip()),
                    "text": " ".join(lines[2:]).strip(),
                })
    return subs


def _srt_to_seconds(ts: str) -> float:
    """Convert SRT timestamp to seconds."""
    parts = ts.replace(",", ".").split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def _get_video_duration(path: Path) -> float:
    """Get video duration in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def render_hook_preview(video_path: Path, duration_seconds: float) -> Path:
    """Extract the first N seconds of a video as a hook preview."""
    output_path = OUTPUT_DIR / "hook_preview.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if not output_path.exists():
        raise RuntimeError("Failed to render hook preview")

    return output_path
