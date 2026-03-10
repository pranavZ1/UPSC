# books/book_indexer.py — Extract text from book PDF, chunk, embed, store in FAISS + MongoDB
#
# RAG pipeline:
#   1. Extract text from PDF (pypdf → fitz → Gemini Vision OCR)
#   2. Chunk text (~800 tokens with 100 overlap)
#   3. Embed each chunk using Gemini embedding
#   4. Build FAISS index — stored in GridFS + local cache
#   5. Save chunk texts to MongoDB

import json
import time
import tempfile
import numpy as np
import faiss
from pathlib import Path

from config import BOOKS_INDEX_DIR, EMBEDDING_MODEL, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP
from db import chunks_col, get_gridfs


# ─── Text extraction ─────────────────────────────────────────────────────

def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> tuple[str, int]:
    """
    Extract text and page count from PDF bytes.
    Strategy: pypdf → PyMuPDF → Gemini Vision OCR
    """
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages.append(text)

    if pages:
        return "\n\n".join(pages), page_count

    print("   ⚠️ pypdf extracted no text — trying PyMuPDF...")

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    pages = []
    for pg in doc:
        text = pg.get_text()
        if text and text.strip():
            pages.append(text)
    doc.close()

    if pages:
        return "\n\n".join(pages), page_count

    print("   ⚠️ PyMuPDF also found no text — falling back to Gemini Vision OCR...")
    pages = _ocr_pdf_with_vision(pdf_bytes, page_count)
    if pages:
        return "\n\n".join(pages), page_count

    return "", page_count


