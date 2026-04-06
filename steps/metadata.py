"""Generate YouTube title, description, and tags using Gemini."""
import json
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-3.1-pro"


def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()
    return json.loads(text)


def generate_metadata(topic: str, script_text: str) -> dict:
    """Generate optimized YouTube title, description, and tags."""
    prompt = f"""Generate YouTube metadata for a video about: {topic}

Script summary: {script_text[:500]}

Return JSON:
{{
    "title": "catchy title, max 60 chars, use caps strategically",
    "description": "full description with timestamps, hashtags, subscribe CTA, 2000+ chars",
    "tags": ["tag1", "tag2", "...up to 15 relevant tags"]
}}

Make the title clickable but not clickbait. Use proven YouTube title formulas.
Description should include relevant keywords for SEO.
Return ONLY valid JSON, no markdown.
"""

    response = client.models.generate_content(model=MODEL, contents=[prompt])
    return _parse_json(response.text)


def generate_viral_titles(topic: str, script_text: str, count: int = 10) -> dict:
    """Generate multiple viral title options with virality scoring."""
    prompt = f"""Generate {count} viral YouTube title options for a video about: {topic}

Script summary: {script_text[:500]}

For each title, provide:
- The title itself (max 60 chars, strategic caps)
- A virality score (1-10)
- Brief reasoning why it would perform well

Use proven viral formulas: curiosity gaps, numbers, emotional triggers, power words.

Return JSON:
{{
    "titles": [
        {{"title": "...", "score": 9.2, "reasoning": "..."}}
    ]
}}
Return ONLY valid JSON, no markdown.
"""

    response = client.models.generate_content(model=MODEL, contents=[prompt])
    return _parse_json(response.text)


def generate_viral_descriptions(topic: str, script_text: str, count: int = 5) -> dict:
    """Generate multiple SEO-optimized description options with scoring."""
    prompt = f"""Generate {count} YouTube description variants for a video about: {topic}

Script summary: {script_text[:500]}

For each description, provide:
- Full description (2000+ chars with timestamps, hashtags, subscribe CTA)
- SEO score (1-10)
- Focus area (e.g. "SEO heavy", "engagement focused", "storytelling")

Return JSON:
{{
    "descriptions": [
        {{"description": "...", "score": 8.5, "focus": "..."}}
    ]
}}
Return ONLY valid JSON, no markdown.
"""

    response = client.models.generate_content(model=MODEL, contents=[prompt])
    return _parse_json(response.text)
