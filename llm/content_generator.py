# llm/content_generator.py — Generate detailed UPSC content from input text

from llm.gemini_client import call_gemini
from prompts.content_prompt import CONTENT_GENERATION_PROMPT


def generate_content(text: str, subtopic: str = "", sub_subtopic: str = "") -> str:
    """
    Generate structured UPSC Prelims content (sections A–G)
    from the given input text.

    The subtopic and sub_subtopic are passed to give the LLM
    syllabus context so it can emphasize the right angles.
    [SUBTOPIC] and [FOCUS] markers are prepended for downstream
    file organization and PDF rendering.
    """
    prompt = CONTENT_GENERATION_PROMPT.format(
        content=text,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    # Prepend organization markers (used by file_manager + pdf_creator)
    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
