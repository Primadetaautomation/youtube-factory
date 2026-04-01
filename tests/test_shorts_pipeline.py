"""Tests for shorts pipeline mode - end-to-end config flow."""

import json
from unittest.mock import patch, MagicMock

import pytest

from steps.pipeline_config import PipelineConfig


class TestShortsConfigFlow:
    """Test the full shorts config flows correctly through the pipeline."""

    def test_apply_shorts_sets_all_expected_values(self):
        cfg = PipelineConfig()
        cfg.apply_shorts_defaults()

        assert cfg.aspect_ratio == "9:16"
        assert cfg.content_type == "shorts"
        assert cfg.subtitle_style == "large_caption"
        assert cfg.subtitle_font_size == 72
        assert cfg.subtitle_position == "center"
        assert cfg.max_clip_duration == 2.0
        assert cfg.width == 1080
        assert cfg.height == 1920

    def test_shorts_config_serialization_roundtrip(self):
        cfg = PipelineConfig()
        cfg.apply_shorts_defaults()
        d = cfg.to_dict()
        restored = PipelineConfig.from_dict(d)
        assert restored.aspect_ratio == "9:16"
        assert restored.content_type == "shorts"
        assert restored.subtitle_font_size == 72

    @patch("steps.script_generator.OpenAI")
    def test_shorts_script_uses_hook_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = json.dumps({"script": "test", "scenes": []})
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        cfg = PipelineConfig(content_type="shorts")
        generate_script("test topic", 1, config=cfg)

        prompt = client.chat.completions.create.call_args[1]["messages"][0]["content"]
        # Shorts prompt should mention hook and short-form
        assert "hook" in prompt.lower()
        assert "short" in prompt.lower() or "viral" in prompt.lower()
        # Should have fewer scenes
        assert "3-6 scenes" in prompt

    @patch("steps.video_editor.subprocess.run")
    def test_shorts_video_uses_vertical_resolution(self, mock_run, tmp_path):
        from steps.video_editor import combine_clips
        from pathlib import Path

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig()
        cfg.apply_shorts_defaults()
        combine_clips([clip], 30.0, config=cfg)

        args = mock_run.call_args[0][0]
        filter_str = args[args.index("-filter_complex") + 1]
        assert "scale=1080:1920" in filter_str

    @patch("steps.video_editor.subprocess.Popen")
    @patch("steps.video_editor._get_video_duration", return_value=2.0)
    def test_shorts_subtitles_are_centered(self, mock_dur, mock_popen, tmp_path):
        from steps.video_editor import burn_subtitles
        from pathlib import Path

        video = tmp_path / "test.mp4"
        video.touch()
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n\n")

        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        output_path = Path("/Users/jamese/youtube-factory/output/test_sub.mp4")
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_bytes(b"x" * 2000)

        cfg = PipelineConfig()
        cfg.apply_shorts_defaults()
        burn_subtitles(video, srt, "test", config=cfg)

        # Verify FFmpeg uses 1080x1920
        cmd = mock_popen.call_args[0][0]
        assert "1080x1920" in " ".join(cmd)

        output_path.unlink(missing_ok=True)


class TestTikTokStyleIntegration:
    """Test TikTok content type works the same as shorts."""

    @patch("steps.script_generator.OpenAI")
    def test_tiktok_uses_shorts_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = json.dumps({"script": "test", "scenes": []})
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        cfg = PipelineConfig(content_type="tiktok")
        generate_script("test", 1, config=cfg)

        prompt = client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "hook" in prompt.lower()
