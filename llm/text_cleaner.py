# llm/text_cleaner.py — Clean and compress raw text before processing

from llm.gemini_client import call_gemini


COMPRESS_PROMPT = """Act as an expert Information Architect.

Task: Perform a ZERO-LOSS HIGH-DENSITY extraction from the text below.

Rules (STRICT):
- REMOVE page numbers, headers/footers, disclaimers, table of contents
- REMOVE conversational filler and redundant adjectives
- DO NOT OMIT ANY FACTUAL INFORMATION
- Preserve ALL dates, numbers, percentages, names, Acts, Articles,
  committees, locations, technical terms
- NO summarization, NO interpretation, NO reordering of facts
- Preserve chronological and thematic flow

Output: Ultra-dense plaintext preserving every fact.

TEXT:
{text}
"""

CLEAN_PROMPT = """You are a text sanitation engine.

Task:
- Remove formatting noise like **, __, extra markdown symbols
- Remove duplicated separators (====, ----)
- Preserve ALL content and facts
- Do NOT summarize, reorder, or add anything

Output: Clean plain text.

TEXT:
{text}
"""


def zero_loss_compress(text: str) -> str:
    """Remove noise while preserving every fact."""
    return call_gemini(COMPRESS_PROMPT.format(text=text))


def clean_text(text: str) -> str:
    """Remove markdown/formatting artifacts."""
    return call_gemini(CLEAN_PROMPT.format(text=text))
