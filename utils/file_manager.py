# utils/file_manager.py  —  MongoDB + GridFS content management
#
# Content blocks live in the article_content collection.
# PDFs are generated in memory and stored in GridFS.
# No local filesystem writes.

import re
from collections import OrderedDict
from datetime import datetime

from db import article_content_col, get_gridfs

THIN_SEP  = "\u2500" * 60
THICK_SEP = "\u2550" * 60

# ── category helpers ─────────────────────────────────────────────────────
CATEGORY_SUFFIX = {
    ("prelims", "content"):     "content",
    ("prelims", "summary"):     "summary",
    ("prelims", "questions"):   "questions",
    ("prelims", "raw_content"): "raw_content",
    ("mains",   "content"):     "content",
    ("mains",   "summary"):     "summary",
    ("mains",   "questions"):   "questions",
    ("mains",   "raw_content"): "raw_content",
}


def _pdf_filename(file_stem: str, category: str, exam: str) -> str:
    suffix = CATEGORY_SUFFIX[(exam, category)]
    prefix = "mains_" if exam == "mains" else ""
    return f"{file_stem}_{prefix}{suffix}.pdf"


def _gridfs_query(file_stem: str, category: str, exam: str) -> dict:
    return {
        "type": "article_pdf",
        "file_stem": file_stem,
        "category": category,
        "exam": exam,
    }


# ── text parsing ─────────────────────────────────────────────────────────

def _extract_markers(text: str) -> tuple[str, str]:
    subtopic = ""
    focus = ""
    for line in text.split("\n"):
        m = re.match(r"^\[SUBTOPIC\]\s*(.+)", line)
        if m:
            subtopic = m.group(1).strip()
        m = re.match(r"^\[FOCUS\]\s*(.+)", line)
        if m:
            focus = m.group(1).strip()
        if subtopic and focus:
            break
    return subtopic, focus


def _extract_body(text: str) -> str:
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("[SUBTOPIC]") or line.startswith("[FOCUS]") or not line.strip():
            body_start = i + 1
        else:
            break
    return "\n".join(lines[body_start:]).strip()


def _serialize_organized(structure: OrderedDict) -> str:
    parts: list[str] = []
    subtopic_items = list(structure.items())
    for si, (subtopic, focuses) in enumerate(subtopic_items):
        parts.append(f"[SUBTOPIC] {subtopic}")
        parts.append("")
        focus_items = list(focuses.items())
        for fi, (focus, blocks) in enumerate(focus_items):
            parts.append(f"[FOCUS] {focus}")
            parts.append("")
            for bi, block in enumerate(blocks):
                parts.append(block)
                if bi < len(blocks) - 1:
                    parts.append("")
                    parts.append(THIN_SEP)
                    parts.append("")
            parts.append("")
        if si < len(subtopic_items) - 1:
            parts.append(THICK_SEP)
            parts.append("")
    return "\n".join(parts)


# ── MongoDB storage ──────────────────────────────────────────────────────

def _store_block(article_id, file_stem, category, exam, subtopic, focus, text):
    article_content_col().insert_one({
        "article_id": article_id or "",
        "file_stem": file_stem,
        "category": category,
        "exam": exam,
        "subtopic": subtopic or "General",
        "focus": focus or "General",
        "text": text,
        "created_at": datetime.now(),
    })


# ── GridFS PDF helpers ───────────────────────────────────────────────────

def _store_pdf(file_stem, category, exam, content_text):
    from utils.pdf_creator import build_pdf_bytes
    fs = get_gridfs()
    query = _gridfs_query(file_stem, category, exam)
    filename = _pdf_filename(file_stem, category, exam)
    for old in fs.find(query):
        fs.delete(old._id)
    pdf_bytes = build_pdf_bytes(content_text)
    fs.put(pdf_bytes, filename=filename, content_type="application/pdf", **query)


def _delete_pdf(file_stem, category, exam):
    fs = get_gridfs()
    query = _gridfs_query(file_stem, category, exam)
    for old in fs.find(query):
        fs.delete(old._id)


# ── rebuild from MongoDB ─────────────────────────────────────────────────

def _rebuild_structured(file_stem, category, exam):
    blocks = list(article_content_col().find({
        "file_stem": file_stem, "category": category, "exam": exam,
    }).sort("created_at", 1))
    if not blocks:
        _delete_pdf(file_stem, category, exam)
        return
    structure: OrderedDict = OrderedDict()
    for block in blocks:
        sub = block.get("subtopic", "General")
        foc = block.get("focus", "General")
        structure.setdefault(sub, OrderedDict()).setdefault(foc, []).append(block["text"])
    content = _serialize_organized(structure)
    _store_pdf(file_stem, category, exam, content)


