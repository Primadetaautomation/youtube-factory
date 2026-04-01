"""Generate voiceover audio with word-level timestamps using ElevenLabs."""
import base64
import json
from pathlib import Path
from elevenlabs import ElevenLabs
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OUTPUT_DIR


def generate_voiceover(script_text: str, output_name: str = "voiceover") -> Path:
    """Generate voiceover from script text, return path to audio file."""
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    audio_generator = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=script_text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    output_path = OUTPUT_DIR / f"{output_name}.mp3"
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    return output_path


def generate_voiceover_with_timestamps(
    script_text: str,
    output_name: str = "voiceover",
    speed: float = 1.0,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    voice_id: str = "",
) -> dict:
    """Generate voiceover with word-level timestamps for subtitle sync."""
    from elevenlabs import VoiceSettings
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Clamp speed to ElevenLabs supported range
    speed = max(0.5, min(2.0, speed))
    selected_voice = voice_id or ELEVENLABS_VOICE_ID

    response = client.text_to_speech.convert_with_timestamps(
        voice_id=selected_voice,
        text=script_text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=True,
        ),
    )

    audio_bytes = b""
    word_timestamps = []

    for key, val in response:
        if key == "audio_base_64" and isinstance(val, str):
            audio_bytes += base64.b64decode(val)

        elif key == "alignment" and hasattr(val, "characters"):
            chars = val.characters
            starts = val.character_start_times_seconds
            ends = val.character_end_times_seconds

            # Build words from characters
            current_word = ""
            word_start = None

            for i, char in enumerate(chars):
                if char == " " or i == len(chars) - 1:
                    if i == len(chars) - 1 and char != " ":
                        current_word += char

                    if current_word.strip():
                        word_end = ends[i - 1] if char == " " else ends[i]
                        word_timestamps.append({
                            "word": current_word.strip(),
                            "start": word_start,
                            "end": word_end,
                        })
                    current_word = ""
                    word_start = None
                else:
                    if word_start is None:
                        word_start = starts[i]
                    current_word += char

    # Save audio
    output_path = OUTPUT_DIR / f"{output_name}.mp3"
    output_path.write_bytes(audio_bytes)

    # Apply speed adjustment with ffmpeg (preserves pitch)
    if speed != 1.0:
        import subprocess
        sped_path = OUTPUT_DIR / f"{output_name}_sped.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-filter:a", f"atempo={speed}",
            "-vn", str(sped_path),
        ], capture_output=True, timeout=30)
        if sped_path.exists():
            sped_path.rename(output_path)
        # Adjust timestamps for speed
        word_timestamps = [
            {"word": w["word"], "start": w["start"] / speed, "end": w["end"] / speed}
            for w in word_timestamps
        ]

    # Save timestamps for debugging
    timestamps_path = OUTPUT_DIR / f"{output_name}_timestamps.json"
    timestamps_path.write_text(json.dumps(word_timestamps, indent=2))

    duration = get_audio_duration(output_path)

    return {
        "audio_path": output_path,
        "duration": duration,
        "word_timestamps": word_timestamps,
    }


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds."""
    from pydub import AudioSegment
    audio = AudioSegment.from_mp3(str(audio_path))
    return len(audio) / 1000.0
