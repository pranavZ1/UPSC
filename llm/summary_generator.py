# llm/summary_generator.py — Generate revision summary from detailed content

from llm.gemini_client import call_gemini
from prompts.summary_prompt import SUMMARY_GENERATION_PROMPT


def generate_summary(content_text: str, subtopic: str = "", sub_subtopic: str = "") -> str:
    """
    Generate a fast-revision summary (sections A–E)
    from the detailed content that was already generated.
    """
    prompt = SUMMARY_GENERATION_PROMPT.format(
        content=content_text,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
