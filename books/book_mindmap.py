# books/book_mindmap.py — Generate AI-illustrated mind map images (MongoDB)

import re
import base64
from pathlib import Path

import fitz  # PyMuPDF

from config import BASE_DIR
from db import mindmaps_col


# ── Cache helpers ─────────────────────────────────────────────────────────────

def get_cached_mindmap(book_id: str, chapter_idx: int) -> dict | None:
    """Return cached mind-map image as a base64 data URI from MongoDB."""
    doc = mindmaps_col().find_one({"_id": f"{book_id}_ch{chapter_idx}"})
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
        extracted = "\n\n".join(chapter_text)
        print(f"📄 Extracted {extract_end - start_page} pages via ToC match")
        return extracted

    print(f"⚠️  No ToC match for '{chapter_title}'. Falling back to keyword search.")

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


# ── Prompt template ───────────────────────────────────────────────────────────

_PROMPT_INSTRUCTION = """You are an expert prompt engineer writing a prompt for Google's Nano Banana 2 (Gemini 3.1 Flash Image) model.

Your task is to write an image generation prompt that produces an educational mindmap based on the provided text, but STRICTLY adhering to the exact visual style, layout, typography, and color palette of the provided REFERENCE IMAGE (if available).

REFERENCE STYLE OBSERVATIONS (replicate these exactly):
- Central core badge/node with a title and small icon.
- Horizontal, thematic flow: Main branches spreading left and right with thick, colorful, curvy swooshes (deep teal, orange, red, blue).
- Branch endpoints use brackets or colored text boxes enclosing sub-lists.
- Cream/off-white background with a warm/vintage educational poster feel.
- Clean vector art style with professional, highly legible sans-serif typography.
- Small illustrative vector icons next to the major topic nodes.
- High density of accurate text capturing the chapter's facts.

CRITICAL RULES FOR NANO BANANA 2:
1. ZERO INACCURACIES: Every word, number, and date must be 100% accurate.
2. ABSOLUTELY ZERO SPELLING MISTAKES.
3. ADAPT TO TEXT: Formulate branches based on the chapter text structure.
4. NO LOREM IPSUM OR GIBBERISH.

YOUR OUTPUT PROMPT MUST FOLLOW THIS EXACT STRUCTURE:

Start with: "A professional, highly detailed horizontal layout mindmap about '{chapter_topic}'. CRITICAL INSTRUCTION: THE HIGHEST PRIORITY IS FLAWLESS, PERFECT TEXT RENDERING WITH ABSOLUTELY ZERO SPELLING ERRORS AND ZERO GIBBERISH. EVERY WORD MUST BE SPELLED EXACTLY CORRECTLY. Cream/off-white background. The poster perfectly mirrors the reference image style: central title node, thick curvy colorful branches spreading left and right, clean vector icons for each main theme, and distinct text lists using brackets or colored nodes. Professional typography, subtle shading."

Then describe:
1. "CENTRAL NODE: A large title '[EXACT TITLE]' with a decorative compass or relevant icon. (SPELL PERFECTLY). IMPORTANT: DO NOT INCLUDE THE CHAPTER NUMBER IN THE TITLE. JUST THE TOPIC NAME."
2. "LEFT BRANCHES: [N] thick swooping lines in [COLORS]. Titled '[SUBTOPIC]'. Details: '[FACTS/DATES]'. CRITICAL: Ensure absolutely perfect spelling and legibility."
3. "RIGHT BRANCHES: [N] thick swooping lines in [COLORS]. Titled '[SUBTOPIC]'. Details: '[FACTS/DATES]'. CRITICAL: Ensure absolutely perfect spelling and legibility."

IMPORTANT: Replace all bracketed placeholders with specific, accurate facts from the chapter text."""


_REF_IMAGE_CANDIDATES = [
    BASE_DIR / "static" / "mindmap_reference.jpg",
    BASE_DIR / "data" / "download.jpg",
]


def _upload_reference_image(client):
    for path in _REF_IMAGE_CANDIDATES:
        if path.exists():
            try:
                ref = client.files.upload(file=str(path))
                print("📸 Uploaded mindmap reference image.")
                return ref
            except Exception as e:
                print(f"⚠️  Could not upload reference image: {e}")
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def generate_mindmap(
    book_id: str, chapter_idx: int, chapter_title: str,
    topics: list[dict], book_title: str = "", pdf_bytes: bytes | None = None,
) -> dict:
    """Generate an AI-illustrated mind map image for a chapter."""
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
        print("📎 Falling back to RAG context…")
        try:
            from books.book_chat import _retrieve_chunks
            query = chapter_title + ": " + ", ".join(t["topic_title"] for t in topics)
            chunks = _retrieve_chunks(book_id, query, top_k=6)
            chapter_text = "\n".join(chunks[:3]) if chunks else ""
        except Exception:
            chapter_text = ""

    ref_image = _upload_reference_image(client)

    clean_topic = re.sub(r'^\d+[\s.\-]*', '', chapter_title).strip()
    print(f"🧠 Distilling mindmap content for: {clean_topic}")

    if chapter_text:
        context_prompt = (
            f'Here is the chapter text about "{clean_topic}":\n\n'
            f'<CHAPTER_TEXT>\n{chapter_text[:20000]}\n</CHAPTER_TEXT>\n\n'
            f'Based on this textbook content and the provided reference image layout, '
            f'{_PROMPT_INSTRUCTION}'
        )
    else:
        topic_list = "\n".join(f"- {t['topic_title']}" for t in topics)
        context_prompt = (
            f'The chapter is titled "{clean_topic}" and covers these topics:\n'
            f'{topic_list}\n\n{_PROMPT_INSTRUCTION}'
        )

    contents = [ref_image, context_prompt] if ref_image else context_prompt

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=contents,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    image_prompt = response.text.strip()
    print(f"🎨 Generated mindmap image prompt ({len(image_prompt)} chars)")

    print("🖼️  Generating mindmap image with nano-banana-pro-preview…")
    image_contents = [ref_image, image_prompt] if ref_image else image_prompt

    result = client.models.generate_content(
        model="nano-banana-pro-preview", contents=image_contents,
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
        return {"error": "Mind map image generation failed. Please try again."}

    # Store in MongoDB
    mindmaps_col().replace_one(
        {"_id": f"{book_id}_ch{chapter_idx}"},
        {"_id": f"{book_id}_ch{chapter_idx}", "book_id": book_id,
         "chapter_idx": chapter_idx, "image_data": img_bytes},
        upsert=True,
    )

    b64 = base64.b64encode(img_bytes).decode("ascii")
    print(f"✅ Mindmap saved to MongoDB")
    return {"image": f"data:image/png;base64,{b64}"}

