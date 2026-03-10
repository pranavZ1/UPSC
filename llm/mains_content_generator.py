# llm/mains_content_generator.py — Generate detailed UPSC Mains content

from llm.gemini_client import call_gemini
from prompts.mains_content_prompt import MAINS_CONTENT_PROMPT
from config import MAINS_PAPER_MAP


def generate_mains_content(
    text: str,
    file_stem: str = "",
    subtopic: str = "",
    sub_subtopic: str = "",
) -> str:
    """
    Generate structured UPSC Mains content (sections A–G)
    with multi-dimensional analysis and way forward.
    """
    paper = MAINS_PAPER_MAP.get(file_stem, "GS3")

    prompt = MAINS_CONTENT_PROMPT.format(
        content=text,
        paper=paper,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
