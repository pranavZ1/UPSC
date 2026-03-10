# db.py — MongoDB connection singleton for UPSC Engine
#
# All collections are accessed via get_db().collection_name
# Binary files (PDFs, MP3s, images) are stored in GridFS.

import os
from functools import lru_cache
from dotenv import load_dotenv
from pymongo import MongoClient
import gridfs

load_dotenv()

_client = None
_db = None
_fs = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.environ.get("MONGODB_URI", "")
        if not uri:
            raise RuntimeError("MONGODB_URI not set in .env")
        _client = MongoClient(uri)
    return _client


def get_db():
    """Return the UPSC database handle."""
    global _db
    if _db is None:
        _db = _get_client().get_database()  # DB name is in the URI ("UPSC")
    return _db


def get_gridfs() -> gridfs.GridFS:
    """Return a GridFS handle for storing binary files."""
    global _fs
    if _fs is None:
        _fs = gridfs.GridFS(get_db())
    return _fs


# ─── Collection accessors (for convenience) ──────────────────────────────

def books_col():
    """Books metadata collection."""
    return get_db()["books"]


def articles_col():
    """Articles metadata collection."""
    return get_db()["articles"]


def structures_col():
    """Book chapter/topic structures."""
    return get_db()["book_structures"]


def chunks_col():
    """Book text chunks (for FAISS rebuild)."""
    return get_db()["book_chunks"]


def audio_col():
    """Audio scripts (JSON)."""
    return get_db()["audio_scripts"]


def mindmaps_col():
    """Mind map images (binary)."""
    return get_db()["mindmaps"]


def infographics_col():
    """Infographic images (binary)."""
    return get_db()["infographics"]


def flashcards_col():
    """Flash cards per topic + super cards."""
    return get_db()["flashcards"]


def quiz_dumps_col():
    """Large question dumps per chapter."""
    return get_db()["quiz_dumps"]


def cheatsheets_col():
    """Cheat sheets per book."""
    return get_db()["cheatsheets"]


def evaluations_col():
    """Answer evaluations."""
    return get_db()["evaluations"]


def pipeline_status_col():
    """Pipeline progress tracking per book."""
    return get_db()["pipeline_status"]


def article_content_col():
    """Processed article content (text)."""
    return get_db()["article_content"]


def pyq_questions_col():
    """PYQ classified questions (one doc per question)."""
    return get_db()["pyq_questions"]


def pyq_explanations_col():
    """PYQ answer explanations cache."""
    return get_db()["pyq_explanations"]


# ─── Ensure indexes ──────────────────────────────────────────────────────

def ensure_indexes():
    """Create MongoDB indexes for common queries. Call once on startup."""
    books_col().create_index("created_at")
    articles_col().create_index("created_at")
    articles_col().create_index("status")
    audio_col().create_index("book_id")
    mindmaps_col().create_index("book_id")
    infographics_col().create_index("book_id")
    flashcards_col().create_index("book_id")
    quiz_dumps_col().create_index("book_id")
    pipeline_status_col().create_index("book_id")
    article_content_col().create_index([("file_stem", 1), ("category", 1), ("exam", 1)])
    pyq_questions_col().create_index("year")
    pyq_questions_col().create_index("topic")
    pyq_questions_col().create_index("qid", unique=True)
    pyq_explanations_col().create_index("question_id", unique=True)
    article_content_col().create_index("article_id")
