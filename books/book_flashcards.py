# books/book_flashcards.py — Generate flash cards (MongoDB)

import json
import re

from db import flashcards_col


# ── Cache helpers ─────────────────────────────────────────────────────────────

def get_cached_cards(book_id: str, chapter_idx: int, topic_idx: int) -> list | None:
    """Return cached flash cards from MongoDB, or None."""
    doc = flashcards_col().find_one(
        {"_id": f"{book_id}_ch{chapter_idx}_t{topic_idx}"}
    )
    return doc["cards"] if doc else None


def get_cached_super_cards(book_id: str) -> list | None:
    """Return cached super last-min cards from MongoDB, or None."""
    doc = flashcards_col().find_one({"_id": f"{book_id}_super"})
    return doc["cards"] if doc else None


# ── Generation ────────────────────────────────────────────────────────────────

_CARD_PROMPT = """You are an expert UPSC educator. Create a set of 8-12 flash cards for the topic below.

OUTPUT FORMAT — respond with ONLY a JSON array:
[
  {{"point": "Front side — the key term, article, or concept (short, ≤15 words)", "detail": "Back side — explanation, remembering aid, or mnemonic (≤40 words)"}},
  ...
]

Rules:
- Cards must be factually accurate.
- Cover key articles, dates, personalities, definitions, distinctions.
- No markdown — pure JSON only.
- "point" = front of card.  "detail" = back of card.

Topic: {topic}
Chapter: {chapter}
"""

_SUPER_PROMPT = """You are an expert UPSC educator. Create a "Super Last-Minute Revision" deck of 25-30 flash cards for the entire book below.

OUTPUT FORMAT — respond with ONLY a JSON array:
[
  {{"point": "Front (≤15 words)", "detail": "Back (≤40 words)"}},
  ...
]

Rules:
- Cover the MOST IMPORTANT points from every chapter.
- Focus on what's most likely to appear in the exam.
- Include key articles, dates, landmark cases, definitions.
- No markdown — pure JSON only.

Book title: {book_title}
Chapters:
{chapters}
"""


def _parse_cards(text: str) -> list:
    """Parse the LLM response into a list of card dicts."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        cards = json.loads(text)
        if isinstance(cards, list):
            return [
                {"point": c.get("point", c.get("front", "")),
                 "detail": c.get("detail", c.get("back", ""))}
                for c in cards if isinstance(c, dict)
            ]
    except json.JSONDecodeError:
        pass
    # fallback: try to capture JSON arrays anywhere in the text
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            cards = json.loads(m.group())
            return [
                {"point": c.get("point", c.get("front", "")),
                 "detail": c.get("detail", c.get("back", ""))}
                for c in cards if isinstance(c, dict)
            ]
        except json.JSONDecodeError:
            pass
    return []


def generate_flashcards(
    book_id: str, chapter_idx: int, topic_idx: int,
    topic_title: str, chapter_title: str,
) -> list:
    """Generate flash cards for a topic and cache in MongoDB."""
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Try to enrich with RAG context
    context = ""
    try:
        from books.book_chat import _retrieve_chunks
        chunks = _retrieve_chunks(book_id, f"{chapter_title} {topic_title}", top_k=3)
        context = "\n".join(chunks[:2]) if chunks else ""
    except Exception:
        pass

    prompt = _CARD_PROMPT.format(topic=topic_title, chapter=chapter_title)
    if context:
        prompt += f"\n\nContext from the book:\n{context[:6000]}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.6),
    )
    cards = _parse_cards(response.text)

    if not cards:
        cards = [{"point": topic_title, "detail": "Cards could not be generated. Try again."}]

    # Store in MongoDB
    flashcards_col().replace_one(
        {"_id": f"{book_id}_ch{chapter_idx}_t{topic_idx}"},
        {
            "_id": f"{book_id}_ch{chapter_idx}_t{topic_idx}",
            "book_id": book_id,
            "chapter_idx": chapter_idx,
            "topic_idx": topic_idx,
            "cards": cards,
        },
        upsert=True,
    )

    print(f"✅ {len(cards)} flash cards saved for ch{chapter_idx}/t{topic_idx}")
    return cards


def generate_super_cards(book_id: str, structure: dict) -> list:
    """Generate super last-min revision deck for entire book, cached in MongoDB."""
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

    prompt = _SUPER_PROMPT.format(book_title=book_title, chapters=ch_text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.6),
    )
    cards = _parse_cards(response.text)

    if not cards:
        cards = [{"point": "Error", "detail": "Super cards could not be generated."}]

    flashcards_col().replace_one(
        {"_id": f"{book_id}_super"},
        {
            "_id": f"{book_id}_super",
            "book_id": book_id,
            "cards": cards,
        },
        upsert=True,
    )

    print(f"✅ {len(cards)} super flash cards saved for {book_id}")
    return cards
