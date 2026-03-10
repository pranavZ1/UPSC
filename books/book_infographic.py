# books/book_infographic.py — Generate AI-illustrated infographic images (MongoDB)

import re
import base64
from pathlib import Path

import fitz  # PyMuPDF

from db import infographics_col


# ── Cache helpers ─────────────────────────────────────────────────────────────

def get_cached_infographic(book_id: str, chapter_idx: int) -> dict | None:
    """Return cached infographic as base64 data URI from MongoDB."""
    doc = infographics_col().find_one({"_id": f"{book_id}_ch{chapter_idx}"})
    if doc and doc.get("image_data"):
        b64 = base64.b64encode(doc["image_data"]).decode("ascii")
        return {"image": f"data:image/png;base64,{b64}"}
    return None


# ── PDF chapter text extraction ───────────────────────────────────────────────

def _extract_chapter_text_from_bytes(pdf_bytes: bytes, chapter_title: str) -> str:
    """Extract full text of a chapter from PDF bytes using ToC."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    toc = doc.get_toc()
    start_page = -1
    end_page = -1

    if toc:
        topic_lower = chapter_title.strip().lower()
        for i, (level, title, page) in enumerate(toc):
            cleaned = title.strip().lower()
            if cleaned == topic_lower or (level == 2 and topic_lower in cleaned):
                start_page = page - 1
                for j in range(i + 1, len(toc)):
                    next_level, _, next_page = toc[j]
                    if next_level <= level:
                        end_page = next_page - 1
                        break
                if end_page == -1:
                    end_page = total_pages - 1
                break

    if start_page != -1:
        extract_end = min(end_page, start_page + 60)
        chapter_text = []
        for pn in range(start_page, extract_end):
            text = doc[pn].get_text()
            if text.strip():
                chapter_text.append(f"--- Page {pn + 1} ---\n{text}")
        doc.close()
        return "\n\n".join(chapter_text)

    keywords = [kw for kw in chapter_title.lower().split() if len(kw) > 2]
    matching_pages = []
    for pn in range(total_pages):
        text_lower = doc[pn].get_text().lower()
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= max(1, len(keywords) // 2):
            matching_pages.append(pn)

    if not matching_pages:
        for pn in range(total_pages):
            text_lower = doc[pn].get_text().lower()
            if any(kw in text_lower for kw in keywords):
                matching_pages.append(pn)

    if not matching_pages:
        doc.close()
        return ""

    first = matching_pages[0]
    s = max(0, first - 1)
    e = min(total_pages - 1, s + 30)
    chapter_text = []
    for pn in range(s, e + 1):
        text = doc[pn].get_text()
        if text.strip():
            chapter_text.append(f"--- Page {pn + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(chapter_text)


_PROMPT_INSTRUCTION = """You are an expert prompt engineer writing a prompt for Google's Nano Banana 2 (Gemini 3.1 Flash Image) model.

Your task is to write an image generation prompt that produces a NotebookLM-style educational infographic that perfectly balances RICH VECTOR ILLUSTRATIONS with SUBSTANTIAL READABLE TEXT.

REFERENCE STYLE:
- Cream/off-white background with soft geometric line patterns
- Multiple distinct visual panels or sections
- Text includes: article numbers, short explanatory sentences, comparison data, durations, and key facts
- A supporting details section with a decorative banner containing multiple items
- Professional typography, clean vector art style, subtle shading
- NotebookLM watermark in the bottom right corner

CRITICAL RULES:
1. ZERO INACCURACIES: Every word, number, and date must be 100% accurate.
2. ZERO SPELLING MISTAKES.
3. NO LOREM IPSUM OR GIBBERISH.
4. TEXT MUST BE COMPREHENSIVE & PROPORTIONAL.
5. ILLUSTRATIONS MUST BE DETAILED.
6. LIGHT THEME ONLY: Cream/off-white background.

