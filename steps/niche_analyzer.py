"""Analyze topic niche potential using YouTube search data + AI analysis."""

import json
from openai import OpenAI
from config import OPENAI_API_KEY
from steps.clip_finder import search_youtube


def analyze_niche(topic: str, search_count: int = 10) -> dict:
    """Analyze a topic's niche potential on YouTube.

    Uses YouTube search (via yt-dlp) to gauge volume and competition,
    then GPT-4o to interpret the data and provide recommendations.
    """
    # Gather search data
    results = search_youtube(topic, max_results=search_count)

    titles = [r.get("title", "") for r in results]
    channels = [r.get("channel", "") for r in results]

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""Analyze this YouTube niche/topic for a content creator: "{topic}"

Here are the top {len(results)} search results:
Titles: {json.dumps(titles, ensure_ascii=False)}
Channels: {json.dumps(channels, ensure_ascii=False)}

Based on these results, analyze:
1. Volume estimate (how much content exists): "low", "medium", "high"
2. Competition level (how established are the channels): "low", "medium", "high"
3. Is this topic currently trending?
4. Overall niche score (1-10, where 10 = great opportunity)
5. 3-5 specific recommendations for a new creator in this niche
6. Top channels dominating this niche

Return JSON:
{{
    "volume_estimate": "low|medium|high",
    "competition": "low|medium|high",
    "trending": true|false,
    "score": 8.5,
    "recommendations": ["recommendation 1", "recommendation 2"],
    "top_channels": ["channel1", "channel2"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    analysis = json.loads(response.choices[0].message.content)
    analysis["topic"] = topic
    analysis["search_results_count"] = len(results)

    return analysis