def _rebuild_raw(file_stem, exam):
    blocks = list(article_content_col().find({
        "file_stem": file_stem, "category": "raw_content", "exam": exam,
    }).sort("created_at", 1))
    if not blocks:
        _delete_pdf(file_stem, "raw_content", exam)
        return
    SEP = "\n\n" + "\u2500" * 60 + "\n\n"
    topic_name = blocks[0].get("subtopic", "")
    parts = []
    if topic_name and topic_name != "General":
        parts.append(f"Title: {topic_name}\n")
    for block in blocks:
        parts.append(block["text"])
    content = SEP.join(parts) + "\n"
    _store_pdf(file_stem, "raw_content", exam, content)


# ── smart append ─────────────────────────────────────────────────────────

def _smart_append(file_stem, category, exam, text, article_id=""):
    subtopic, focus = _extract_markers(text)
    body = _extract_body(text)
    if not subtopic:
        subtopic = "General"
    if not focus:
        focus = "General"
    _store_block(article_id, file_stem, category, exam, subtopic, focus, body)
    _rebuild_structured(file_stem, category, exam)


# ── public API (prelims) ─────────────────────────────────────────────────

def append_content(file_stem, text, article_id=""):
    _smart_append(file_stem, "content", "prelims", text, article_id)

def append_summary(file_stem, text, article_id=""):
    _smart_append(file_stem, "summary", "prelims", text, article_id)

def append_qa(file_stem, text, article_id=""):
    _smart_append(file_stem, "questions", "prelims", text, article_id)

def append_raw_content(file_stem, text, topic_name="", article_id=""):
    _store_block(article_id, file_stem, "raw_content", "prelims",
                 topic_name or "General", "", text.strip())
    _rebuild_raw(file_stem, "prelims")


# ── public API (mains) ───────────────────────────────────────────────────

def append_mains_content(file_stem, text, article_id=""):
    _smart_append(file_stem, "content", "mains", text, article_id)

def append_mains_summary(file_stem, text, article_id=""):
    _smart_append(file_stem, "summary", "mains", text, article_id)

def append_mains_qa(file_stem, text, article_id=""):
    _smart_append(file_stem, "questions", "mains", text, article_id)

def append_mains_raw_content(file_stem, text, topic_name="", article_id=""):
    _store_block(article_id, file_stem, "raw_content", "mains",
                 topic_name or "General", "", text.strip())
    _rebuild_raw(file_stem, "mains")


# ── article content removal ──────────────────────────────────────────────

def remove_article_content(article_id, file_stems=None):
    results = {}
    blocks = list(article_content_col().find(
        {"article_id": article_id},
        {"file_stem": 1, "category": 1, "exam": 1},
    ))
    to_rebuild = set()
    for block in blocks:
        to_rebuild.add((block["file_stem"], block["category"], block["exam"]))
    article_content_col().delete_many({"article_id": article_id})
    for stem, category, exam in to_rebuild:
        if stem not in results:
            results[stem] = []
        if category == "raw_content":
            _rebuild_raw(stem, exam)
        else:
            _rebuild_structured(stem, category, exam)
        label = f"{exam}_{category}"
        remaining = article_content_col().count_documents({
            "file_stem": stem, "category": category, "exam": exam,
        })
        results[stem].append(f"{label}:{'cleaned' if remaining > 0 else 'deleted'}")
    return results


# ── query helpers (used by app.py) ───────────────────────────────────────

def list_article_pdfs(exam_category: str):
    if exam_category.startswith("mains_"):
        exam, category = "mains", exam_category[6:]
    else:
        exam, category = "prelims", exam_category
    fs = get_gridfs()
    query = {"type": "article_pdf", "exam": exam, "category": category}
    results = []
    for f in fs.find(query):
        results.append({
            "filename": f.filename,
            "file_stem": getattr(f, "file_stem", f.filename.replace(".pdf", "")),
            "size_kb": round(f.length / 1024, 1),
            "modified": f.upload_date.strftime("%d %b %Y, %I:%M %p"),
        })
    results.sort(key=lambda x: x["filename"])
    return results


def get_article_pdf_bytes(exam_category: str, filename: str):
    if exam_category.startswith("mains_"):
        exam, category = "mains", exam_category[6:]
    else:
        exam, category = "prelims", exam_category
    fs = get_gridfs()
    f = fs.find_one({
        "type": "article_pdf",
        "exam": exam,
        "category": category,
        "filename": filename,
    })
    if f:
        return f.read()
    return None


def count_article_pdfs():
    fs = get_gridfs()
    cats = [
        "raw_content", "content", "summary", "questions",
        "mains_raw_content", "mains_content", "mains_summary", "mains_questions",
    ]
    counts = {}
    for cat in cats:
        if cat.startswith("mains_"):
            exam, c = "mains", cat[6:]
        else:
            exam, c = "prelims", cat
        # GridFS .find().count() counts matching files
        cursor = fs.find({"type": "article_pdf", "exam": exam, "category": c})
        cnt = 0
        for _ in cursor:
            cnt += 1
        counts[cat] = cnt
    return counts