YOUR OUTPUT PROMPT MUST FOLLOW THIS EXACT STRUCTURE:

Start with: "A professional, highly detailed, high-resolution educational infographic poster about '{chapter_topic}' in the NotebookLM style. THE HIGHEST PRIORITY IS PERFECT TEXT RENDERING WITH ABSOLUTELY ZERO SPELLING ERRORS. Cream/off-white background with subtle decorative line patterns. Professional typography, clean vector art style."

Then describe:
1. "TOP HEADER: A large, bold title '[EXACT TITLE]' with a decorative vector illustration. Below, a comprehensive intro paragraph. THE TEXT MUST BE SPELLED FLAWLESSLY."
2. "MAIN BODY: [N] colored panels arranged in a grid. - [For EVERY major subtopic, describe a panel]: Titled '[SUBTOPIC]' on a [COLOR] background, featuring a vector illustration. Below: '[DESCRIPTIVE SENTENCES]'. Data labels: '[LABEL]: [FACT]'."
3. "SUPPORTING DETAILS SECTION: A decorative banner containing [N] items with icons and text explanations."

IMPORTANT: Replace ALL bracketed placeholders with REAL content from the chapter."""


def generate_infographic(
    book_id: str, chapter_idx: int, chapter_title: str,
    topics: list[dict], pdf_bytes: bytes | None = None,
) -> dict:
    """Generate an AI-illustrated infographic image for a chapter."""
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    chapter_text = ""
    if pdf_bytes:
        chapter_text = _extract_chapter_text_from_bytes(pdf_bytes, chapter_title)

    if not chapter_text:
        try:
            from books.book_chat import _retrieve_chunks
            query = chapter_title + ": " + ", ".join(t["topic_title"] for t in topics)
            chunks = _retrieve_chunks(book_id, query, top_k=6)
            chapter_text = "\n".join(chunks[:3]) if chunks else ""
        except Exception:
            chapter_text = ""

    print(f"🧠 Distilling content for: {chapter_title}")

    prompt_instruction = _PROMPT_INSTRUCTION.replace(
        "'{chapter_topic}'", f"'{chapter_title}'"
    )

    if chapter_text:
        context_prompt = (
            f'Here is the chapter text about "{chapter_title}":\n\n'
            f'<CHAPTER_TEXT>\n{chapter_text[:20000]}\n</CHAPTER_TEXT>\n\n'
            f'Based on this textbook content, {prompt_instruction}'
        )
    else:
        topic_list = "\n".join(f"- {t['topic_title']}" for t in topics)
        context_prompt = (
            f'The chapter is titled "{chapter_title}" and covers these topics:\n'
            f'{topic_list}\n\n{prompt_instruction}'
        )

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=context_prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    image_prompt = response.text.strip()
    print(f"🎨 Generated image prompt ({len(image_prompt)} chars)")

    print("🖼️  Generating image with nano-banana-pro-preview…")
    result = client.models.generate_content(
        model="nano-banana-pro-preview", contents=image_prompt,
    )

    img_bytes = None
    if result.candidates:
        for candidate in result.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        raw = part.inline_data.data
                        if isinstance(raw, bytes) and raw[:4] != b"\x89PNG":
                            try:
                                img_bytes = base64.b64decode(raw)
                            except Exception:
                                img_bytes = raw
                        else:
                            img_bytes = raw
                        break
            if img_bytes:
                break

    if not img_bytes:
        return {"error": "Image generation failed. Please try again."}

    # Store in MongoDB
    infographics_col().replace_one(
        {"_id": f"{book_id}_ch{chapter_idx}"},
        {"_id": f"{book_id}_ch{chapter_idx}", "book_id": book_id,
         "chapter_idx": chapter_idx, "image_data": img_bytes},
        upsert=True,
    )

    b64 = base64.b64encode(img_bytes).decode("ascii")
    print(f"✅ Infographic saved to MongoDB")
    return {"image": f"data:image/png;base64,{b64}"}