def _ocr_pdf_with_vision(pdf_bytes: bytes, page_count: int) -> list[str]:
    """Render each PDF page as image and OCR with Gemini Vision."""
    import fitz
    import io
    from PIL import Image
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    OCR_PROMPT = (
        "Extract ALL text from this scanned book page image. "
        "Reproduce every word, number, heading, bullet point, and footnote exactly. "
        "Preserve the original structure. "
        "If text is partially obscured, do your best to infer it. "
        "Do NOT hallucinate text. If unreadable, output 'UNREADABLE'. "
        "Output plain text only."
    )

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    max_pages = min(page_count, 350)
    pages_text = []

    print(f"   🔍 OCR-ing {max_pages} pages with Gemini Vision...")

    for i in range(max_pages):
        pg = doc[i]
        pix = pg.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.convert("L").save(buf, "JPEG", quality=95)
        jpg_bytes = buf.getvalue()

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(text=OCR_PROMPT),
                                types.Part(inline_data=types.Blob(
                                    mime_type="image/jpeg", data=jpg_bytes,
                                )),
                            ],
                        )
                    ],
                )
                text = response.text.strip() if response.text else ""
                if text and text != "UNREADABLE":
                    pages_text.append(text)
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 2 ** attempt * 5
                    print(f"   ⏳ Rate limited on page {i+1}, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"   ⚠️ OCR failed for page {i+1}: {e}")
                    break

        if (i + 1) % 10 == 0 or i == max_pages - 1:
            print(f"   📄 OCR progress: {i+1}/{max_pages} ({len(pages_text)} extracted)")
        time.sleep(0.5)

    doc.close()
    return pages_text


# ─── Chunking ────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = RAG_CHUNK_SIZE,
                overlap: int = RAG_CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


# ─── Embedding ────────────────────────────────────────────────────────────

def _embed_texts(texts: list[str], batch_size: int = 10) -> np.ndarray:
    """Embed using Gemini embedding API with retry."""
    from google import genai
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    all_embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i: i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL, contents=batch,
                )
                for emb in result.embeddings:
                    all_embeddings.append(emb.values)
                print(f"   Batch {batch_num}/{total_batches} done ({len(all_embeddings)}/{total})")
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 2 ** attempt * 5
                    print(f"   ⏳ Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
        else:
            raise RuntimeError(f"Failed after {max_retries} retries")

        if i + batch_size < total:
            time.sleep(2)

    return np.array(all_embeddings, dtype=np.float32)


# ─── FAISS index management ──────────────────────────────────────────────

def _save_index_local(book_id: str, embeddings: np.ndarray):
    """Save FAISS index to local disk cache."""
    index_dir = BOOKS_INDEX_DIR / book_id
    index_dir.mkdir(parents=True, exist_ok=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(index_dir / "index.faiss"))

    (index_dir / "meta.json").write_text(
        json.dumps({"dim": dim, "count": embeddings.shape[0]}), encoding="utf-8"
    )
    return index


def _save_index_gridfs(book_id: str, embeddings: np.ndarray):
    """Store FAISS index binary in GridFS for persistence."""
    index_dir = BOOKS_INDEX_DIR / book_id
    index_path = index_dir / "index.faiss"

    if not index_path.exists():
        return

    fs = get_gridfs()
    # Remove old if exists
    for old in fs.find({"metadata.book_id": book_id, "metadata.type": "faiss_index"}):
        fs.delete(old._id)

    fs.put(
        index_path.read_bytes(),
        filename=f"{book_id}_index.faiss",
        metadata={"book_id": book_id, "type": "faiss_index"},
    )


def _save_chunks_mongodb(book_id: str, chunks: list[str]):
    """Store text chunks in MongoDB."""
    chunks_col().replace_one(
        {"_id": book_id},
        {"_id": book_id, "chunks": chunks, "count": len(chunks)},
        upsert=True,
    )


def load_index(book_id: str):
    """
    Load FAISS index + chunks.
    1. Check local cache
    2. If not present, download from GridFS
    Returns (faiss.Index, list[str]) or None.
    """
    index_dir = BOOKS_INDEX_DIR / book_id
    index_path = index_dir / "index.faiss"

    # Load chunks from MongoDB
    chunk_doc = chunks_col().find_one({"_id": book_id})
    if not chunk_doc:
        return None
    chunks = chunk_doc.get("chunks", [])

    # Check local FAISS cache
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        return index, chunks

    # Download from GridFS
    fs = get_gridfs()
    cursor = fs.find({"metadata.book_id": book_id, "metadata.type": "faiss_index"})
    gf = next(cursor, None)
    if not gf:
        return None

    index_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_bytes(gf.read())
    index = faiss.read_index(str(index_path))
    return index, chunks


# ─── Main indexing pipeline ──────────────────────────────────────────────

def index_book(book_id: str, pdf_bytes: bytes) -> dict:
    """
    Full indexing pipeline for a book (using PDF bytes from GridFS):
    1. Extract text
    2. Chunk
    3. Embed
    4. Store FAISS index (local + GridFS) + chunks in MongoDB

    Returns: {"page_count": int, "chunk_count": int}
    """
    print(f"📖 Extracting text from book {book_id}...")
    text, page_count = _extract_text_from_pdf_bytes(pdf_bytes)

    if not text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    print(f"✅ Extracted {len(text)} chars from {page_count} pages")

    print(f"🔄 Chunking text (size={RAG_CHUNK_SIZE}, overlap={RAG_CHUNK_OVERLAP})...")
    chunks = _chunk_text(text)
    print(f"✅ Created {len(chunks)} chunks")

    # Save chunks to MongoDB
    _save_chunks_mongodb(book_id, chunks)
    print(f"💾 Chunks saved to MongoDB")

    print(f"🔄 Generating embeddings ({len(chunks)} chunks)...")
    embeddings = _embed_texts(chunks)
    print(f"✅ Embeddings: shape {embeddings.shape}")

    # Save FAISS index locally + to GridFS
    print(f"💾 Saving FAISS index...")
    _save_index_local(book_id, embeddings)
    _save_index_gridfs(book_id, embeddings)
    print(f"✅ Index saved for book {book_id}")

    return {"page_count": page_count, "chunk_count": len(chunks)}
