# books/book_registry.py — Track metadata for uploaded books (MongoDB)
#
# Stores book metadata in MongoDB 'books' collection:
#   - filename, title, category, page count, index status, pipeline progress

import uuid
from datetime import datetime

from db import books_col, get_gridfs


def register_book(filename: str, category: str, title: str = "") -> str:
    """Register a new book. Returns book_id."""
    book_id = uuid.uuid4().hex[:12]

    books_col().insert_one({
        "_id": book_id,
        "filename": filename,
        "title": title or filename.replace(".pdf", "").replace("_", " ").title(),
        "category": category,
        "indexed": False,
        "indexing": False,
        "chunk_count": 0,
        "page_count": 0,
        "size_kb": 0,
        "created_at": datetime.now().isoformat(),
        "error": None,
        "pdf_file_id": None,
        "thumbnail_file_id": None,
        # Pipeline progress
        "pipeline": {
            "status": "pending",       # pending | running | completed | error
            "phase": "",               # current phase name
            "phase_progress": 0,       # 0-100 within current phase
            "phases_done": [],         # list of completed phase names
            "total_chapters": 0,
            "current_task": "",
            "error": None,
        },
    })
    return book_id


def update_book(book_id: str, **kwargs):
    """Update fields on a book entry."""
    if kwargs:
        books_col().update_one({"_id": book_id}, {"$set": kwargs})


def update_pipeline(book_id: str, **kwargs):
    """Update pipeline sub-document fields."""
    update = {}
    for k, v in kwargs.items():
        update[f"pipeline.{k}"] = v
    if update:
        books_col().update_one({"_id": book_id}, {"$set": update})


def add_pipeline_phase_done(book_id: str, phase_name: str):
    """Mark a pipeline phase as completed."""
    books_col().update_one(
        {"_id": book_id},
        {"$addToSet": {"pipeline.phases_done": phase_name}},
    )


def get_book(book_id: str) -> dict | None:
    doc = books_col().find_one({"_id": book_id})
    if doc:
        doc["id"] = doc["_id"]
    return doc


def get_all_books() -> list[dict]:
    docs = list(books_col().find().sort("created_at", -1))
    for d in docs:
        d["id"] = d["_id"]
    return docs


def get_books_by_category(category: str) -> list[dict]:
    return [b for b in get_all_books() if b.get("category") == category]


def delete_book(book_id: str) -> dict | None:
    """Remove book from MongoDB and delete all associated data."""
    doc = books_col().find_one_and_delete({"_id": book_id})
    if not doc:
        return None
    doc["id"] = doc["_id"]

    fs = get_gridfs()

    # Delete PDF from GridFS
    if doc.get("pdf_file_id"):
        try:
            fs.delete(doc["pdf_file_id"])
        except Exception:
            pass

    # Delete thumbnail from GridFS
    if doc.get("thumbnail_file_id"):
        try:
            fs.delete(doc["thumbnail_file_id"])
        except Exception:
            pass

    # Delete all associated data from other collections
    from db import (
        structures_col, chunks_col, audio_col, mindmaps_col,
        infographics_col, flashcards_col, quiz_dumps_col,
        cheatsheets_col, pipeline_status_col,
    )
    structures_col().delete_many({"_id": book_id})
    chunks_col().delete_many({"_id": book_id})
    audio_col().delete_many({"book_id": book_id})
    mindmaps_col().delete_many({"book_id": book_id})
    infographics_col().delete_many({"book_id": book_id})
    flashcards_col().delete_many({"book_id": book_id})
    quiz_dumps_col().delete_many({"book_id": book_id})
    cheatsheets_col().delete_many({"_id": book_id})
    pipeline_status_col().delete_many({"book_id": book_id})

    # Delete ALL GridFS files linked to this book
    for gf in fs.find({"metadata.book_id": book_id}):
        fs.delete(gf._id)

    # Clean up local FAISS cache if exists
    from config import BOOKS_INDEX_DIR
    import shutil
    local_idx = BOOKS_INDEX_DIR / book_id
    if local_idx.exists():
        shutil.rmtree(local_idx, ignore_errors=True)

    return doc


def store_pdf(book_id: str, pdf_bytes: bytes, filename: str):
    """Store book PDF in GridFS and update book record."""
    fs = get_gridfs()
    file_id = fs.put(pdf_bytes, filename=filename,
                     metadata={"book_id": book_id, "type": "pdf"})
    update_book(book_id, pdf_file_id=file_id)
    return file_id


def get_pdf_bytes(book_id: str) -> bytes | None:
    """Retrieve book PDF from GridFS."""
    doc = get_book(book_id)
    if not doc or not doc.get("pdf_file_id"):
        return None
    fs = get_gridfs()
    try:
        return fs.get(doc["pdf_file_id"]).read()
    except Exception:
        return None


def store_thumbnail(book_id: str, img_bytes: bytes):
    """Store thumbnail in GridFS."""
    fs = get_gridfs()
    file_id = fs.put(img_bytes, filename=f"{book_id}_thumb.jpg",
                     metadata={"book_id": book_id, "type": "thumbnail"})
    update_book(book_id, thumbnail_file_id=file_id)
    return file_id


def get_thumbnail_bytes(book_id: str) -> bytes | None:
    """Retrieve thumbnail from GridFS."""
    doc = get_book(book_id)
    if not doc or not doc.get("thumbnail_file_id"):
        return None
    fs = get_gridfs()
    try:
        return fs.get(doc["thumbnail_file_id"]).read()
    except Exception:
        return None
