# pyq/explainer.py — On-demand answer explanations using Gemini (MongoDB)
#
# Generates a concise explanation for why the correct answer is right.
# Results are cached in the pyq_explanations collection in MongoDB.

from db import pyq_explanations_col


def get_explanation(question_id: str, question: str, options: dict, answer: str) -> dict:
    """Return cached or freshly-generated explanation for a PYQ question."""
    col = pyq_explanations_col()

    # Check cache
    cached = col.find_one({"question_id": question_id}, {"_id": 0})
    if cached:
        return cached

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

    col.update_one(
        {"question_id": question_id},
        {"$set": result},
        upsert=True,
    )
    return result
