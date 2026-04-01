"""Shared pytest fixtures for youtube-factory tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path so `from steps.X import Y` works.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from steps.pipeline_config import PipelineConfig


@pytest.fixture
def default_config():
    """A PipelineConfig with all defaults."""
    return PipelineConfig()


@pytest.fixture
def shorts_config():
    """A PipelineConfig pre-configured for shorts."""
    cfg = PipelineConfig()
    cfg.apply_shorts_defaults()
    return cfg


@pytest.fixture
def vintage_config():
    """A PipelineConfig with vintage style."""
    return PipelineConfig(style="vintage", sub_style="slow_pacing")


@pytest.fixture
def mock_openai():
    """Mock OpenAI client that returns canned responses."""
    with patch("openai.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client

        # Default chat completion response
        choice = MagicMock()
        choice.message.content = '{"script": "test", "scenes": []}'
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response

        yield client


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for FFmpeg/yt-dlp calls."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        yield mock_run
