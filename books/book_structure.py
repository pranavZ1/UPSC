# books/book_structure.py — Extract chapter/topic structure from a book (MongoDB)

import json
from db import structures_col


def get_book_structure(book_id: str) -> dict | None:
    """Load cached chapter/topic structure from MongoDB."""
    doc = structures_col().find_one({"_id": book_id})
    if doc:
        doc.pop("_id", None)
    return doc


def save_book_structure(book_id: str, structure: dict):
    """Save chapter/topic structure to MongoDB."""
    structure["_id"] = book_id
    structures_col().replace_one({"_id": book_id}, structure, upsert=True)


def extract_structure(book_id: str, pdf_bytes: bytes) -> dict:
    """
    Use Gemini to extract chapters & topics from the book.
    pdf_bytes: raw PDF file bytes from GridFS.
    """
    import io
    import re
    from pypdf import PdfReader
    from llm.gemini_client import call_gemini

    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    # Get first 50 pages (likely has TOC)
    sample_pages = []
    for i in range(min(50, total_pages)):
        text = reader.pages[i].extract_text()
        if text:
            sample_pages.append(f"[PAGE {i+1}]\n{text}")

    # Sample from middle and end
    for i in range(50, total_pages, max(1, total_pages // 15)):
        if i < total_pages:
            text = reader.pages[i].extract_text()
            if text:
                sample_pages.append(f"[PAGE {i+1}]\n{text}")

    book_text = "\n\n".join(sample_pages)

    # Fallback for scanned PDFs: use indexed chunks from MongoDB
    if not book_text.strip():
        print(f"   ⚠️ pypdf extracted no text for structure — trying indexed chunks...")
        from db import chunks_col
        chunk_doc = chunks_col().find_one({"_id": book_id})
        if chunk_doc and chunk_doc.get("chunks"):
            chunks = chunk_doc["chunks"]
            selected = chunks[:40]
            step = max(1, (len(chunks) - 40) // 15)
            for j in range(40, len(chunks), step):
                if j < len(chunks):
                    selected.append(chunks[j])
            book_text = "\n\n".join(
                f"[CHUNK {k+1}]\n{c}" for k, c in enumerate(selected)
            )
            print(f"   ✅ Using {len(selected)} indexed chunks for structure extraction")

        if not book_text.strip():
            print("   ❌ No text available for structure extraction")
            structure = {"book_summary": "", "chapters": []}
            save_book_structure(book_id, structure)
            return structure

    if len(book_text) > 30000:
        book_text = book_text[:30000]

    prompt = f"""Analyze this book's text and extract its COMPLETE chapter and topic structure.

RULES:
1. Identify ALL chapters/units in the book.
2. For EVERY chapter, list 3-5 key topics/sections covered. NEVER leave topics empty.
3. Each topic summary must be exactly ONE short sentence (max 20 words).
4. If the book has no clear chapters, create logical groupings based on content.
5. Return ONLY valid JSON, no markdown fences.
6. CRITICAL: Every single chapter MUST have at least 3 topics. Do NOT skip any chapter.

Return this exact JSON format:
{{
    "book_summary": "1-2 sentence overview of what this book covers",
    "chapters": [
        {{
            "chapter_number": 1,
            "chapter_title": "Chapter Title",
            "topics": [
                {{
                    "topic_title": "Topic Name",
                    "summary": "One short sentence summary"
                }}
            ]
        }}
    ]
}}

BOOK TEXT:
{book_text}

JSON:"""

    response = call_gemini(prompt)

    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        cleaned = cleaned[start:end]

    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)

    try:
        structure = json.loads(cleaned)
    except json.JSONDecodeError:
        fix_resp = call_gemini(
            "Fix this malformed JSON and return ONLY valid JSON:\n\n" + cleaned[:12000]
        )
        fixed = fix_resp.strip()
        if fixed.startswith("```"):
            fixed = fixed.split("\n", 1)[-1]
        if fixed.endswith("```"):
            fixed = fixed[:-3]
        s = fixed.find("{")
        e = fixed.rfind("}") + 1
        if s >= 0 and e > s:
            fixed = fixed[s:e]
        structure = json.loads(fixed)

    if "chapters" not in structure:
        structure = {"chapters": [], "book_summary": ""}

    for ch in structure["chapters"]:
        for i, topic in enumerate(ch.get("topics", []), 1):
            topic["topic_number"] = i

    save_book_structure(book_id, structure)
    return structure
