# books/book_pipeline.py — Background pipelines for uploaded books
#
# TWO pipelines:
#
# 1. LIGHT pipeline (on upload):
#    Phase 1: Store PDF in GridFS + generate thumbnail
#    Phase 2: Extract text → chunk → embed → FAISS index
#    Phase 3: Extract chapter/topic structure
#    → Done. Book is ready for on-demand generation.
#
# 2. SECTION generator (user-triggered per section):
#    Generates all chapters for ONE section type (mindmaps, infographics,
#    audio, flashcards, quiz, cheatsheet).  Skips already-cached items.
#    Each section runs independently in its own background thread.
#
# Progress tracked in the book document's `pipeline` sub-document.

import threading
import traceback
import io

from books.book_registry import (
    get_book, store_pdf, store_thumbnail,
    update_book, update_pipeline, add_pipeline_phase_done,
)


LIGHT_PHASES = ["upload", "indexing", "structure"]

SECTION_PHASES = [
    "mindmaps", "infographics", "audio",
    "flashcards", "quiz", "cheatsheet",
]

# All recognised phases (light + sections) — used for status display
PIPELINE_PHASES = LIGHT_PHASES + SECTION_PHASES


def _run_light_pipeline(book_id: str, pdf_bytes: bytes, filename: str):
    """Execute the light pipeline: upload → index → structure only."""
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

        total_ch = len(structure["chapters"])
        update_pipeline(book_id, total_chapters=total_ch)
        add_pipeline_phase_done(book_id, "structure")

        # ── Light pipeline done — ready for on-demand / section generation
        update_pipeline(book_id, status="completed", phase="done",
                        phase_progress=100,
                        current_task="Book indexed & structured. Generate sections on demand.")
        print(f"✅ Light pipeline complete for book {book_id} ({total_ch} chapters)")

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


# ═══════════════════════════════════════════════════════════════════════════
# SECTION GENERATOR — generates all chapters for ONE section type
# ═══════════════════════════════════════════════════════════════════════════

# Track running section generators: {(book_id, section): True}
_running_sections: dict[tuple, bool] = {}
_section_lock = threading.Lock()


def _run_section_gen(book_id: str, section: str):
    """Generate all items for a single section type."""
    try:
        update_pipeline(book_id, status="running", phase=section,
                        phase_progress=0, current_task=f"Generating {section}…",
                        error=None)

        from books.book_structure import get_book_structure
        structure = get_book_structure(book_id)
        if not structure or not structure.get("chapters"):
            update_pipeline(book_id, status="error",
                            error="Book structure not found")
            return

        chapters = structure["chapters"]
        total_ch = len(chapters)
        pdf_bytes = get_book(book_id) and get_pdf_bytes_for_section(book_id)

        if section == "mindmaps":
            from books.book_mindmap import generate_mindmap, get_cached_mindmap
            for ci, ch in enumerate(chapters):
                update_pipeline(book_id, current_task=f"Mindmap: {ch['chapter_title']}",
                                phase_progress=_pct(ci, total_ch))
                if get_cached_mindmap(book_id, ci):
                    continue
                try:
                    generate_mindmap(book_id, ci, ch["chapter_title"],
                                     ch.get("topics", []), pdf_bytes=pdf_bytes)
                except Exception as e:
                    print(f"[section-gen] Mindmap ch{ci} failed: {e}")

        elif section == "infographics":
            from books.book_infographic import generate_infographic, get_cached_infographic
            for ci, ch in enumerate(chapters):
                update_pipeline(book_id, current_task=f"Infographic: {ch['chapter_title']}",
                                phase_progress=_pct(ci, total_ch))
                if get_cached_infographic(book_id, ci):
                    continue
                try:
                    generate_infographic(book_id, ci, ch["chapter_title"],
                                         ch.get("topics", []), pdf_bytes=pdf_bytes)
                except Exception as e:
                    print(f"[section-gen] Infographic ch{ci} failed: {e}")

        elif section == "audio":
            from books.book_audio import generate_chapter_audio_script, get_cached_chapter_script
            book_title = structure.get("book_summary", "")
            for ci, ch in enumerate(chapters):
                update_pipeline(book_id, current_task=f"Audio: {ch['chapter_title']}",
                                phase_progress=_pct(ci, total_ch))
                if get_cached_chapter_script(book_id, ci):
                    continue
                try:
                    generate_chapter_audio_script(
                        book_id, ci, ch["chapter_title"],
                        ch.get("topics", []), book_title=book_title,
                    )
                except Exception as e:
                    print(f"[section-gen] Audio ch{ci} failed: {e}")

        elif section == "flashcards":
            from books.book_flashcards import generate_flashcards, get_cached_cards
            total_topics = sum(len(ch.get("topics", [])) for ch in chapters)
            done = 0
            for ci, ch in enumerate(chapters):
                for ti, topic in enumerate(ch.get("topics", [])):
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
                        print(f"[section-gen] Flashcards ch{ci}/t{ti} failed: {e}")
                    done += 1

        elif section == "quiz":
            from books.book_quiz import generate_quiz_dump_all_difficulties, get_full_dump
            for ci, ch in enumerate(chapters):
                update_pipeline(book_id, current_task=f"Quiz: {ch['chapter_title']}",
                                phase_progress=_pct(ci, total_ch))
                if get_full_dump(book_id, ci, "medium"):
                    continue
                try:
                    generate_quiz_dump_all_difficulties(
                        book_id, ci, ch["chapter_title"], ch.get("topics", []),
                    )
                except Exception as e:
                    print(f"[section-gen] Quiz ch{ci} failed: {e}")

        elif section == "cheatsheet":
            from books.book_cheatsheet import generate_cheatsheet, get_cached_cheatsheet
            from books.book_flashcards import generate_super_cards, get_cached_super_cards
            if not get_cached_cheatsheet(book_id):
                try:
                    generate_cheatsheet(book_id, structure)
                except Exception as e:
                    print(f"[section-gen] Cheatsheet failed: {e}")
            update_pipeline(book_id, current_task="Super flash cards…",
                            phase_progress=50)
            if not get_cached_super_cards(book_id):
                try:
                    generate_super_cards(book_id, structure)
                except Exception as e:
                    print(f"[section-gen] Super cards failed: {e}")

        # Mark this section phase done
        add_pipeline_phase_done(book_id, section)
        update_pipeline(book_id, status="completed", phase="done",
                        phase_progress=100,
                        current_task=f"{section.title()} generated!")
        print(f"✅ Section '{section}' complete for book {book_id}")

    except Exception as e:
        traceback.print_exc()
        update_pipeline(book_id, status="error", error=str(e))
    finally:
        with _section_lock:
            _running_sections.pop((book_id, section), None)


