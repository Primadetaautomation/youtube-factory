"""Tests for viral tools - title finder, description finder."""

import json
from unittest.mock import patch, MagicMock

import pytest


def _mock_openai_json(content_dict):
    choice = MagicMock()
    choice.message.content = json.dumps(content_dict)
    response = MagicMock()
    response.choices = [choice]
    return response


class TestGenerateViralTitles:
    @patch("steps.metadata.OpenAI")
    def test_returns_list_of_scored_titles(self, mock_cls):
        from steps.metadata import generate_viral_titles

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_json({
            "titles": [
                {"title": "Test Title 1", "score": 9.2, "reasoning": "strong hook"},
                {"title": "Test Title 2", "score": 7.5, "reasoning": "decent"},
            ]
        })

        result = generate_viral_titles("test topic", "some script text")
        assert "titles" in result
        assert len(result["titles"]) >= 1
        assert "score" in result["titles"][0]
        assert "title" in result["titles"][0]

    @patch("steps.metadata.OpenAI")
    def test_prompt_includes_topic(self, mock_cls):
        from steps.metadata import generate_viral_titles

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_json({
            "titles": [{"title": "T", "score": 8, "reasoning": "r"}]
        })

        generate_viral_titles("Max Verstappen", "script about racing")
        prompt = client.chat.completions.create.call_args[1]["messages"][0]["content"]
        assert "Max Verstappen" in prompt


class TestGenerateViralDescriptions:
    @patch("steps.metadata.OpenAI")
    def test_returns_list_of_descriptions(self, mock_cls):
        from steps.metadata import generate_viral_descriptions

        client = MagicMock()
        mock_cls.return_value = client
        client.chat.completions.create.return_value = _mock_openai_json({
            "descriptions": [
                {"description": "Full desc here...", "score": 8.5, "focus": "SEO"},
            ]
        })

        result = generate_viral_descriptions("test topic", "script text")
        assert "descriptions" in result
        assert len(result["descriptions"]) >= 1


class TestPromptTemplates:
    def test_get_templates_returns_list(self):
        from steps.prompt_templates import get_prompt_templates

        templates = get_prompt_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_each_template_has_required_fields(self):
        from steps.prompt_templates import get_prompt_templates

        for t in get_prompt_templates():
            assert "name" in t
            assert "category" in t
            assert "template" in t
