# llm/mains_qa_generator.py — Generate UPSC Mains-style Q&A

from llm.gemini_client import call_gemini
from prompts.mains_qa_prompt import MAINS_QA_PROMPT
from config import MAINS_PAPER_MAP


def generate_mains_qa(
    content_text: str,
    file_stem: str = "",
    subtopic: str = "",
    sub_subtopic: str = "",
) -> str:
    """
    Generate 4-5 UPSC Mains-style questions with immediate structured answers.
    """
    paper = MAINS_PAPER_MAP.get(file_stem, "GS3")

    prompt = MAINS_QA_PROMPT.format(
        content=content_text,
        paper=paper,
        subtopic=subtopic or "General",
        sub_subtopic=sub_subtopic or "General",
    )
    body = call_gemini(prompt)

    header = f"[SUBTOPIC] {subtopic}\n[FOCUS] {sub_subtopic}\n\n"
    return header + body