def get_pdf_bytes_for_section(book_id: str) -> bytes | None:
    """Helper to fetch PDF bytes from GridFS for section generators."""
    from books.book_registry import get_pdf_bytes
    return get_pdf_bytes(book_id)


def start_pipeline(book_id: str, pdf_bytes: bytes, filename: str):
    """Launch the LIGHT pipeline (upload → index → structure) in a background thread."""
    t = threading.Thread(
        target=_run_light_pipeline,
        args=(book_id, pdf_bytes, filename),
        daemon=True,
        name=f"pipeline-{book_id}",
    )
    t.start()
    return t


def start_section_gen(book_id: str, section: str) -> bool:
    """Launch a section generator in a background thread.

    Returns True if started, False if already running.
    """
    if section not in SECTION_PHASES:
        return False
    key = (book_id, section)
    with _section_lock:
        if _running_sections.get(key):
            return False
        _running_sections[key] = True
    t = threading.Thread(
        target=_run_section_gen,
        args=(book_id, section),
        daemon=True,
        name=f"section-{book_id}-{section}",
    )
    t.start()
    return True


def is_section_running(book_id: str, section: str) -> bool:
    """Check if a section generator is currently running."""
    with _section_lock:
        return _running_sections.get((book_id, section), False)


def get_section_completeness(book_id: str) -> dict:
    """Return per-section completion status: {section: {total, done, complete}}.

    Uses fast count_documents queries instead of fetching full documents.
    """
    from books.book_structure import get_book_structure
    structure = get_book_structure(book_id)
    if not structure or not structure.get("chapters"):
        return {}

    chapters = structure["chapters"]
    total_ch = len(chapters)
    result = {}

    import re
    from db import (mindmaps_col, infographics_col, audio_col,
                    flashcards_col, quiz_dumps_col, cheatsheets_col)

    # Mindmaps — _id like {book_id}_ch{n}
    mm_done = mindmaps_col().count_documents(
        {"_id": {"$regex": f"^{re.escape(book_id)}_ch\\d+$"}})
    result["mindmaps"] = {"total": total_ch, "done": mm_done, "complete": mm_done >= total_ch}

    # Infographics — _id like {book_id}_ch{n}
    ig_done = infographics_col().count_documents(
        {"_id": {"$regex": f"^{re.escape(book_id)}_ch\\d+$"}})
    result["infographics"] = {"total": total_ch, "done": ig_done, "complete": ig_done >= total_ch}

    # Audio — _id like {book_id}_chapter_{n}
    au_done = audio_col().count_documents(
        {"_id": {"$regex": f"^{re.escape(book_id)}_chapter_\\d+$"}})
    result["audio"] = {"total": total_ch, "done": au_done, "complete": au_done >= total_ch}

    # Flashcards — _id like {book_id}_ch{n}_t{m}
    fc_total = sum(len(ch.get("topics", [])) for ch in chapters)
    fc_done = flashcards_col().count_documents(
        {"_id": {"$regex": f"^{re.escape(book_id)}_ch\\d+_t\\d+$"}})
    result["flashcards"] = {"total": fc_total, "done": fc_done, "complete": fc_done >= fc_total}

    # Quiz — _id like {book_id}_ch{n}_medium (check medium difficulty as proxy)
    qz_done = quiz_dumps_col().count_documents(
        {"_id": {"$regex": f"^{re.escape(book_id)}_ch\\d+_medium$"}})
    result["quiz"] = {"total": total_ch, "done": qz_done, "complete": qz_done >= total_ch}

    # Cheatsheet — _id = {book_id}
    cs = cheatsheets_col().count_documents({"_id": book_id})
    result["cheatsheet"] = {"total": 1, "done": cs, "complete": cs >= 1}

    return result


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
