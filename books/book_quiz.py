# books/book_quiz.py — Quiz question dump + random sampling (MongoDB)

import json
import re
import random

from db import quiz_dumps_col


# ── Cache / retrieval ─────────────────────────────────────────────────────────

def get_cached_quiz(book_id: str, chapter_idx: int, difficulty: str) -> list | None:
    """
    Return 10 random questions from the pre-generated dump for this chapter + difficulty.
    If no dump exists, return None (caller should trigger generation).
    """
    doc = quiz_dumps_col().find_one({"_id": f"{book_id}_ch{chapter_idx}_{difficulty}"})
    if not doc:
        return None
    pool = doc.get("questions", [])
    if not pool:
        return None
    # Randomly pick 10 (or fewer if pool is small)
    sample_size = min(10, len(pool))
    return random.sample(pool, sample_size)


def get_full_dump(book_id: str, chapter_idx: int, difficulty: str) -> list | None:
    """Return the full question dump (admin / pipeline use)."""
    doc = quiz_dumps_col().find_one({"_id": f"{book_id}_ch{chapter_idx}_{difficulty}"})
    return doc["questions"] if doc else None


# ── Prompt ────────────────────────────────────────────────────────────────────

_QUIZ_PROMPT = """You are an expert UPSC question-paper setter.

Generate exactly {count} multiple-choice questions for the chapter below at "{difficulty}" difficulty level.

DIFFICULTY GUIDE:
- easy: Basic recall — definitions, straightforward facts
- medium: Application & analysis — compare/contrast, cause-effect
- hard: UPSC Prelims style — tricky options, require deep understanding

OUTPUT FORMAT — respond with ONLY a JSON array:
[
  {{
    "question": "The question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Why this answer is correct (1-2 sentences)"
  }},
  ...
]

Rules:
- Exactly 4 options per question.
- "correct" is the 0-based index of the right option.
- Every fact must be accurate.
- Questions should be diverse — cover different topics within the chapter.
- No markdown — pure JSON only.

Chapter: {chapter_title}
Topics covered: {topics}
"""


def _parse_questions(text: str) -> list:
    """Parse LLM response into a list of question dicts."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        qs = json.loads(text)
        if isinstance(qs, list):
            return _validate_questions(qs)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            qs = json.loads(m.group())
            return _validate_questions(qs)
        except json.JSONDecodeError:
            pass
    return []


def _validate_questions(qs: list) -> list:
    """Ensure each question has the required fields."""
    valid = []
    for q in qs:
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ("question", "options", "correct")):
            continue
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            continue
        if not isinstance(q["correct"], int) or q["correct"] < 0 or q["correct"] > 3:
            continue
        valid.append({
            "question": str(q["question"]),
            "options": [str(o) for o in q["options"]],
            "correct": q["correct"],
            "explanation": str(q.get("explanation", "")),
        })
    return valid


# ── Generation ────────────────────────────────────────────────────────────────

DUMP_SIZE = 30  # questions per chapter per difficulty


def generate_quiz(
    book_id: str, chapter_idx: int,
    chapter_title: str, topics: list[dict],
    difficulty: str = "medium",
) -> list:
    """
    Generate a question dump for this chapter + difficulty, store in MongoDB,
    then return 10 random questions from the dump.
    """
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    topic_text = ", ".join(t["topic_title"] for t in topics) if topics else chapter_title

    # Enrich with RAG context
    context = ""
    try:
        from books.book_chat import _retrieve_chunks
        chunks = _retrieve_chunks(book_id, chapter_title, top_k=4)
        context = "\n".join(chunks[:3]) if chunks else ""
    except Exception:
        pass

    prompt = _QUIZ_PROMPT.format(
        count=DUMP_SIZE,
        difficulty=difficulty,
        chapter_title=chapter_title,
        topics=topic_text,
    )
    if context:
        prompt += f"\n\nContext from the book:\n{context[:8000]}"

    print(f"📝 Generating {DUMP_SIZE} {difficulty} questions for: {chapter_title}")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    questions = _parse_questions(response.text)

    if not questions:
        questions = [{
            "question": f"Error generating questions for {chapter_title}",
            "options": ["Try again", "N/A", "N/A", "N/A"],
            "correct": 0,
            "explanation": "Generation failed",
        }]

    # Store the full dump in MongoDB
    doc_id = f"{book_id}_ch{chapter_idx}_{difficulty}"
    quiz_dumps_col().replace_one(
        {"_id": doc_id},
        {
            "_id": doc_id,
            "book_id": book_id,
            "chapter_idx": chapter_idx,
            "difficulty": difficulty,
            "questions": questions,
            "count": len(questions),
        },
        upsert=True,
    )

    print(f"✅ {len(questions)} {difficulty} questions dumped for ch{chapter_idx}")

    # Return 10 random from the dump
    sample_size = min(10, len(questions))
    return random.sample(questions, sample_size)


def generate_quiz_dump_all_difficulties(
    book_id: str, chapter_idx: int,
    chapter_title: str, topics: list[dict],
) -> dict:
    """Generate question dumps for all three difficulties (used by pipeline)."""
    results = {}
    for diff in ("easy", "medium", "hard"):
        qs = generate_quiz(book_id, chapter_idx, chapter_title, topics, difficulty=diff)
        results[diff] = len(qs)
    return results
