# books/book_cheatsheet.py — Generate whole-book cheat sheet (MongoDB)

import json
import re

from db import cheatsheets_col


# ── Cache ─────────────────────────────────────────────────────────────────────

def get_cached_cheatsheet(book_id: str) -> dict | None:
    """Return cached cheat sheet from MongoDB, or None."""
    doc = cheatsheets_col().find_one({"_id": book_id})
    if doc:
        return {"book_title": doc.get("book_title", ""), "chapters": doc.get("chapters", [])}
    return None


# ── Prompt ────────────────────────────────────────────────────────────────────

_CS_PROMPT = """You are an expert UPSC educator. Create a comprehensive, last-minute cheat sheet for the ENTIRE book.

OUTPUT FORMAT — respond with ONLY a JSON object:
{{
  "book_title": "<title>",
  "chapters": [
    {{
      "title": "<chapter title>",
      "points": [
        {{"text": "<key point in ≤ 30 words>", "reference": "<Article / Part / Section / Year, or '—' if none>"}},
        ...
      ]
    }},
    ...
  ]
}}

Rules:
- Cover EVERY chapter (even briefly).
- 3-6 key points per chapter — the most exam-relevant facts.
- Include article numbers, years, landmark cases, constitutional provisions.
- No markdown — pure JSON only.

Book: {book_title}
Chapters & Topics:
{chapters}
"""


def _parse_cheatsheet(text: str) -> dict | None:
    """Parse LLM response into cheat sheet dict."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "chapters" in data:
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, dict) and "chapters" in data:
                return data
        except json.JSONDecodeError:
            pass
    return None


def generate_cheatsheet(book_id: str, structure: dict) -> dict:
    """Generate and cache a whole-book cheat sheet."""
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    book_title = structure.get("book_summary", "Unknown Book")
    chapters = structure.get("chapters", [])
    ch_text = "\n".join(
        f"- {ch['chapter_title']}: " + ", ".join(t["topic_title"] for t in ch.get("topics", []))
        for ch in chapters
    )

    prompt = _CS_PROMPT.format(book_title=book_title, chapters=ch_text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.5),
    )
    result = _parse_cheatsheet(response.text)

    if not result:
        result = {
            "book_title": book_title,
            "chapters": [{"title": "Error", "points": [{"text": "Could not generate cheat sheet. Try again.", "reference": "—"}]}],
        }

    # Store in MongoDB
    cheatsheets_col().replace_one(
        {"_id": book_id},
        {
            "_id": book_id,
            "book_id": book_id,
            "book_title": result.get("book_title", book_title),
            "chapters": result.get("chapters", []),
        },
        upsert=True,
    )

    print(f"✅ Cheat sheet saved for {book_id}")
    return result
