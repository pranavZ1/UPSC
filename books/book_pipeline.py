# books/book_pipeline.py — Background pre-generation pipeline for uploaded books
#
# When a book is uploaded, this pipeline runs in a background thread:
#   Phase 1: Store PDF in GridFS + generate thumbnail
#   Phase 2: Extract text → chunk → embed → FAISS index
#   Phase 3: Extract chapter/topic structure
#   Phase 4: Generate mindmaps per chapter
#   Phase 5: Generate infographics per chapter
#   Phase 6: Generate audio per chapter  (chapter-level only, topic-level on demand)
#   Phase 7: Generate flashcards per chapter × topic
#   Phase 8: Generate quiz dumps per chapter (easy, medium, hard)
#   Phase 9: Generate cheat sheet + super flash cards
#
# Progress tracked in the book document's `pipeline` sub-document.

import threading
import traceback
import io

from books.book_registry import (
    get_book, store_pdf, store_thumbnail,
    update_book, update_pipeline, add_pipeline_phase_done,
)


PIPELINE_PHASES = [
    "upload",       # 1: Store PDF + thumbnail
    "indexing",     # 2: Text extraction → FAISS
    "structure",    # 3: Structure extraction
    "mindmaps",    # 4: Mindmap per chapter
    "infographics", # 5: Infographic per chapter
    "audio",       # 6: Audio per chapter
    "flashcards",  # 7: Flash cards per chapter × topic
    "quiz",        # 8: Quiz dump per chapter (all difficulties)
    "cheatsheet",  # 9: Cheat sheet + super cards
]


