# utils/article_registry.py — MongoDB-backed article metadata tracking
#
# Replaces the old JSON-file registry with MongoDB.
# Same function signatures for backward compatibility with pipeline.py & app.py.

import uuid
from datetime import datetime
from typing import Optional

from db import articles_col


def register_article(
    filename: str,
    file_type: str = "upload",
    title: str = "",
) -> str:
    """
    Register a new article and return its unique article_id.

    Args:
        filename: Original filename or "pasted_text" for text paste
        file_type: "upload" or "paste"
        title: Article title (can be set later after Gemini generates it)

    Returns:
        article_id (UUID string)
    """
    article_id = uuid.uuid4().hex[:12]
    articles_col().insert_one({
        "_id": article_id,
        "filename": filename,
        "file_type": file_type,
        "title": title or filename,
        "topics": [],
        "subtopics": [],
        "file_stems": [],
        "status": "uploaded",
        "created_at": datetime.now().isoformat(),
        "processed_at": None,
        "error": None,
    })
    return article_id


def update_status(article_id: str, status: str, error: str = None):
    """Update the processing status of an article."""
    updates = {"status": status}
    if status == "processed":
        updates["processed_at"] = datetime.now().isoformat()
    if error:
        updates["error"] = error
    articles_col().update_one({"_id": article_id}, {"$set": updates})


def add_topic(article_id: str, main_topic: str, subtopic: str, file_stem: str):
    """Record that this article was classified under a topic."""
    add_to_set = {"topics": main_topic, "file_stems": file_stem}
    if subtopic:
        add_to_set["subtopics"] = subtopic
    articles_col().update_one(
        {"_id": article_id},
        {"$addToSet": add_to_set},
    )


def set_title(article_id: str, title: str):
    """Set the Gemini-generated article title."""
    articles_col().update_one({"_id": article_id}, {"$set": {"title": title}})


def get_article(article_id: str) -> Optional[dict]:
    """Get a single article's metadata."""
    doc = articles_col().find_one({"_id": article_id})
    if doc:
        doc["id"] = doc["_id"]
    return doc


def get_all_articles() -> list[dict]:
    """Get all articles as a list, sorted by creation time (newest first)."""
    docs = list(articles_col().find().sort("created_at", -1))
    for d in docs:
        d["id"] = d["_id"]
    return docs


def get_uploaded_articles() -> list[dict]:
    """Get articles with status 'uploaded' (pending processing)."""
    return [a for a in get_all_articles() if a["status"] == "uploaded"]


def get_processed_articles() -> list[dict]:
    """Get articles with status 'processed'."""
    return [a for a in get_all_articles() if a["status"] == "processed"]


def delete_article(article_id: str) -> Optional[dict]:
    """
    Remove an article from MongoDB and return its metadata
    (so the caller can cascade-delete content + input files).
    """
    doc = articles_col().find_one_and_delete({"_id": article_id})
    if doc:
        doc["id"] = doc["_id"]
    return doc


def get_articles_by_status() -> dict:
    """Group articles by status for dashboard display."""
    all_articles = get_all_articles()
    return {
        "uploaded": [a for a in all_articles if a["status"] == "uploaded"],
        "processing": [a for a in all_articles if a["status"] == "processing"],
        "processed": [a for a in all_articles if a["status"] == "processed"],
        "error": [a for a in all_articles if a["status"] == "error"],
    }
