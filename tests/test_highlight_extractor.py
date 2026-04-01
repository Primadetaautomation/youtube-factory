"""Tests for highlight extractor."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestExtractHighlights:
    @patch("steps.highlight_extractor.OpenAI")
    @patch("steps.highlight_extractor.subprocess.run")
    def test_returns_highlight_list(self, mock_run, mock_cls, tmp_path):
        from steps.highlight_extractor import extract_highlights

        video = tmp_path / "long_video.mp4"
        video.touch()

        # Mock FFmpeg scene detection output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="scene_score=0.85,pts_time=12.5\nscene_score=0.72,pts_time=45.2\nscene_score=0.91,pts_time=78.0\n",
        )

        # Mock GPT analysis
        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = json.dumps({
            "highlights": [
                {"start": 10.0, "end": 15.0, "description": "Key moment 1"},
                {"start": 43.0, "end": 48.0, "description": "Key moment 2"},
            ]
        })
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        result = extract_highlights(video, target_count=3)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "start" in result[0]
        assert "description" in result[0]


class TestRenderHookPreview:
    @patch("steps.video_editor.subprocess.run")
    def test_extracts_first_n_seconds(self, mock_run, tmp_path):
        from steps.video_editor import render_hook_preview
        from steps.pipeline_config import PipelineConfig

        video = tmp_path / "video.mp4"
        video.touch()

        output = Path("/Users/jamese/youtube-factory/output/hook_preview.mp4")
        mock_run.side_effect = lambda *a, **kw: output.touch() or MagicMock()

        result = render_hook_preview(video, 3.0)
        assert mock_run.called
        args = mock_run.call_args[0][0]
        # Should use -t for duration limit
        assert "-t" in args
        t_idx = args.index("-t")
        assert args[t_idx + 1] == "3.0"
