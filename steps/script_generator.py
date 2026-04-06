"""Generate video script + visual suggestions using Gemini."""
import json
from google import genai
from config import GEMINI_API_KEY
from steps.pipeline_config import PipelineConfig
from steps.style_registry import get_prompt_modifier

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-3.1-pro"


def generate_script(topic: str, duration_minutes: int = 4, *, config=None) -> dict:
    """Generate a YouTube script with scene-by-scene visual suggestions."""
    if config is None:
        config = PipelineConfig()

    style_modifier = get_prompt_modifier(config.style, config.sub_style)
    style_instruction = f"\n- Visual and narrative style: {style_modifier}" if style_modifier else ""

    if config.content_type in ("shorts", "tiktok"):
        prompt = f"""Create a {duration_minutes}-minute short-form viral video script about: {topic}

Requirements:
- HOOK in the first 1-2 seconds — grab attention immediately
- Short, punchy, emotionally charged sentences
- Maximum impact in minimum time
- Big emotional moments visible on screen{style_instruction}

Return JSON with this exact structure:
{{
    "script": "full narration text",
    "scenes": [
        {{
            "timestamp": "0:00-0:02",
            "section": "HOOK",
            "narration": "the narration for this section",
            "visuals": [
                {{
                    "line": "specific narration line",
                    "search_query": "YouTube search query for matching footage",
                    "description": "what the clip should show"
                }}
            ]
        }}
    ]
}}

Make 3-6 scenes. Keep it tight and viral.
Each visual should be 1-3 seconds of footage.
Search queries should find real footage on YouTube.
Return ONLY valid JSON, no markdown.
"""
    else:
        prompt = f"""Create a {duration_minutes}-minute YouTube video script about: {topic}

Requirements:
- Dramatic, engaging narration style
- Short punchy sentences, lots of line breaks
- Builds tension and keeps viewer engaged{style_instruction}

Return JSON with this exact structure:
{{
    "script": "full narration text",
    "scenes": [
        {{
            "timestamp": "0:00-0:12",
            "section": "HOOK",
            "narration": "the narration for this section",
            "visuals": [
                {{
                    "line": "specific narration line",
                    "search_query": "YouTube search query for matching footage",
                    "description": "what the clip should show"
                }}
            ]
        }}
    ]
}}

Make 8-12 scenes covering the full {duration_minutes} minutes.
Each visual should be 2-3 seconds of footage.
Search queries should find real footage on YouTube (highlights, compilations, etc).
Return ONLY valid JSON, no markdown.
"""

    response = client.models.generate_content(model=MODEL, contents=[prompt])
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()

    return json.loads(text)


def refine_script(script_text: str, feedback: str) -> dict:
    """Refine an existing script based on user feedback."""
    prompt = (
        "You refine YouTube video scripts. Return the same JSON structure "
        "(with script and scenes keys).\n\n"
        f"Original script:\n{script_text}\n\n"
        f"Feedback:\n{feedback}\n\n"
        "Return updated JSON with script and scenes. Return ONLY valid JSON, no markdown."
    )

    response = client.models.generate_content(model=MODEL, contents=[prompt])
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()

    return json.loads(text)
