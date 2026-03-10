# news/analyzer.py — AI-powered news analysis using Gemini
#
# Two modes:
# 1. Analyze — Summarize the article concisely
# 2. Deep Dive — Explain causes, effects, background context

import json
from pathlib import Path
from config import BASE_DIR
from news.fetcher import fetch_article_content

ANALYSIS_CACHE_DIR = BASE_DIR / "news_cache" / "analysis"
ANALYSIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _analysis_cache_path(article_id: str, mode: str) -> Path:
    return ANALYSIS_CACHE_DIR / f"{article_id}_{mode}.json"


def _get_cached(article_id: str, mode: str) -> dict | None:
    path = _analysis_cache_path(article_id, mode)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _cache_result(article_id: str, mode: str, result: dict):
    path = _analysis_cache_path(article_id, mode)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_article(article_id: str, title: str, url: str, summary: str = "") -> dict:
    """
    Analyze / summarize a news article.
    Returns: {"summary": "...", "key_points": ["..."], "upsc_relevance": "..."}
    """
    cached = _get_cached(article_id, "analyze")
    if cached:
        return cached

    from llm.gemini_client import call_gemini

    # Fetch full article content
    content = fetch_article_content(url)

    prompt = f"""You are an expert UPSC coach and news analyst. Analyze this news article and provide a concise summary suitable for UPSC aspirants.

ARTICLE TITLE: {title}

ARTICLE CONTENT:
{content if len(content) > 100 else f"(Limited content available) Summary: {summary}"}

Provide your analysis in this EXACT JSON format:
{{
    "summary": "A clear, concise summary of the article in 3-5 sentences. Focus on facts, figures, and key developments.",
    "key_points": [
        "Key point 1 — most important takeaway",
        "Key point 2 — relevant fact or figure",
        "Key point 3 — context or significance",
        "Key point 4 — if applicable"
    ],
    "upsc_relevance": "Brief note on why this is relevant for UPSC preparation — which paper/topic/syllabus area it connects to."
}}

Return ONLY valid JSON. No markdown, no extra text."""

    response = call_gemini(prompt)
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {
            "summary": response[:500],
            "key_points": ["Could not parse structured response"],
            "upsc_relevance": "N/A",
        }

    _cache_result(article_id, "analyze", result)
    return result


def deep_dive_article(article_id: str, title: str, url: str, summary: str = "") -> dict:
    """
    Deep dive analysis — causes, effects, background, implications.
    Returns: {"background": "...", "causes": ["..."], "effects": ["..."],
              "implications": "...", "connected_topics": ["..."]}
    """
    cached = _get_cached(article_id, "deepdive")
    if cached:
        return cached

    from llm.gemini_client import call_gemini

    content = fetch_article_content(url)

    prompt = f"""You are an expert UPSC analyst. Perform a DEEP DIVE analysis of this news article. Explain the full context — why it happened, what caused it, what are the effects, and what it means for India and the world.

ARTICLE TITLE: {title}

ARTICLE CONTENT:
{content if len(content) > 100 else f"(Limited content available) Summary: {summary}"}

Provide your deep dive in this EXACT JSON format:
{{
    "background": "Historical and contextual background of this event/development. What led to this? (3-5 sentences)",
    "causes": [
        "Primary cause or trigger of this development",
        "Secondary cause or contributing factor",
        "Any underlying structural cause"
    ],
    "effects": [
        "Immediate impact or consequence",
        "Impact on India specifically",
        "Broader global or long-term impact"
    ],
    "implications": "What does this mean going forward? Future outlook and what to watch for. (2-4 sentences)",
    "connected_topics": [
        "Related UPSC syllabus topic 1",
        "Related UPSC syllabus topic 2",
        "Related current affair connection"
    ]
}}

Return ONLY valid JSON. Be detailed and analytical. No markdown."""

    response = call_gemini(prompt)
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {
            "background": response[:500],
            "causes": ["Could not parse structured response"],
            "effects": ["N/A"],
            "implications": "N/A",
            "connected_topics": [],
        }

    _cache_result(article_id, "deepdive", result)
    return result
