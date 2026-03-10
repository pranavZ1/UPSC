# pyq/explainer.py — On-demand answer explanations using Gemini
#
# Generates a concise explanation for why the correct answer is right.
# Only explains why other options are wrong when it adds educational value.
# Results are cached per question.

import json
from pathlib import Path

from config import PYQ_CACHE_DIR

EXPLAIN_CACHE_DIR = PYQ_CACHE_DIR / "explanations"


def get_explanation(question_id: str, question: str, options: dict, answer: str) -> dict:
    """Return cached or freshly-generated explanation for a PYQ question."""
    EXPLAIN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = EXPLAIN_CACHE_DIR / f"{question_id}.json"

    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    from llm.gemini_client import call_gemini

    options_text = "\n".join(f"  {k.upper()}) {v}" for k, v in options.items())
    correct_letter = answer.upper()

    prompt = f"""You are an expert UPSC Civil Services exam coach. Explain the answer to this UPSC Prelims question.

Question:
{question}

Options:
{options_text}

Correct Answer: {correct_letter}

Instructions:
- Explain clearly why option {correct_letter} is the correct answer.
- Support with relevant facts, dates, constitutional articles, treaties, or scientific concepts as applicable.
- Only explain why other options are incorrect if doing so adds significant educational value (e.g., common misconception, tricky distractor). Do NOT mechanically explain every wrong option.
- Keep it concise: 3-6 sentences total.
- Use plain text, no markdown headers, no bullet points, no JSON.
- Write in clear, exam-oriented language a UPSC aspirant would find useful."""

    explanation = call_gemini(prompt)

    result = {
        "question_id": question_id,
        "explanation": explanation.strip(),
    }

    cache_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result
