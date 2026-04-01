"""Tests for video_editor.py with PipelineConfig support."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from steps.pipeline_config import PipelineConfig


class TestCombineClipsConfig:
    """Test that combine_clips uses PipelineConfig for dimensions, quality, and filters."""

    def _get_ffmpeg_args(self, mock_run):
        """Extract the FFmpeg command args from mock_run call."""
        assert mock_run.called
        return mock_run.call_args[0][0]

    @patch("steps.video_editor.subprocess.run")
    def test_default_config_uses_1920x1080(self, mock_run, tmp_path):
        """With default config, should use 1920x1080."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        # Make combined output exist so no RuntimeError
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        combine_clips([clip], 10.0, config=PipelineConfig())
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "scale=1920:1080" in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_vertical_config_uses_1080x1920(self, mock_run, tmp_path):
        """With 9:16 aspect ratio, should use 1080x1920."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(aspect_ratio="9:16")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "scale=1080:1920" in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_square_config_uses_1080x1080(self, mock_run, tmp_path):
        """With 1:1 aspect ratio, should use 1080x1080."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(aspect_ratio="1:1")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "scale=1080:1080" in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_720p_resolution(self, mock_run, tmp_path):
        """720p should use 1280x720."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(resolution="720p")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "scale=1280:720" in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_custom_crf(self, mock_run, tmp_path):
        """Custom CRF should be used in FFmpeg args."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(quality_crf=18)
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "18"

    @patch("steps.video_editor.subprocess.run")
    def test_custom_preset(self, mock_run, tmp_path):
        """Custom preset should be used in FFmpeg args."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(quality_preset="medium")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        preset_idx = args.index("-preset")
        assert args[preset_idx + 1] == "medium"

    @patch("steps.video_editor.subprocess.run")
    def test_style_filters_applied(self, mock_run, tmp_path):
        """Vintage style should add color grading FFmpeg filters."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(style="vintage")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "curves=vintage" in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_modern_style_no_extra_filters(self, mock_run, tmp_path):
        """Modern style should not add color grading filters."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        cfg = PipelineConfig(style="modern")
        combine_clips([clip], 10.0, config=cfg)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        assert "curves=" not in filter_str

    @patch("steps.video_editor.subprocess.run")
    def test_no_config_backward_compatible(self, mock_run, tmp_path):
        """Calling without config should still work (backward compat)."""
        from steps.video_editor import combine_clips

        clip = tmp_path / "clip_0.mp4"
        clip.touch()
        combined_path = Path("/Users/jamese/youtube-factory/temp/combined_clips.mp4")
        mock_run.side_effect = lambda *a, **kw: combined_path.touch() or MagicMock()

        combine_clips([clip], 10.0)
        args = self._get_ffmpeg_args(mock_run)
        filter_str = args[args.index("-filter_complex") + 1]
        # Default should be 1920x1080
        assert "scale=1920:1080" in filter_str


class TestBurnSubtitlesConfig:
    """Test that burn_subtitles uses PipelineConfig for dimensions and subtitle styling."""

    @patch("steps.video_editor.subprocess.Popen")
    @patch("steps.video_editor._get_video_duration", return_value=2.0)
    def test_vertical_dimensions_in_overlay(self, mock_dur, mock_popen, tmp_path):
        """With 9:16 config, subtitle overlay should be 1080x1920."""
        from steps.video_editor import burn_subtitles

        video = tmp_path / "test.mp4"
        video.touch()
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello world\n\n")

        # Mock the Popen process
        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.wait.return_value = 0
        mock_popen.return_value = proc

        output_path = Path("/Users/jamese/youtube-factory/output/test_sub.mp4")
        output_path.parent.mkdir(exist_ok=True)
        output_path.touch()
        # Make file > 1000 bytes
        output_path.write_bytes(b"x" * 2000)

        cfg = PipelineConfig(aspect_ratio="9:16")
        burn_subtitles(video, srt, "test", config=cfg)

        # Check FFmpeg command uses 1080x1920
        cmd = mock_popen.call_args[0][0]
        assert "1080x1920" in " ".join(cmd)

        # Cleanup
        output_path.unlink(missing_ok=True)
