"""Central pipeline configuration that flows through all step functions."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


# Resolution maps: name -> (width, height)
RESOLUTION_MAP = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}

# Aspect ratio maps: name -> (width, height) multiplier base
ASPECT_RATIO_MAP = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "1:1": (1, 1),
}


def _compute_dimensions(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    """Compute output dimensions from resolution + aspect ratio.

    For 16:9 at 1080p -> 1920x1080
    For 9:16 at 1080p -> 1080x1920
    For 1:1  at 1080p -> 1080x1080
    """
    if resolution not in RESOLUTION_MAP:
        resolution = "1080p"
    if aspect_ratio not in ASPECT_RATIO_MAP:
        aspect_ratio = "16:9"

    base_w, base_h = RESOLUTION_MAP[resolution]
    ar_w, ar_h = ASPECT_RATIO_MAP[aspect_ratio]

    if aspect_ratio == "16:9":
        return base_w, base_h
    elif aspect_ratio == "9:16":
        return base_h, base_w
    else:  # 1:1
        short_side = min(base_w, base_h)
        return short_side, short_side


@dataclass
class PipelineConfig:
    """Configuration object that flows through the entire video pipeline."""

    # Format
    aspect_ratio: str = "16:9"
    resolution: str = "1080p"

    # Style
    style: str = "modern"
    sub_style: str = ""

    # Editing
    max_clip_duration: float = 3.0
    transition: str = "cut"

    # Subtitles
    subtitle_style: str = "default"
    subtitle_font_size: int = 48
    subtitle_position: str = "bottom"

    # Content type
    content_type: str = "standard"

    # Encoding quality
    quality_crf: int = 23
    quality_preset: str = "fast"

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return (width, height) for the current config."""
        return _compute_dimensions(self.resolution, self.aspect_ratio)

    @property
    def width(self) -> int:
        return self.dimensions[0]

    @property
    def height(self) -> int:
        return self.dimensions[1]

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transport."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PipelineConfig:
        """Create from dict, ignoring unknown keys."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def apply_shorts_defaults(self) -> None:
        """Apply sensible defaults for short-form content."""
        self.aspect_ratio = "9:16"
        self.content_type = "shorts"
        self.subtitle_style = "large_caption"
        self.subtitle_font_size = 72
        self.subtitle_position = "center"
        self.max_clip_duration = 2.0
