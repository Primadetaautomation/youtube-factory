"""Tests for the style registry."""

import pytest

from steps.style_registry import (
    STYLES,
    SUB_STYLES,
    get_style,
    get_sub_style,
    get_ffmpeg_filters,
    get_prompt_modifier,
    get_effective_clip_duration,
)


class TestStylesCompleteness:
    def test_all_expected_styles_exist(self):
        expected = {"vintage", "80s", "90s", "2000s", "modern"}
        assert set(STYLES.keys()) == expected

    def test_all_styles_have_required_keys(self):
        required = {"label", "ffmpeg_filters", "prompt_modifier", "thumbnail_style"}
        for name, style in STYLES.items():
            missing = required - set(style.keys())
            assert not missing, f"Style '{name}' missing keys: {missing}"

    def test_all_expected_sub_styles_exist(self):
        expected = {
            "minimalistisch", "hyper_edit", "gaming", "cartoon",
            "documentaire", "slow_pacing", "dark_tone", "hypnotic",
        }
        assert set(SUB_STYLES.keys()) == expected

    def test_all_sub_styles_have_required_keys(self):
        required = {"label", "clip_duration_override", "subtitle_style", "prompt_modifier"}
        for name, sub in SUB_STYLES.items():
            missing = required - set(sub.keys())
            assert not missing, f"Sub-style '{name}' missing keys: {missing}"


class TestGetStyle:
    def test_get_existing_style(self):
        s = get_style("vintage")
        assert s["label"] == "Vintage"

    def test_get_unknown_style_returns_modern(self):
        s = get_style("nonexistent")
        assert s["label"] == "Modern"

    def test_modern_has_empty_filters(self):
        s = get_style("modern")
        assert s["ffmpeg_filters"] == ""


class TestGetSubStyle:
    def test_get_existing_sub_style(self):
        s = get_sub_style("hyper_edit")
        assert s is not None
        assert s["clip_duration_override"] == 1.5

    def test_get_unknown_sub_style_returns_none(self):
        assert get_sub_style("nonexistent") is None


class TestGetFfmpegFilters:
    def test_style_only(self):
        f = get_ffmpeg_filters("vintage")
        assert "curves=vintage" in f

    def test_modern_returns_empty(self):
        assert get_ffmpeg_filters("modern") == ""

    def test_style_with_sub_style_extra(self):
        f = get_ffmpeg_filters("modern", "dark_tone")
        assert "brightness" in f

    def test_style_with_sub_style_no_extra(self):
        f = get_ffmpeg_filters("vintage", "minimalistisch")
        # minimalistisch has no ffmpeg_filters_extra, so just vintage filters
        assert "curves=vintage" in f

    def test_combined_filters(self):
        f = get_ffmpeg_filters("80s", "dark_tone")
        assert "saturation=1.5" in f
        assert "brightness" in f


class TestGetPromptModifier:
    def test_style_only(self):
        p = get_prompt_modifier("vintage")
        assert "nostalgic" in p.lower()

    def test_style_with_sub_style(self):
        p = get_prompt_modifier("modern", "hyper_edit")
        assert "modern" in p.lower()
        assert "fast-paced" in p.lower()

    def test_unknown_sub_style_returns_style_only(self):
        p = get_prompt_modifier("vintage", "nonexistent")
        assert "nostalgic" in p.lower()


class TestGetEffectiveClipDuration:
    def test_no_sub_style(self):
        assert get_effective_clip_duration(3.0) == 3.0

    def test_sub_style_override(self):
        assert get_effective_clip_duration(3.0, "hyper_edit") == 1.5

    def test_slow_pacing_override(self):
        assert get_effective_clip_duration(3.0, "slow_pacing") == 6.0

    def test_unknown_sub_style_returns_base(self):
        assert get_effective_clip_duration(3.0, "nonexistent") == 3.0
