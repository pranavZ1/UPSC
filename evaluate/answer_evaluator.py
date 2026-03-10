# evaluate/answer_evaluator.py  —  MongoDB-backed answer evaluation
#
# Evaluations are stored in the `evaluations` collection.
# Uploaded files are stored in GridFS with type="eval_upload".
# No local filesystem I/O.

import io
import json
import re
from datetime import datetime

from google import genai
from PIL import Image

from db import evaluations_col, get_gridfs


# ── Gemini client setup ──────────────────────────────────────────────────

_client = genai.Client()
MODEL = "gemini-2.5-flash"


# ── image extraction helpers ─────────────────────────────────────────────

def _images_from_pdf_bytes(pdf_bytes: bytes) -> list[Image.Image]:
    """Convert each page of a PDF (bytes) into a PIL Image."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required for PDF evaluation")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    doc.close()
    return images


def _read_image_bytes(data: bytes, ext: str):
    """Return (PIL.Image, mime_type) from raw bytes + extension."""
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }
    mime = mime_map.get(ext.lower(), "image/png")
    img = Image.open(io.BytesIO(data))
    return img, mime


# ── evaluation prompt ────────────────────────────────────────────────────

EVAL_PROMPT = """You are an expert UPSC answer evaluator.

Subject: {subject}

Evaluate the handwritten answer in the image(s) below. Provide:

1. **Score**: X/10
2. **Content Analysis**: Coverage of key points, accuracy, relevance
3. **Structure & Presentation**: Organization, introduction, conclusion, flow
4. **Writing Quality**: Clarity, coherence, grammar
5. **UPSC Specific Feedback**: Answer format, time management hints, keyword usage
6. **Model Answer**: A brief ideal answer outline
7. **Improvement Tips**: Specific, actionable suggestions

Be constructive and specific. Reference actual content from the answer.
Format your response in clean Markdown."""


# ── core evaluation ──────────────────────────────────────────────────────

def evaluate_text(subject: str, text: str) -> str:
    """Evaluate a plain-text answer."""
    prompt = EVAL_PROMPT.format(subject=subject) + "\n\nAnswer text:\n" + text
    resp = _client.models.generate_content(model=MODEL, contents=[prompt])
    return resp.text


def evaluate_file_bytes(subject: str, file_bytes: bytes, file_ext: str,
                        filename: str = "") -> str:
    """Evaluate an uploaded file (image or PDF) provided as raw bytes."""
    ext = file_ext.lower()
    if ext == ".pdf":
        images = _images_from_pdf_bytes(file_bytes)
    else:
        img, _ = _read_image_bytes(file_bytes, ext)
        images = [img]

    prompt = EVAL_PROMPT.format(subject=subject)
    contents = [prompt] + images
    resp = _client.models.generate_content(model=MODEL, contents=contents)
    return resp.text


# ── GridFS upload storage ────────────────────────────────────────────────

def save_eval_upload(eval_id: str, file_bytes: bytes, ext: str):
    """Store the uploaded evaluation file in GridFS."""
    fs = get_gridfs()
    # delete previous upload for same eval_id
    for old in fs.find({"type": "eval_upload", "eval_id": eval_id}):
        fs.delete(old._id)
    mime_map = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }
    mime = mime_map.get(ext.lower(), "application/octet-stream")
    fs.put(file_bytes,
           filename=f"{eval_id}{ext}",
           content_type=mime,
           type="eval_upload",
           eval_id=eval_id)


# ── MongoDB evaluation persistence ──────────────────────────────────────

def save_evaluation(eval_id: str, subject: str, result_md: str,
                    filename: str = "", method: str = "file"):
    """Upsert an evaluation document into MongoDB."""
    evaluations_col().update_one(
        {"eval_id": eval_id},
        {"$set": {
            "eval_id": eval_id,
            "subject": subject,
            "result_markdown": result_md,
            "filename": filename,
            "method": method,
            "created_at": datetime.now(),
        }},
        upsert=True,
    )


def load_evaluation(eval_id: str) -> dict | None:
    """Load a single evaluation from MongoDB."""
    return evaluations_col().find_one({"eval_id": eval_id}, {"_id": 0})


def get_recent_evaluations(limit: int = 20) -> list[dict]:
    """Return the most recent evaluations."""
    cursor = evaluations_col().find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    return list(cursor)
