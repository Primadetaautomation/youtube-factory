"""Generate YouTube title, description, and tags using OpenAI."""
import json
from openai import OpenAI
from config import OPENAI_API_KEY


def generate_metadata(topic: str, script_text: str) -> dict:
    """Generate optimized YouTube title, description, and tags."""
    client = OpenAI(api_key=OPENAI_API_KEY)

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
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    return json.loads(response.choices[0].message.content)


def generate_viral_titles(topic: str, script_text: str, count: int = 10) -> dict:
    """Generate multiple viral title options with virality scoring."""
    client = OpenAI(api_key=OPENAI_API_KEY)

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
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
    )

    return json.loads(response.choices[0].message.content)


def generate_viral_descriptions(topic: str, script_text: str, count: int = 5) -> dict:
    """Generate multiple SEO-optimized description options with scoring."""
    client = OpenAI(api_key=OPENAI_API_KEY)

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
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    return json.loads(response.choices[0].message.content)
