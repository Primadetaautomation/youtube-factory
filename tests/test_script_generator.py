"""Tests for script_generator.py with style integration."""

import json
from unittest.mock import patch, MagicMock

import pytest

from steps.pipeline_config import PipelineConfig


def _mock_openai_response(content_dict):
    """Create a mock OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = json.dumps(content_dict)
    response = MagicMock()
    response.choices = [choice]
    return response


class TestGenerateScriptStyleIntegration:
    """Test that generate_script injects style modifiers into the prompt."""

    @patch("steps.script_generator.OpenAI")
    def test_vintage_style_modifies_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        cfg = PipelineConfig(style="vintage")
        generate_script("test topic", 4, config=cfg)

        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "nostalgic" in prompt.lower() or "vintage" in prompt.lower()

    @patch("steps.script_generator.OpenAI")
    def test_80s_style_modifies_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        cfg = PipelineConfig(style="80s")
        generate_script("test topic", 4, config=cfg)

        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "1980s" in prompt or "retro" in prompt.lower() or "neon" in prompt.lower()

    @patch("steps.script_generator.OpenAI")
    def test_modern_style_still_works(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        cfg = PipelineConfig(style="modern")
        generate_script("test topic", 4, config=cfg)

        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "modern" in prompt.lower()

    @patch("steps.script_generator.OpenAI")
    def test_sub_style_modifies_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        cfg = PipelineConfig(style="modern", sub_style="hyper_edit")
        generate_script("test topic", 4, config=cfg)

        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "fast-paced" in prompt.lower() or "rapid" in prompt.lower()

    @patch("steps.script_generator.OpenAI")
    def test_no_config_backward_compatible(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        # No config passed - should still work with default prompt
        generate_script("test topic", 4)

        assert client.chat.completions.create.called

    @patch("steps.script_generator.OpenAI")
    def test_shorts_content_type_modifies_prompt(self, mock_cls):
        from steps.script_generator import generate_script

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_response(
            {"script": "test", "scenes": []}
        )

        cfg = PipelineConfig(content_type="shorts")
        generate_script("test topic", 1, config=cfg)

        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "short" in prompt.lower() or "hook" in prompt.lower()
