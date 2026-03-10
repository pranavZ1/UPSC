# llm/qa_generator.py — Generate UPSC Prelims-style MCQs

from llm.gemini_client import call_gemini
from prompts.qa_prompt import QA_GENERATION_PROMPT


def generate_mcqs(content_text: str, subtopic: str = "", sub_subtopic: str = "") -> str:
    """
    Generate 8–10 UPSC Prelims-style MCQs with answer key
    from the detailed content.
    """
    prompt = QA_GENERATION_PROMPT.format(
        content=content_text,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
