"""Style definitions for video pipeline - film eras and editing sub-styles.

Each style is a dict of parameters consumed by different pipeline steps:
- ffmpeg_filters: applied in video_editor.combine_clips()
- prompt_modifier: injected into script_generator and thumbnail prompts
- subtitle_*: override subtitle rendering
- thumbnail_style: injected into DALL-E / Gemini thumbnail prompts
"""

from __future__ import annotations


STYLES: dict[str, dict] = {
    "vintage": {
        "label": "Vintage",
        "description": "Nostalgisch, filmkorrel, warme sepia tinten (jaren 60-70)",
        "ffmpeg_filters": "curves=vintage,noise=alls=20:allf=t+u",
        "prompt_modifier": (
            "nostalgic vintage style, film grain, warm sepia tones, "
            "1960s-1970s aesthetic, muted colors, soft focus"
        ),
        "subtitle_color": "#F5DEB3",
        "subtitle_bg_color": "#3B2F1E",
        "thumbnail_style": "vintage film poster, aged look, warm tones",
    },
    "80s": {
        "label": "80's",
        "description": "Neon, hoge saturatie, synth-wave esthetiek",
        "ffmpeg_filters": "eq=saturation=1.5:contrast=1.3,colorbalance=rs=0.1:gs=-0.05:bs=0.15",
        "prompt_modifier": (
            "1980s retro style, neon colors, high saturation, "
            "synthwave aesthetic, VHS look, bold and vibrant"
        ),
        "subtitle_color": "#FF69B4",
        "subtitle_bg_color": "#1A0033",
        "thumbnail_style": "80s neon retro, synthwave colors, bold gradients",
    },
    "90s": {
        "label": "90's",
        "description": "Grunge, licht desaturatie, raw esthetiek",
        "ffmpeg_filters": "eq=saturation=0.85:contrast=1.1,unsharp=5:5:0.8",
        "prompt_modifier": (
            "1990s grunge style, slightly desaturated, raw footage feel, "
            "gritty urban aesthetic, handheld camera look"
        ),
        "subtitle_color": "#E0E0E0",
        "subtitle_bg_color": "#2B2B2B",
        "thumbnail_style": "90s grunge aesthetic, raw, urban, slightly dark",
    },
    "2000s": {
        "label": "2000's",
        "description": "Hoge contrast, blauwe tint, cinematic look",
        "ffmpeg_filters": "eq=contrast=1.2:brightness=0.02,colorbalance=rs=-0.05:bs=0.1",
        "prompt_modifier": (
            "early 2000s cinematic style, teal and orange color grading, "
            "high contrast, polished digital look, blockbuster aesthetic"
        ),
        "subtitle_color": "#FFFFFF",
        "subtitle_bg_color": "#0A1628",
        "thumbnail_style": "2000s cinematic, teal and orange, high contrast",
    },
    "modern": {
        "label": "Modern",
        "description": "Clean, helder, professioneel (standaard)",
        "ffmpeg_filters": "",
        "prompt_modifier": (
            "modern clean style, professional, sharp and bright, "
            "contemporary cinematic look"
        ),
        "subtitle_color": "#FFFFFF",
        "subtitle_bg_color": "#000000",
        "thumbnail_style": "modern professional, clean, high quality",
    },
}


SUB_STYLES: dict[str, dict] = {
    "minimalistisch": {
        "label": "Minimalistisch",
        "description": "Rustige pacing, weinig cuts, clean look",
        "clip_duration_override": 5.0,
        "subtitle_style": "minimal",
        "prompt_modifier": "minimalist, clean, simple, lots of breathing room",
        "editing_pace": "slow",
    },
    "hyper_edit": {
        "label": "Hyper Edit / Fast Pace",
        "description": "Snelle cuts, energiek, veel beweging",
        "clip_duration_override": 1.5,
        "subtitle_style": "large_caption",
        "prompt_modifier": "fast-paced, energetic, rapid cuts, high energy, dynamic",
        "editing_pace": "fast",
    },
    "gaming": {
        "label": "Gaming",
        "description": "Gaming esthetiek, bold kleuren, hype energy",
        "clip_duration_override": 2.0,
        "subtitle_style": "large_caption",
        "prompt_modifier": "gaming style, bold colors, hype energy, esports aesthetic",
        "editing_pace": "fast",
    },
    "cartoon": {
        "label": "Cartoon",
        "description": "Speels, animatie-achtig, bright kleuren",
        "clip_duration_override": 3.0,
        "subtitle_style": "default",
        "prompt_modifier": "cartoon style, playful, animated feel, bright vivid colors",
        "editing_pace": "medium",
    },
    "documentaire": {
        "label": "Documentaire",
        "description": "Serieus, informatief, rustige opbouw",
        "clip_duration_override": 4.0,
        "subtitle_style": "minimal",
        "prompt_modifier": "documentary style, serious, informative, measured pacing",
        "editing_pace": "slow",
    },
    "slow_pacing": {
        "label": "Slow Pacing",
        "description": "Traag, contemplatief, sfeerbeelden",
        "clip_duration_override": 6.0,
        "subtitle_style": "minimal",
        "prompt_modifier": "slow paced, contemplative, atmospheric, cinematic wide shots",
        "editing_pace": "slow",
    },
    "dark_tone": {
        "label": "Dark Tone",
        "description": "Donker, mysterieus, spanning",
        "clip_duration_override": 3.0,
        "subtitle_style": "default",
        "prompt_modifier": "dark tone, mysterious, suspenseful, moody lighting, shadows",
        "editing_pace": "medium",
        "ffmpeg_filters_extra": "eq=brightness=-0.05:contrast=1.2:saturation=0.8",
    },
    "hypnotic": {
        "label": "Hypnotisch",
        "description": "Repetitief, tranceachtig, seamless loops",
        "clip_duration_override": 4.0,
        "subtitle_style": "minimal",
        "prompt_modifier": "hypnotic, trance-like, repetitive patterns, seamless, ambient",
        "editing_pace": "slow",
    },
}


def get_style(name: str) -> dict:
    """Get a style definition by name, falling back to 'modern'."""
    return STYLES.get(name, STYLES["modern"])


def get_sub_style(name: str) -> dict | None:
    """Get a sub-style definition by name, or None if not found."""
    return SUB_STYLES.get(name)


def get_ffmpeg_filters(style_name: str, sub_style_name: str = "") -> str:
    """Build combined FFmpeg filter string from style + sub-style."""
    style = get_style(style_name)
    filters = style.get("ffmpeg_filters", "")

    if sub_style_name:
        sub = get_sub_style(sub_style_name)
        if sub and sub.get("ffmpeg_filters_extra"):
            extra = sub["ffmpeg_filters_extra"]
            filters = f"{filters},{extra}" if filters else extra

    return filters


def get_prompt_modifier(style_name: str, sub_style_name: str = "") -> str:
    """Build combined prompt modifier from style + sub-style."""
    style = get_style(style_name)
    modifier = style.get("prompt_modifier", "")

    if sub_style_name:
        sub = get_sub_style(sub_style_name)
        if sub and sub.get("prompt_modifier"):
            modifier = f"{modifier}. {sub['prompt_modifier']}"

    return modifier


def get_effective_clip_duration(
    base_duration: float, sub_style_name: str = ""
) -> float:
    """Get effective clip duration, with sub-style override if applicable."""
    if sub_style_name:
        sub = get_sub_style(sub_style_name)
        if sub and "clip_duration_override" in sub:
            return sub["clip_duration_override"]
    return base_duration
