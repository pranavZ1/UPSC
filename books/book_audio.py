# books/book_audio.py — Generate audio explanations (MongoDB + GridFS)

import json
import os
import requests
from dotenv import load_dotenv

from db import audio_col, get_gridfs

load_dotenv()

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ELEVENLABS_MODEL = "eleven_multilingual_v2"


def _tts_generate_mp3(script_text: str) -> bytes | None:
    """Call ElevenLabs TTS API and return MP3 bytes (or None)."""
    if not ELEVENLABS_API_KEY:
        print("[audio] ELEVENLABS_API_KEY not set — skipping TTS")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    payload = {
        "text": script_text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.5, "similarity_boost": 0.75,
            "style": 0.4, "use_speaker_boost": True,
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            print(f"[audio] MP3 generated ({len(resp.content)//1024} KB)")
            return resp.content
        else:
            print(f"[audio] ElevenLabs error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[audio] TTS request failed: {e}")
        return None


def _audio_doc_id(book_id: str, chapter_idx: int, topic_idx: int) -> str:
    return f"{book_id}_ch{chapter_idx}_t{topic_idx}"


def _chapter_audio_doc_id(book_id: str, chapter_idx: int) -> str:
    return f"{book_id}_chapter_{chapter_idx}"


def get_cached_script(book_id: str, chapter_idx: int, topic_idx: int) -> dict | None:
    """Load cached audio script from MongoDB."""
    doc = audio_col().find_one({"_id": _audio_doc_id(book_id, chapter_idx, topic_idx)})
    if not doc:
        return None
    doc.pop("_id", None)
    doc.pop("book_id", None)
    # Build audio URL if MP3 exists in GridFS
    if doc.get("mp3_file_id"):
        doc["audio_url"] = f"/notebook/{book_id}/audio-file/ch{chapter_idx}_t{topic_idx}.mp3"
    return doc


def get_cached_chapter_script(book_id: str, chapter_idx: int) -> dict | None:
    """Load cached chapter audio script from MongoDB."""
    doc = audio_col().find_one({"_id": _chapter_audio_doc_id(book_id, chapter_idx)})
    if not doc:
        return None
    doc.pop("_id", None)
    doc.pop("book_id", None)
    if doc.get("mp3_file_id"):
        doc["audio_url"] = f"/notebook/{book_id}/audio-file/chapter_{chapter_idx}.mp3"
    return doc


def generate_audio_script(
    book_id: str, chapter_idx: int, topic_idx: int,
    topic_title: str, chapter_title: str, book_title: str = "",
) -> dict:
    """Generate podcast-style audio script for a topic using RAG context."""
    from books.book_chat import _retrieve_chunks
    from llm.gemini_client import call_gemini

    query = f"{chapter_title}: {topic_title}"
    chunks = _retrieve_chunks(book_id, query, top_k=5)
    context = "\n\n".join(chunks) if chunks else "No specific content found."

    prompt = f"""Create a clear, engaging audio lecture script for a UPSC student studying this topic.

TOPIC: {topic_title}
CHAPTER: {chapter_title}
BOOK: {book_title}

CONTEXT FROM BOOK:
{context}

RULES:
1. Write as an ENTHUSIASTIC, passionate teacher. Be warm, motivating, and engaging.
2. Start with an energetic hook.
3. Cover all key concepts, facts, dates, articles, and important details from the context.
4. Use energetic transitions and rhetorical questions to keep the listener engaged.
5. End with a motivating recap.
6. Aim for 2-4 minutes of reading time (~400-700 words).
7. Write ONLY flowing prose suitable for reading aloud. No markdown, no headers, no bullets.
8. SKIP references to figures, images, diagrams, tables, page numbers, footnotes.
9. Spell out abbreviations on first use.
10. NEVER use asterisks or stars in the text.

AUDIO SCRIPT:"""

    script = call_gemini(prompt)

    word_count = len(script.split())
    minutes = round(word_count / 150, 1)
    duration = f"{int(minutes)}:{int((minutes % 1) * 60):02d}"

    result = {
        "title": topic_title,
        "chapter": chapter_title,
        "script": script.strip(),
        "word_count": word_count,
        "duration_estimate": duration,
    }

    # Generate MP3
    mp3_bytes = _tts_generate_mp3(script.strip())
    mp3_file_id = None
    if mp3_bytes:
        fs = get_gridfs()
        mp3_file_id = fs.put(
            mp3_bytes,
            filename=f"{book_id}_ch{chapter_idx}_t{topic_idx}.mp3",
            metadata={"book_id": book_id, "type": "audio",
                      "chapter_idx": chapter_idx, "topic_idx": topic_idx},
        )
        result["audio_url"] = f"/notebook/{book_id}/audio-file/ch{chapter_idx}_t{topic_idx}.mp3"

    # Store in MongoDB
    doc_id = _audio_doc_id(book_id, chapter_idx, topic_idx)
    audio_col().replace_one(
        {"_id": doc_id},
        {"_id": doc_id, "book_id": book_id, "chapter_idx": chapter_idx,
         "topic_idx": topic_idx, "mp3_file_id": mp3_file_id, **result},
        upsert=True,
    )

    return result


def generate_chapter_audio_script(
    book_id: str, chapter_idx: int,
    chapter_title: str, topics: list[dict], book_title: str = "",
) -> dict:
    """Generate comprehensive audio script for an ENTIRE chapter."""
    from books.book_chat import _retrieve_chunks
    from llm.gemini_client import call_gemini

    all_chunks = []
    queries = [chapter_title] + [t.get("topic_title", "") for t in topics[:8]]
    for q in queries:
        chunks = _retrieve_chunks(book_id, f"{chapter_title}: {q}", top_k=3)
        for c in chunks:
            if c not in all_chunks:
                all_chunks.append(c)

    context = "\n\n".join(all_chunks[:15]) if all_chunks else "No content found."
    topic_names = ", ".join(t.get("topic_title", "") for t in topics)

    prompt = f"""Create a comprehensive audio lecture script covering an ENTIRE chapter for a UPSC student.

CHAPTER: {chapter_title}
TOPICS IN THIS CHAPTER: {topic_names}
BOOK: {book_title}

CONTEXT FROM BOOK:
{context}

RULES:
1. Write as a PASSIONATE, enthusiastic professor.
2. Start with a strong hook about why this chapter is essential for UPSC.
3. Cover ALL listed topics in a logical flow.
4. Use energetic transitions and rhetorical questions.
5. End with a motivating recap and encouragement.
6. Aim for 5-10 minutes of reading time (~800-1500 words).
7. Write ONLY flowing prose for reading aloud. No markdown etc.
8. SKIP references to figures, images, diagrams, tables, page numbers.
9. Spell out abbreviations on first use.
10. NEVER use asterisks or stars.

AUDIO LECTURE SCRIPT:"""

    script = call_gemini(prompt)

    word_count = len(script.split())
    minutes = round(word_count / 150, 1)
    duration = f"{int(minutes)}:{int((minutes % 1) * 60):02d}"

    result = {
        "title": f"Chapter: {chapter_title}",
        "chapter": chapter_title,
        "script": script.strip(),
        "word_count": word_count,
        "duration_estimate": duration,
    }

    mp3_bytes = _tts_generate_mp3(script.strip())
    mp3_file_id = None
    if mp3_bytes:
        fs = get_gridfs()
        mp3_file_id = fs.put(
            mp3_bytes,
            filename=f"{book_id}_chapter_{chapter_idx}.mp3",
            metadata={"book_id": book_id, "type": "audio_chapter",
                      "chapter_idx": chapter_idx},
        )
        result["audio_url"] = f"/notebook/{book_id}/audio-file/chapter_{chapter_idx}.mp3"

    doc_id = _chapter_audio_doc_id(book_id, chapter_idx)
    audio_col().replace_one(
        {"_id": doc_id},
        {"_id": doc_id, "book_id": book_id, "chapter_idx": chapter_idx,
         "mp3_file_id": mp3_file_id, **result},
        upsert=True,
    )

    return result


def get_audio_mp3_bytes(book_id: str, filename: str) -> bytes | None:
    """Retrieve MP3 bytes from GridFS by filename pattern."""
    fs = get_gridfs()
    gf = fs.find_one({"filename": f"{book_id}_{filename}",
                       "metadata.book_id": book_id})
    if gf:
        return gf.read()
    # Try alternate patterns
    gf = fs.find_one({"metadata.book_id": book_id, "metadata.type": {"$in": ["audio", "audio_chapter"]},
                       "filename": {"$regex": filename.replace(".", r"\.")}})
    if gf:
        return gf.read()
    return None
