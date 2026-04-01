"""Tests for PipelineConfig dataclass."""

import pytest

from steps.pipeline_config import PipelineConfig, _compute_dimensions


class TestComputeDimensions:
    def test_standard_16_9_1080p(self):
        assert _compute_dimensions("1080p", "16:9") == (1920, 1080)

    def test_standard_16_9_720p(self):
        assert _compute_dimensions("720p", "16:9") == (1280, 720)

    def test_standard_16_9_4k(self):
        assert _compute_dimensions("4k", "16:9") == (3840, 2160)

    def test_vertical_9_16_1080p(self):
        assert _compute_dimensions("1080p", "9:16") == (1080, 1920)

    def test_vertical_9_16_720p(self):
        assert _compute_dimensions("720p", "9:16") == (720, 1280)

    def test_square_1_1_1080p(self):
        assert _compute_dimensions("1080p", "1:1") == (1080, 1080)

    def test_square_1_1_720p(self):
        assert _compute_dimensions("720p", "1:1") == (720, 720)

    def test_invalid_resolution_falls_back(self):
        w, h = _compute_dimensions("invalid", "16:9")
        assert (w, h) == (1920, 1080)

    def test_invalid_aspect_ratio_falls_back(self):
        w, h = _compute_dimensions("1080p", "invalid")
        assert (w, h) == (1920, 1080)


class TestPipelineConfigDefaults:
    def test_defaults(self, default_config):
        assert default_config.aspect_ratio == "16:9"
        assert default_config.resolution == "1080p"
        assert default_config.style == "modern"
        assert default_config.sub_style == ""
        assert default_config.max_clip_duration == 3.0
        assert default_config.content_type == "standard"
        assert default_config.quality_crf == 23
        assert default_config.quality_preset == "fast"

    def test_dimensions_property(self, default_config):
        assert default_config.width == 1920
        assert default_config.height == 1080

    def test_dimensions_vertical(self):
        cfg = PipelineConfig(aspect_ratio="9:16")
        assert cfg.width == 1080
        assert cfg.height == 1920


class TestPipelineConfigSerialization:
    def test_to_dict(self, default_config):
        d = default_config.to_dict()
        assert isinstance(d, dict)
        assert d["aspect_ratio"] == "16:9"
        assert d["quality_crf"] == 23

    def test_from_dict_roundtrip(self, default_config):
        d = default_config.to_dict()
        restored = PipelineConfig.from_dict(d)
        assert restored.to_dict() == d

    def test_from_dict_ignores_unknown_keys(self):
        cfg = PipelineConfig.from_dict({"aspect_ratio": "9:16", "unknown_field": True})
        assert cfg.aspect_ratio == "9:16"

    def test_from_dict_empty(self):
        cfg = PipelineConfig.from_dict({})
        assert cfg.aspect_ratio == "16:9"  # defaults

    def test_from_dict_partial(self):
        cfg = PipelineConfig.from_dict({"style": "vintage", "quality_crf": 18})
        assert cfg.style == "vintage"
        assert cfg.quality_crf == 18
        assert cfg.resolution == "1080p"  # default for unset


class TestShortsDefaults:
    def test_apply_shorts_defaults(self, shorts_config):
        assert shorts_config.aspect_ratio == "9:16"
        assert shorts_config.content_type == "shorts"
        assert shorts_config.subtitle_style == "large_caption"
        assert shorts_config.subtitle_font_size == 72
        assert shorts_config.subtitle_position == "center"
        assert shorts_config.max_clip_duration == 2.0

    def test_shorts_dimensions(self, shorts_config):
        assert shorts_config.width == 1080
        assert shorts_config.height == 1920
