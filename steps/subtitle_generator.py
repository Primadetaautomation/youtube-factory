"""Generate SRT subtitles from word-level timestamps."""
from pathlib import Path
from config import OUTPUT_DIR


def generate_srt_from_timestamps(word_timestamps: list[dict], output_name: str = "subtitles") -> Path:
    """Create SRT from word-level timestamps, grouped per sentence.

    Groups words into sentences (split on . ! ? or every ~8 words).
    Each sentence appears and disappears exactly when spoken.
    """
    if not word_timestamps:
        return _write_empty_srt(output_name)

    # Group words into sentences
    sentences = []
    current_words = []
    current_start = None

    for wt in word_timestamps:
        word = wt["word"]

        if current_start is None:
            current_start = wt["start"]

        current_words.append(word)

        # End sentence on punctuation or every 8 words
        is_sentence_end = (
            word.endswith((".", "!", "?", "…"))
            or len(current_words) >= 8
        )

        if is_sentence_end:
            sentences.append({
                "text": " ".join(current_words),
                "start": current_start,
                "end": wt["end"],
            })
            current_words = []
            current_start = None

    # Remaining words
    if current_words:
        sentences.append({
            "text": " ".join(current_words),
            "start": current_start,
            "end": word_timestamps[-1]["end"],
        })

    # Write SRT
    srt_lines = []
    for i, sent in enumerate(sentences):
        srt_lines.append(f"{i + 1}")
        srt_lines.append(f"{_format_time(sent['start'])} --> {_format_time(sent['end'])}")
        srt_lines.append(sent["text"])
        srt_lines.append("")

    output_path = OUTPUT_DIR / f"{output_name}.srt"
    output_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return output_path


def generate_srt(script_text: str, audio_duration: float, output_name: str = "subtitles") -> Path:
    """Fallback: generate SRT without timestamps (evenly distributed)."""
    lines = [l.strip() for l in script_text.split("\n") if l.strip()]
    if not lines:
        return _write_empty_srt(output_name)

    # Group short lines
    chunks = []
    current = ""
    for line in lines:
        if len(current.split()) + len(line.split()) <= 8:
            current = f"{current} {line}".strip() if current else line
        else:
            if current:
                chunks.append(current)
            current = line
    if current:
        chunks.append(current)

    chunk_duration = audio_duration / len(chunks)
    srt_lines = []
    for i, chunk in enumerate(chunks):
        start = i * chunk_duration
        end = (i + 1) * chunk_duration
        srt_lines.append(f"{i + 1}")
        srt_lines.append(f"{_format_time(start)} --> {_format_time(end)}")
        srt_lines.append(chunk)
        srt_lines.append("")

    output_path = OUTPUT_DIR / f"{output_name}.srt"
    output_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return output_path


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_empty_srt(output_name: str) -> Path:
    output_path = OUTPUT_DIR / f"{output_name}.srt"
    output_path.write_text("1\n00:00:00,000 --> 00:00:01,000\n \n", encoding="utf-8")
    return output_path