def _run_pipeline(book_id: str, pdf_bytes: bytes, filename: str):
    """Execute the full pre-generation pipeline."""
    try:
        update_pipeline(book_id, status="running", error=None)

        # ── Phase 1: Upload ──────────────────────────────────────────────
        _set_phase(book_id, "upload", "Storing PDF…")
        store_pdf(book_id, pdf_bytes, filename)

        # Generate thumbnail from first page
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=120)
            thumb_bytes = pix.tobytes("jpeg")
            doc.close()
            store_thumbnail(book_id, thumb_bytes)
            update_book(book_id, page_count=len(fitz.open(stream=pdf_bytes, filetype="pdf")),
                        size_kb=len(pdf_bytes) // 1024)
        except Exception as e:
            print(f"[pipeline] Thumbnail generation failed: {e}")

        add_pipeline_phase_done(book_id, "upload")

        # ── Phase 2: Indexing ────────────────────────────────────────────
        _set_phase(book_id, "indexing", "Extracting text & building FAISS index…")
        from books.book_indexer import index_book
        index_book(book_id, pdf_bytes)
        update_book(book_id, indexed=True, indexing=False)
        add_pipeline_phase_done(book_id, "indexing")

        # ── Phase 3: Structure ───────────────────────────────────────────
        _set_phase(book_id, "structure", "Extracting chapter structure…")
        from books.book_structure import extract_structure, get_book_structure
        extract_structure(book_id, pdf_bytes)
        structure = get_book_structure(book_id)

        if not structure or not structure.get("chapters"):
            update_pipeline(book_id, status="error",
                            error="Failed to extract book structure")
            return

        chapters = structure["chapters"]
        total_ch = len(chapters)
        update_pipeline(book_id, total_chapters=total_ch)
        add_pipeline_phase_done(book_id, "structure")

        # ── Phase 4: Mindmaps ────────────────────────────────────────────
        _set_phase(book_id, "mindmaps", "Generating mindmaps…")
        from books.book_mindmap import generate_mindmap, get_cached_mindmap
        for ci, ch in enumerate(chapters):
            update_pipeline(
                book_id, current_task=f"Mindmap: {ch['chapter_title']}",
                phase_progress=_pct(ci, total_ch),
            )
            if get_cached_mindmap(book_id, ci):
                continue
            try:
                generate_mindmap(book_id, ci, ch["chapter_title"],
                                 ch.get("topics", []), pdf_bytes=pdf_bytes)
            except Exception as e:
                print(f"[pipeline] Mindmap ch{ci} failed: {e}")
        add_pipeline_phase_done(book_id, "mindmaps")

        # ── Phase 5: Infographics ────────────────────────────────────────
        _set_phase(book_id, "infographics", "Generating infographics…")
        from books.book_infographic import generate_infographic, get_cached_infographic
        for ci, ch in enumerate(chapters):
            update_pipeline(
                book_id, current_task=f"Infographic: {ch['chapter_title']}",
                phase_progress=_pct(ci, total_ch),
            )
            if get_cached_infographic(book_id, ci):
                continue
            try:
                generate_infographic(book_id, ci, ch["chapter_title"],
                                     ch.get("topics", []), pdf_bytes=pdf_bytes)
            except Exception as e:
                print(f"[pipeline] Infographic ch{ci} failed: {e}")
        add_pipeline_phase_done(book_id, "infographics")

        # ── Phase 6: Audio (chapter-level) ───────────────────────────────
        _set_phase(book_id, "audio", "Generating audio lectures…")
        from books.book_audio import generate_chapter_audio_script, get_cached_chapter_script
        book_title = structure.get("book_summary", "")
        for ci, ch in enumerate(chapters):
            update_pipeline(
                book_id, current_task=f"Audio: {ch['chapter_title']}",
                phase_progress=_pct(ci, total_ch),
            )
            if get_cached_chapter_script(book_id, ci):
                continue
            try:
                generate_chapter_audio_script(
                    book_id, ci, ch["chapter_title"],
                    ch.get("topics", []), book_title=book_title,
                )
            except Exception as e:
                print(f"[pipeline] Audio ch{ci} failed: {e}")
        add_pipeline_phase_done(book_id, "audio")

        # ── Phase 7: Flash cards (per chapter × topic) ───────────────────
        _set_phase(book_id, "flashcards", "Generating flash cards…")
        from books.book_flashcards import generate_flashcards, get_cached_cards
        total_topics = sum(len(ch.get("topics", [])) for ch in chapters)
        done = 0
        for ci, ch in enumerate(chapters):
            topics = ch.get("topics", [])
            for ti, topic in enumerate(topics):
                update_pipeline(
                    book_id,
                    current_task=f"Flashcards: {ch['chapter_title']} — {topic['topic_title']}",
                    phase_progress=_pct(done, total_topics),
                )
                if get_cached_cards(book_id, ci, ti):
                    done += 1
                    continue
                try:
                    generate_flashcards(book_id, ci, ti,
                                        topic["topic_title"], ch["chapter_title"])
                except Exception as e:
                    print(f"[pipeline] Flashcards ch{ci}/t{ti} failed: {e}")
                done += 1
        add_pipeline_phase_done(book_id, "flashcards")

        # ── Phase 8: Quiz dumps (per chapter, all difficulties) ──────────
        _set_phase(book_id, "quiz", "Generating quiz question dumps…")
        from books.book_quiz import generate_quiz_dump_all_difficulties, get_full_dump
        for ci, ch in enumerate(chapters):
            update_pipeline(
                book_id, current_task=f"Quiz dump: {ch['chapter_title']}",
                phase_progress=_pct(ci, total_ch),
            )
            # Skip if any difficulty already done for this chapter
            if get_full_dump(book_id, ci, "medium"):
                continue
            try:
                generate_quiz_dump_all_difficulties(
                    book_id, ci, ch["chapter_title"], ch.get("topics", []),
                )
            except Exception as e:
                print(f"[pipeline] Quiz ch{ci} failed: {e}")
        add_pipeline_phase_done(book_id, "quiz")

        # ── Phase 9: Cheat sheet + Super cards ───────────────────────────
        _set_phase(book_id, "cheatsheet", "Generating cheat sheet & super cards…")
        from books.book_cheatsheet import generate_cheatsheet, get_cached_cheatsheet
        from books.book_flashcards import generate_super_cards, get_cached_super_cards

        if not get_cached_cheatsheet(book_id):
            try:
                generate_cheatsheet(book_id, structure)
            except Exception as e:
                print(f"[pipeline] Cheatsheet failed: {e}")

        update_pipeline(book_id, current_task="Generating super flash cards…",
                        phase_progress=50)

        if not get_cached_super_cards(book_id):
            try:
                generate_super_cards(book_id, structure)
            except Exception as e:
                print(f"[pipeline] Super cards failed: {e}")

        add_pipeline_phase_done(book_id, "cheatsheet")

        # ── All done ─────────────────────────────────────────────────────
        update_pipeline(book_id, status="completed", phase="done",
                        phase_progress=100, current_task="All assets generated!")
        print(f"✅ Pipeline complete for book {book_id}")

    except Exception as e:
        traceback.print_exc()
        update_pipeline(book_id, status="error", error=str(e))


def _set_phase(book_id: str, phase: str, task: str):
    """Set the current pipeline phase."""
    update_pipeline(book_id, phase=phase, phase_progress=0, current_task=task)
    print(f"📦 Pipeline [{book_id}] — Phase: {phase}")


def _pct(done: int, total: int) -> int:
    """Calculate percentage."""
    if total <= 0:
        return 0
    return min(100, int((done / total) * 100))


def start_pipeline(book_id: str, pdf_bytes: bytes, filename: str):
    """Launch the pipeline in a background thread."""
    t = threading.Thread(
        target=_run_pipeline,
        args=(book_id, pdf_bytes, filename),
        daemon=True,
        name=f"pipeline-{book_id}",
    )
    t.start()
    return t


def get_pipeline_status(book_id: str) -> dict | None:
    """Get current pipeline status for the book."""
    book = get_book(book_id)
    if not book:
        return None
    pipeline = book.get("pipeline", {})
    return {
        "status": pipeline.get("status", "pending"),
        "phase": pipeline.get("phase", ""),
        "phase_progress": pipeline.get("phase_progress", 0),
        "phases_done": pipeline.get("phases_done", []),
        "total_chapters": pipeline.get("total_chapters", 0),
        "current_task": pipeline.get("current_task", ""),
        "error": pipeline.get("error"),
        "all_phases": PIPELINE_PHASES,
    }
