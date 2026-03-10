# llm/mains_summary_generator.py — Generate Mains revision summary

from llm.gemini_client import call_gemini
from prompts.mains_summary_prompt import MAINS_SUMMARY_PROMPT
from config import MAINS_PAPER_MAP


def generate_mains_summary(
    content_text: str,
    file_stem: str = "",
    subtopic: str = "",
    sub_subtopic: str = "",
) -> str:
    """
    Generate a Mains-oriented revision summary from detailed content.
    """
    paper = MAINS_PAPER_MAP.get(file_stem, "GS3")

    prompt = MAINS_SUMMARY_PROMPT.format(
        content=content_text,
        paper=paper,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
