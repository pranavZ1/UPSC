# books/book_chat.py — RAG-powered chat engine for books (MongoDB)

import re
import numpy as np
import faiss

from config import EMBEDDING_MODEL, RAG_TOP_K
from books.book_indexer import load_index


def _embed_query(query: str) -> np.ndarray:
    """Embed a single query string."""
    from google import genai
    from dotenv import load_dotenv
    import os

    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    result = client.models.embed_content(
        model=EMBEDDING_MODEL, contents=[query],
    )
    vec = np.array([result.embeddings[0].values], dtype=np.float32)
    faiss.normalize_L2(vec)
    return vec


def _retrieve_chunks(book_id: str, query: str, top_k: int = RAG_TOP_K) -> list[str]:
    """Retrieve top-k relevant chunks from the book's FAISS index."""
    loaded = load_index(book_id)
    if loaded is None:
        return []

    index, chunks = loaded
    query_vec = _embed_query(query)

    k = min(top_k, len(chunks))
    scores, indices = index.search(query_vec, k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(chunks):
            results.append(chunks[idx])
    return results


_CHAPTER_QUERY_PATTERNS = [
    r'\b(list|show|give|tell|what).*(chapter|topic|content|index|table of contents)',
    r'\b(chapter|topic).*(list|all|name|title|cover)',
    r'\bhow many chapters\b',
    r'\btable of contents\b',
]


def _is_chapter_query(query: str) -> bool:
    q = query.lower()
    return any(re.search(p, q) for p in _CHAPTER_QUERY_PATTERNS)


def _format_chapter_list(structure: dict) -> str:
    if not structure or "chapters" not in structure:
        return ""
    chapters = structure["chapters"]
    total = len(chapters)
    lines = [f"This book has {total} chapters.\n"]
    for ch in chapters:
        num = ch.get("chapter_number", "")
        title = ch.get("chapter_title", "")
        lines.append(f"{num}. {title}")
    return "\n".join(lines)


BOOK_CHAT_SYSTEM_PROMPT = """You are an expert UPSC study assistant. Answer using ONLY the provided book context.

FORMATTING RULES (very strict, follow exactly):
- NEVER use asterisks (*), hash symbols (#), curly braces, or any markdown.
- For emphasis, wrap key terms in <b> and </b> tags. Example: <b>Fundamental Rights</b>
- For italic, use <i> and </i> tags.
- EVERY numbered point MUST be on its own separate line. Never put two numbered items on the same line.
- Use numbered format: 1. 2. 3. etc. Each on a NEW LINE.
- For sub-points, use a. b. c. each on a NEW LINE indented.
- For headings, write in UPPERCASE on its own line.
- Keep paragraphs short (2-3 sentences max).
- Separate sections with a blank line.

CONTENT RULES:
- If not in context, say: This is not covered in the provided sections of this book.
- Be CONCISE: 150-200 words max unless user asks for detail.
- For key notes: 5-8 numbered points, each on its own line.
- For summaries: 3-5 sentences.
- For questions: direct answer first, then 1-2 supporting points.

BOOK CONTEXT:
{context}

QUESTION: {query}

ANSWER:"""


def chat_with_book(book_id: str, query: str, book_title: str = "") -> str:
    """RAG pipeline: retrieve relevant chunks → build prompt → call Gemini."""
    from llm.gemini_client import call_gemini

    if _is_chapter_query(query):
        from books.book_structure import get_book_structure
        structure = get_book_structure(book_id)
        if structure:
            return _format_chapter_list(structure)

    chunks = _retrieve_chunks(book_id, query)

    if not chunks:
        return "This book hasn't been indexed yet. Please wait for indexing to complete."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Passage {i}]\n{chunk}")
    context = "\n\n".join(context_parts)

    prompt = BOOK_CHAT_SYSTEM_PROMPT.format(context=context, query=query)

    response = call_gemini(prompt)
    return response if response else "I couldn't generate a response. Please try rephrasing."
