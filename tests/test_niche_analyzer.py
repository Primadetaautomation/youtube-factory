"""Tests for niche analyzer and copyright checker."""

import json
from unittest.mock import patch, MagicMock

import pytest


class TestAnalyzeNiche:
    @patch("steps.niche_analyzer.OpenAI")
    @patch("steps.niche_analyzer.search_youtube")
    def test_returns_niche_analysis(self, mock_search, mock_cls):
        from steps.niche_analyzer import analyze_niche

        mock_search.return_value = [
            {"video_id": "abc", "title": "Top 10 F1 Moments", "channel": "F1"},
            {"video_id": "def", "title": "Verstappen Wins", "channel": "ESPN"},
        ]

        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = json.dumps({
            "volume_estimate": "high",
            "competition": "medium",
            "trending": True,
            "score": 8.5,
            "recommendations": ["Focus on recent events", "Use dramatic style"],
            "top_channels": ["F1", "ESPN"],
        })
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        result = analyze_niche("F1 racing")
        assert result["topic"] == "F1 racing"
        assert "score" in result
        assert "recommendations" in result

    @patch("steps.niche_analyzer.OpenAI")
    @patch("steps.niche_analyzer.search_youtube")
    def test_handles_no_search_results(self, mock_search, mock_cls):
        from steps.niche_analyzer import analyze_niche

        mock_search.return_value = []

        client = MagicMock()
        mock_cls.return_value = client
        choice = MagicMock()
        choice.message.content = json.dumps({
            "volume_estimate": "low",
            "competition": "low",
            "trending": False,
            "score": 3.0,
            "recommendations": ["Very niche topic"],
            "top_channels": [],
        })
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        result = analyze_niche("obscure topic xyz")
        assert result["topic"] == "obscure topic xyz"


class TestCheckClipCopyright:
    @patch("steps.copyright_checker.subprocess.run")
    def test_returns_risk_assessment(self, mock_run):
        from steps.copyright_checker import check_clip_copyright

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "license": "Creative Commons",
                "channel": "FreeStockFootage",
                "description": "Free to use footage",
            }),
        )

        result = check_clip_copyright("https://youtube.com/watch?v=abc")
        assert "risk_level" in result
        assert result["risk_level"] in ("low", "medium", "high")

    @patch("steps.copyright_checker.subprocess.run")
    def test_copyrighted_content_flagged(self, mock_run):
        from steps.copyright_checker import check_clip_copyright

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "license": "Standard YouTube License",
                "channel": "ESPN",
                "description": "Copyright ESPN. All rights reserved. No reuse.",
            }),
        )

        result = check_clip_copyright("https://youtube.com/watch?v=def")
        assert result["risk_level"] in ("medium", "high")
        assert len(result["warnings"]) > 0

    @patch("steps.copyright_checker.subprocess.run")
    def test_handles_yt_dlp_failure(self, mock_run):
        from steps.copyright_checker import check_clip_copyright

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = check_clip_copyright("https://youtube.com/watch?v=bad")
        assert result["risk_level"] == "medium"
        assert "warnings" in result
