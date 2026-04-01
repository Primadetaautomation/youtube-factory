"""Generate video script + visual suggestions using OpenAI."""
import json
from openai import OpenAI
from config import OPENAI_API_KEY
from steps.pipeline_config import PipelineConfig
from steps.style_registry import get_prompt_modifier


def generate_script(topic: str, duration_minutes: int = 4, *, config=None) -> dict:
    """Generate a YouTube script with scene-by-scene visual suggestions."""
    if config is None:
        config = PipelineConfig()

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build style instruction from config
    style_modifier = get_prompt_modifier(config.style, config.sub_style)
    style_instruction = f"\n- Visual and narrative style: {style_modifier}" if style_modifier else ""

    # Shorts/short-form content gets a different prompt structure
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
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    return json.loads(response.choices[0].message.content)


def refine_script(script_text: str, feedback: str) -> dict:
    """Refine an existing script based on user feedback."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You refine YouTube video scripts. Return the same JSON structure."},
            {"role": "user", "content": f"Original script:\n{script_text}\n\nFeedback:\n{feedback}\n\nReturn updated JSON with script and scenes."},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    return json.loads(response.choices[0].message.content)
