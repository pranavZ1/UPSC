# app.py — Flask web dashboard for UPSC Prelims & Mains Engine
#
# Features:
#   - File upload (drag & drop) + text paste input
#   - Article tracking with Gemini-generated titles + topic badges
#   - Uploaded / Processed tabs with cascading delete
#   - Prelims: Raw Content, Content, Summary, Questions pages
#   - Mains:   Raw Content, Study Notes, Summaries, Q&A pages
#   - Toggle between Prelims / Mains views
#   - PDF viewer with download
#   - Real-time pipeline status polling

import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort, Response,
)
from werkzeug.utils import secure_filename

from config import (
    BASE_DIR, INPUT_DIR,
    TOPIC_FILE_MAP, MAINS_TOPIC_FILE_MAP, MAINS_PAPER_MAP,
)
from utils.article_registry import (
    register_article, update_status, get_all_articles,
    get_articles_by_status, delete_article, get_article,
)
from utils.file_manager import (
    remove_article_content, list_article_pdfs, get_article_pdf_bytes, count_article_pdfs,
)
from books.book_registry import (
    register_book, get_book, get_all_books, get_books_by_category,
    update_book, delete_book, get_pdf_bytes, get_thumbnail_bytes,
)
from books.book_indexer import index_book
from books.book_chat import chat_with_book
from books.book_structure import get_book_structure, extract_structure
from books.book_audio import generate_audio_script, get_cached_script, get_audio_mp3_bytes
from books.book_mindmap import generate_mindmap, get_cached_mindmap
from books.book_infographic import generate_infographic, get_cached_infographic
from books.book_flashcards import generate_flashcards, get_cached_cards, generate_super_cards, get_cached_super_cards
from books.book_quiz import generate_quiz, get_cached_quiz
from books.book_cheatsheet import generate_cheatsheet, get_cached_cheatsheet
from books.book_pipeline import start_pipeline, get_pipeline_status
from evaluate.answer_evaluator import (
    evaluate_text, evaluate_file_bytes, save_evaluation, save_eval_upload,
    load_evaluation, get_recent_evaluations,
)
from news.fetcher import fetch_all_news
from news.analyzer import analyze_article, deep_dive_article
from pyq.data_loader import get_master_data, get_classify_status, PYQ_TOPICS, YEARS as PYQ_YEARS
from pyq.explainer import get_explanation as pyq_get_explanation

# ═══════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.secret_key = "upsc-prelims-engine-2026"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

# ─── Prelims topic badge colors ──────────────────────────────────────────
TOPIC_COLORS = {
    "current_affairs":      "#e53935",
    "history":              "#8e24aa",
    "geography":            "#43a047",
    "polity_governance":    "#1e88e5",
    "economy":              "#fb8c00",
    "science_technology":   "#00acc1",
    "environment_ecology":  "#2e7d32",
    "art_culture":          "#d81b60",
}

TOPIC_DISPLAY_NAMES = {
    "current_affairs":      "Current Affairs",
    "history":              "History",
    "geography":            "Geography",
    "polity_governance":    "Polity & Governance",
    "economy":              "Economy",
    "science_technology":   "Science & Technology",
    "environment_ecology":  "Environment & Ecology",
    "art_culture":          "Art & Culture",
}

# ─── Mains topic badge colors ────────────────────────────────────────────
MAINS_TOPIC_COLORS = {
    # GS1
    "gs1_art_culture":           "#d81b60",
    "gs1_history":               "#8e24aa",
    "gs1_society":               "#5c6bc0",
    "gs1_geography":             "#43a047",
    # GS2
    "gs2_polity":                "#1e88e5",
    "gs2_governance":            "#0097a7",
    "gs2_social_justice":        "#7b1fa2",
    "gs2_international_relations":"#2e7d32",
    # GS3
    "gs3_economy":               "#fb8c00",
    "gs3_agriculture":           "#558b2f",
    "gs3_science_technology":    "#00acc1",
    "gs3_environment":           "#388e3c",
    "gs3_internal_security":     "#c62828",
    "gs3_disaster_management":   "#d84315",
    # GS4
    "gs4_ethics":                "#6a1b9a",
}

MAINS_TOPIC_DISPLAY_NAMES = {
    "gs1_art_culture":            "Indian Art & Culture",
    "gs1_history":                "History",
    "gs1_society":                "Indian Society",
    "gs1_geography":              "Geography",
    "gs2_polity":                 "Constitution & Polity",
    "gs2_governance":             "Governance",
    "gs2_social_justice":         "Social Justice",
    "gs2_international_relations":"International Relations",
    "gs3_economy":                "Economy",
    "gs3_agriculture":            "Agriculture",
    "gs3_science_technology":     "Science & Technology",
    "gs3_environment":            "Environment",
    "gs3_internal_security":      "Internal Security",
    "gs3_disaster_management":    "Disaster Management",
    "gs4_ethics":                 "Ethics",
}

# Combined colors for badge rendering (prelims + mains stems)
ALL_TOPIC_COLORS = {**TOPIC_COLORS, **MAINS_TOPIC_COLORS}
ALL_TOPIC_DISPLAY = {**TOPIC_DISPLAY_NAMES, **MAINS_TOPIC_DISPLAY_NAMES}


# ─── Pipeline job tracking ────────────────────────────────────────────────

pipeline_status = {
    "running": False,
    "filename": "",
    "article_id": "",
    "started_at": "",
    "logs": [],
    "progress": 0,
    "error": None,
}


# ─── Helpers ──────────────────────────────────────────────────────────────

def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _get_pdf_list(exam_category: str, display_names: dict = None) -> list[dict]:
    """Return article PDFs from GridFS with display metadata."""
    if display_names is None:
        display_names = TOPIC_DISPLAY_NAMES
    raw = list_article_pdfs(exam_category)
    pdfs = []
    for entry in raw:
        stem = entry["file_stem"]
        # Strip mains_ prefix from stem for display lookup
        lookup_stem = stem
        display_name = display_names.get(lookup_stem, lookup_stem.replace("_", " ").title())
        paper = MAINS_PAPER_MAP.get(lookup_stem, "")
        pdfs.append({
            "filename": entry["filename"],
            "display_name": display_name,
            "stem": stem,
            "paper": paper,
            "size_kb": entry["size_kb"],
            "modified": entry["modified"],
        })
    return pdfs


def _count_all_pdfs() -> dict:
    """Count article PDFs per category from GridFS."""
    return count_article_pdfs()


def _run_pipeline_thread(file_path: str, article_id: str = None):
    """Run pipeline in background thread with status capture."""
    global pipeline_status
    pipeline_status["running"] = True
    pipeline_status["error"] = None
    pipeline_status["logs"] = []
    pipeline_status["progress"] = 0

    try:
        import io
        import sys

        class LogCapture(io.StringIO):
            def write(self, msg):
                if msg.strip():
                    pipeline_status["logs"].append(msg.strip())
                    text = msg.strip().lower()
                    if "compression done" in text:
                        pipeline_status["progress"] = 20
                    elif "topic chunks" in text:
                        pipeline_status["progress"] = 30
                    elif "chunk" in text and "complete" in text:
                        pipeline_status["progress"] = min(
                            95, pipeline_status["progress"] + 10
                        )
                    elif "all done" in text:
                        pipeline_status["progress"] = 100
                return super().write(msg)

            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = LogCapture()

        from pipeline import run_pipeline
        run_pipeline(file_path, article_id=article_id)

        sys.stdout = old_stdout
        pipeline_status["progress"] = 100

    except Exception as e:
        pipeline_status["error"] = str(e)
        pipeline_status["logs"].append(f"ERROR: {e}")
        if article_id:
            update_status(article_id, "error", str(e))
    finally:
        pipeline_status["running"] = False


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    counts = _count_all_pdfs()
    prelims_total = counts["raw_content"] + counts["content"] + counts["summary"] + counts["questions"]
    mains_total = counts["mains_raw_content"] + counts["mains_content"] + counts["mains_summary"] + counts["mains_questions"]
    total_pdfs = prelims_total + mains_total
    articles_by_status = get_articles_by_status()
    all_articles = get_all_articles()

    return render_template(
        "dashboard.html",
        counts=counts,
        total_pdfs=total_pdfs,
        prelims_total=prelims_total,
        mains_total=mains_total,
        articles_by_status=articles_by_status,
        all_articles=all_articles,
        status=pipeline_status,
        topic_colors=ALL_TOPIC_COLORS,
        topic_display=ALL_TOPIC_DISPLAY,
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload."""
    if "file" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("dashboard"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("dashboard"))

    if not _allowed_file(file.filename):
        flash(
            f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            "error",
        )
        return redirect(url_for("dashboard"))

    filename = secure_filename(file.filename)
    save_path = INPUT_DIR / filename
    file.save(str(save_path))

    # Register in article registry
    article_id = register_article(filename, file_type="upload")
    flash(f"File '{filename}' uploaded successfully!", "success")

    # Auto-start pipeline if requested
    if request.form.get("auto_process") == "on":
        if pipeline_status["running"]:
            flash("Pipeline is already running. Please wait.", "warning")
        else:
            _start_pipeline(filename, str(save_path), article_id)

    return redirect(url_for("dashboard"))


@app.route("/paste", methods=["POST"])
def paste_text():
    """Handle text paste input."""
    text = request.form.get("paste_text", "").strip()
    if not text:
        flash("No text provided", "error")
        return redirect(url_for("dashboard"))

    # Save as .txt file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pasted_{timestamp}.txt"
    save_path = INPUT_DIR / filename
    save_path.write_text(text, encoding="utf-8")

    # Register
    article_id = register_article(filename, file_type="paste")
    flash("Text saved and ready for processing!", "success")

    # Auto-start pipeline if requested
    if request.form.get("auto_process_paste") == "on":
        if pipeline_status["running"]:
            flash("Pipeline is already running. Please wait.", "warning")
        else:
            _start_pipeline(filename, str(save_path), article_id)

    return redirect(url_for("dashboard"))


def _start_pipeline(filename: str, file_path: str, article_id: str):
    """Start pipeline in a background thread."""
    pipeline_status["filename"] = filename
    pipeline_status["article_id"] = article_id
    pipeline_status["started_at"] = datetime.now().strftime("%I:%M %p")
    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(file_path, article_id),
    )
    thread.daemon = True
    thread.start()


@app.route("/process/<article_id>")
def process_article(article_id):
    """Manually trigger pipeline for an already-uploaded article."""
    article = get_article(article_id)
    if not article:
        flash("Article not found", "error")
        return redirect(url_for("dashboard"))

    file_path = INPUT_DIR / article["filename"]
    if not file_path.exists():
        flash(f"File '{article['filename']}' not found on disk", "error")
        return redirect(url_for("dashboard"))

    if pipeline_status["running"]:
        flash("Pipeline is already running. Please wait.", "warning")
        return redirect(url_for("dashboard"))

    _start_pipeline(article["filename"], str(file_path), article_id)
    flash(f"Pipeline started for '{article['title']}'", "info")
    return redirect(url_for("dashboard"))


@app.route("/status")
def get_status():
    """API endpoint for polling pipeline status."""
    return jsonify(pipeline_status)


# ── PDF pages ─────────────────────────────────────────────────────────────

@app.route("/raw-content")
def raw_content_page():
    pdfs = _get_pdf_list("raw_content")
    return render_template(
        "pdf_list.html",
        page_title="Raw Content",
        page_subtitle="Original extracted text from uploaded materials",
        page_icon="📦",
        category="raw_content",
        pdfs=pdfs,
        colors=TOPIC_COLORS,
    )


@app.route("/content")
def content_page():
    pdfs = _get_pdf_list("content")
    return render_template(
        "pdf_list.html",
        page_title="Study Notes",
        page_subtitle="Detailed content notes organized by topic (Sections A-G)",
        page_icon="📝",
        category="content",
        pdfs=pdfs,
        colors=TOPIC_COLORS,
    )


@app.route("/summary")
def summary_page():
    pdfs = _get_pdf_list("summary")
    return render_template(
        "pdf_list.html",
        page_title="Revision Summaries",
        page_subtitle="Quick revision notes (Sections A-E)",
        page_icon="📋",
        category="summary",
        pdfs=pdfs,
        colors=TOPIC_COLORS,
    )


@app.route("/questions")
def questions_page():
    pdfs = _get_pdf_list("questions")
    return render_template(
        "pdf_list.html",
        page_title="Practice MCQs",
        page_subtitle="UPSC-style questions with answer key & explanations",
        page_icon="❓",
        category="questions",
        pdfs=pdfs,
        colors=TOPIC_COLORS,
    )


# ── Mains PDF pages ──────────────────────────────────────────────────────

@app.route("/mains/raw-content")
def mains_raw_content_page():
    pdfs = _get_pdf_list("mains_raw_content", MAINS_TOPIC_DISPLAY_NAMES)
    return render_template(
        "pdf_list.html",
        page_title="Mains — Raw Content",
        page_subtitle="Original text classified by GS papers",
        page_icon="📦",
        category="mains_raw_content",
        pdfs=pdfs,
        colors=MAINS_TOPIC_COLORS,
        is_mains=True,
    )


@app.route("/mains/content")
def mains_content_page():
    pdfs = _get_pdf_list("mains_content", MAINS_TOPIC_DISPLAY_NAMES)
    return render_template(
        "pdf_list.html",
        page_title="Mains — Study Notes",
        page_subtitle="Multi-dimensional analysis with way forward",
        page_icon="📝",
        category="mains_content",
        pdfs=pdfs,
        colors=MAINS_TOPIC_COLORS,
        is_mains=True,
    )


@app.route("/mains/summary")
def mains_summary_page():
    pdfs = _get_pdf_list("mains_summary", MAINS_TOPIC_DISPLAY_NAMES)
    return render_template(
        "pdf_list.html",
        page_title="Mains — Summaries",
        page_subtitle="Answer-ready revision with key phrases",
        page_icon="📋",
        category="mains_summary",
        pdfs=pdfs,
        colors=MAINS_TOPIC_COLORS,
        is_mains=True,
    )


@app.route("/mains/questions")
def mains_questions_page():
    pdfs = _get_pdf_list("mains_questions", MAINS_TOPIC_DISPLAY_NAMES)
    return render_template(
        "pdf_list.html",
        page_title="Mains — Q&A",
        page_subtitle="Mains-style questions with structured answers",
        page_icon="❓",
        category="mains_questions",
        pdfs=pdfs,
        colors=MAINS_TOPIC_COLORS,
        is_mains=True,
    )


# ── PDF serving & viewer ─────────────────────────────────────────────────

@app.route("/pdf/<category>/<filename>")
def serve_pdf(category, filename):
    """Serve an article PDF from GridFS."""
    valid = {"raw_content", "content", "summary", "questions",
             "mains_raw_content", "mains_content", "mains_summary", "mains_questions"}
    if category not in valid:
        flash("Invalid category", "error")
        return redirect(url_for("dashboard"))
    pdf_bytes = get_article_pdf_bytes(category, filename)
    if not pdf_bytes:
        abort(404)
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": "inline"})


@app.route("/view/<category>/<filename>")
def view_pdf(category, filename):
    """Render PDF viewer page."""
    pdf_url = url_for("serve_pdf", category=category, filename=filename)
    stem = filename.replace(".pdf", "")
    for suffix in ("_raw_content", "_content", "_summary", "_questions"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    is_mains = category.startswith("mains_")
    display_names = MAINS_TOPIC_DISPLAY_NAMES if is_mains else TOPIC_DISPLAY_NAMES
    colors = MAINS_TOPIC_COLORS if is_mains else TOPIC_COLORS
    display_name = display_names.get(stem, stem.replace("_", " ").title())

    # Add GS paper prefix for mains
    paper = MAINS_PAPER_MAP.get(stem, "")
    if paper:
        display_name = f"[{paper}] {display_name}"

    cat_labels = {
        "raw_content": "Raw Content",
        "content": "Study Notes",
        "summary": "Revision Summary",
        "questions": "Practice MCQs",
        "mains_raw_content": "Mains — Raw Content",
        "mains_content": "Mains — Study Notes",
        "mains_summary": "Mains — Summary",
        "mains_questions": "Mains — Q&A",
    }

    # Back link should go to the correct page
    back_endpoints = {
        "raw_content": "raw_content_page",
        "content": "content_page",
        "summary": "summary_page",
        "questions": "questions_page",
        "mains_raw_content": "mains_raw_content_page",
        "mains_content": "mains_content_page",
        "mains_summary": "mains_summary_page",
        "mains_questions": "mains_questions_page",
    }

    return render_template(
        "viewer.html",
        pdf_url=pdf_url,
        filename=filename,
        display_name=display_name,
        category=category,
        category_label=cat_labels.get(category, category),
        color=colors.get(stem, "#546e7a"),
        back_endpoint=back_endpoints.get(category, "dashboard"),
    )


# ── Article management ────────────────────────────────────────────────────

@app.route("/delete-article/<article_id>")
def delete_article_route(article_id):
    """Delete an article: remove from registry + input file + content from topic files."""
    article = delete_article(article_id)
    if article:
        # Delete input file
        input_file = INPUT_DIR / article["filename"]
        if input_file.exists():
            input_file.unlink()

        # Cascade-delete content from MongoDB + regenerate affected PDFs
        # (works for both Prelims AND Mains — queries MongoDB for all blocks)
        results = remove_article_content(article_id)
        cleaned = sum(
            1 for sr in results.values() for r in sr if "cleaned" in r
        )
        deleted = sum(
            1 for sr in results.values() for r in sr if "deleted" in r
        )
        parts = []
        if cleaned:
            parts.append(f"{cleaned} file(s) updated")
        if deleted:
            parts.append(f"{deleted} file(s) removed")
        detail = f" ({', '.join(parts)})" if parts else ""
        flash(f"Deleted: {article['title']}{detail}", "success")
    else:
        flash("Article not found", "error")
    return redirect(url_for("dashboard"))


# ═══════════════════════════════════════════════════════════════════════════
# BOOKS LIBRARY — Unified Library + NotebookLLM
# ═══════════════════════════════════════════════════════════════════════════

BOOK_ALLOWED_EXT = {".pdf"}


@app.route("/books")
def books_page():
    """Unified book library — all books in one grid."""
    all_books = get_all_books()
    return render_template("books.html", books=all_books)


@app.route("/books/upload", methods=["POST"])
def upload_book():
    """Upload a book PDF → store in MongoDB → start background pipeline."""
    if "book_file" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("books_page"))

    file = request.files["book_file"]
    category = "general"

    if file.filename == "" or Path(file.filename).suffix.lower() not in BOOK_ALLOWED_EXT:
        flash("Please upload a valid PDF file.", "error")
        return redirect(url_for("books_page"))

    filename = secure_filename(file.filename)
    pdf_bytes = file.read()
    size_kb = round(len(pdf_bytes) / 1024, 1)
    title = request.form.get("title", "").strip()

    book_id = register_book(filename, category, title)
    update_book(book_id, size_kb=size_kb, indexing=True)

    # Launch full background pipeline (stores PDF, indexes, generates all assets)
    start_pipeline(book_id, pdf_bytes, filename)

    flash(f"Book '{title or filename}' uploaded! Pipeline started — check progress in Notebook.", "success")
    return redirect(url_for("books_page"))


@app.route("/books/<book_id>/reindex", methods=["POST"])
def reindex_book(book_id):
    """Re-index a book that previously failed indexing."""
    book = get_book(book_id)
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("books_page"))

    pdf_bytes = get_pdf_bytes(book_id)
    if not pdf_bytes:
        flash("PDF not found in database", "error")
        return redirect(url_for("books_page"))

    update_book(book_id, indexing=True, error=None, indexed=False)

    # Re-run full pipeline
    start_pipeline(book_id, pdf_bytes, book["filename"])

    flash(f"Re-indexing started for '{book.get('title', book['filename'])}'!", "success")
    return redirect(url_for("books_page"))


@app.route("/books/<book_id>/view")
def book_viewer(book_id):
    """View book PDF with AI chat panel."""
    book = get_book(book_id)
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("books_page"))

    pdf_url = url_for("serve_book_pdf", book_id=book_id)
    return render_template("book_viewer.html", book=book, pdf_url=pdf_url)


@app.route("/books/<book_id>/serve")
def serve_book_pdf(book_id):
    """Serve a book's PDF from MongoDB GridFS."""
    pdf_bytes = get_pdf_bytes(book_id)
    if not pdf_bytes:
        abort(404)
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": "inline"})


@app.route("/books/<book_id>/thumbnail")
def serve_book_thumbnail(book_id):
    """Serve thumbnail from MongoDB GridFS."""
    thumb_bytes = get_thumbnail_bytes(book_id)
    if not thumb_bytes:
        abort(404)
    return Response(thumb_bytes, mimetype="image/jpeg")


@app.route("/books/<book_id>/index", methods=["POST"])
def index_book_route(book_id):
    """Trigger FAISS indexing for a book."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    if book.get("indexing"):
        return jsonify({"status": "already_indexing"})
    if book.get("indexed"):
        return jsonify({"status": "already_indexed"})

    update_book(book_id, indexing=True, error=None)

    def _index_thread():
        try:
            pdf_bytes = get_pdf_bytes(book_id)
            if not pdf_bytes:
                update_book(book_id, indexing=False, error="PDF not found in DB")
                return
            result = index_book(book_id, pdf_bytes)
            update_book(book_id, indexed=True, indexing=False,
                        page_count=result["page_count"], chunk_count=result["chunk_count"])
        except Exception as e:
            update_book(book_id, indexing=False, error=str(e))

    threading.Thread(target=_index_thread, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/books/<book_id>/index-status")
def book_index_status(book_id):
    """Poll indexing status."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({
        "indexed": book.get("indexed", False),
        "indexing": book.get("indexing", False),
        "chunk_count": book.get("chunk_count", 0),
        "page_count": book.get("page_count", 0),
        "error": book.get("error"),
    })


@app.route("/books/<book_id>/chat", methods=["POST"])
def book_chat(book_id):
    """RAG chat endpoint."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    if not book.get("indexed"):
        return jsonify({"error": "Book is not indexed yet."}), 400

    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "No question provided"}), 400

    try:
        answer = chat_with_book(book_id, query, book_title=book.get("title", ""))
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Chat error: {str(e)}"}), 500


@app.route("/books/delete/<book_id>")
def delete_book_route(book_id):
    """Delete a book."""
    book = delete_book(book_id)
    if book:
        flash(f"Deleted: {book.get('title', book.get('filename'))}", "success")
    else:
        flash("Book not found", "error")
    return redirect(url_for("books_page"))


@app.route("/books/<book_id>/pipeline-status")
def book_pipeline_status(book_id):
    """API: Poll the book's background pipeline progress."""
    status = get_pipeline_status(book_id)
    if not status:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(status)


# ═══════════════════════════════════════════════════════════════════════════
# NOTEBOOK LLM — Audio, Mind Maps, Infographics, Flash Cards
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/notebook/<book_id>")
def notebook_page(book_id):
    """Main NotebookLLM page for a book."""
    book = get_book(book_id)
    if not book:
        flash("Book not found", "error")
        return redirect(url_for("books_page"))

    structure = get_book_structure(book_id)
    return render_template("notebook.html", book=book, structure=structure)


@app.route("/notebook/<book_id>/structure")
def notebook_structure(book_id):
    """Get or generate chapter/topic structure (JSON API)."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    structure = get_book_structure(book_id)
    if structure:
        return jsonify(structure)

    if not book.get("indexed"):
        return jsonify({"error": "Book must be indexed first."}), 400

    # Generate structure from PDF bytes in GridFS
    try:
        pdf_bytes = get_pdf_bytes(book_id)
        if not pdf_bytes:
            return jsonify({"error": "PDF not found in database"}), 404
        structure = extract_structure(book_id, pdf_bytes)
        return jsonify(structure)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/audio/<int:chapter_idx>/<int:topic_idx>")
def notebook_audio(book_id, chapter_idx, topic_idx):
    """Generate or return cached audio script for a topic."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    # Check cache
    cached = get_cached_script(book_id, chapter_idx, topic_idx)
    if cached:
        return jsonify(cached)

    # Get topic info from structure
    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]
    topics = chapter.get("topics", [])
    if topic_idx >= len(topics):
        return jsonify({"error": "Topic not found"}), 404

    topic = topics[topic_idx]
    try:
        result = generate_audio_script(
            book_id, chapter_idx, topic_idx,
            topic["topic_title"], chapter["chapter_title"],
            book.get("title", ""),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/audio-chapter/<int:chapter_idx>")
def notebook_audio_chapter(book_id, chapter_idx):
    """Generate or return cached audio script for an entire chapter."""
    from books.book_audio import get_cached_chapter_script, generate_chapter_audio_script

    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_chapter_script(book_id, chapter_idx)
    if cached:
        return jsonify(cached)

    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]
    try:
        result = generate_chapter_audio_script(
            book_id, chapter_idx,
            chapter["chapter_title"], chapter.get("topics", []),
            book.get("title", ""),
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/audio-file/<path:filename>")
def notebook_audio_file(book_id, filename):
    """Serve a generated MP3 audio file from GridFS."""
    mp3_bytes = get_audio_mp3_bytes(book_id, filename)
    if not mp3_bytes:
        abort(404)
    return Response(mp3_bytes, mimetype="audio/mpeg")


@app.route("/notebook/<book_id>/mindmap/<int:chapter_idx>")
def notebook_mindmap(book_id, chapter_idx):
    """Generate or return cached mind map for a chapter."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_mindmap(book_id, chapter_idx)
    if cached:
        return jsonify(cached)

    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]

    # Get PDF bytes from GridFS for chapter text extraction
    pdf_bytes = get_pdf_bytes(book_id)

    try:
        result = generate_mindmap(
            book_id, chapter_idx,
            chapter["chapter_title"], chapter.get("topics", []),
            book_title=book.get("title", ""),
            pdf_bytes=pdf_bytes,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/infographic/<int:chapter_idx>")
def notebook_infographic(book_id, chapter_idx):
    """Generate or return cached infographic for a chapter."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_infographic(book_id, chapter_idx)
    if cached:
        return jsonify(cached)

    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]

    # Get PDF bytes from GridFS for chapter text extraction
    pdf_bytes = get_pdf_bytes(book_id)

    try:
        result = generate_infographic(
            book_id, chapter_idx,
            chapter["chapter_title"], chapter.get("topics", []),
            pdf_bytes=pdf_bytes,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/flashcards/super")
def notebook_super_flashcards(book_id):
    """Generate or return cached super last-min revision cards for entire book."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_super_cards(book_id)
    if cached:
        return jsonify({"cards": cached})

    structure = get_book_structure(book_id)
    if not structure:
        return jsonify({"error": "Book structure not found"}), 404

    try:
        cards = generate_super_cards(book_id, structure)
        return jsonify({"cards": cards})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/flashcards/<int:chapter_idx>/<int:topic_idx>")
def notebook_flashcards(book_id, chapter_idx, topic_idx):
    """Generate or return cached flash cards for a topic."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_cards(book_id, chapter_idx, topic_idx)
    if cached:
        return jsonify({"cards": cached})

    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]
    topics = chapter.get("topics", [])
    if topic_idx >= len(topics):
        return jsonify({"error": "Topic not found"}), 404

    topic = topics[topic_idx]
    try:
        cards = generate_flashcards(
            book_id, chapter_idx, topic_idx,
            topic["topic_title"], chapter["chapter_title"],
        )
        return jsonify({"cards": cards})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/quiz/<int:chapter_idx>/<difficulty>")
def notebook_quiz(book_id, chapter_idx, difficulty):
    """Generate or return cached quiz for a chapter at given difficulty."""
    if difficulty not in ("easy", "medium", "hard"):
        return jsonify({"error": "Invalid difficulty"}), 400

    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_quiz(book_id, chapter_idx, difficulty)
    if cached:
        return jsonify({"questions": cached})

    structure = get_book_structure(book_id)
    if not structure or chapter_idx >= len(structure.get("chapters", [])):
        return jsonify({"error": "Chapter not found"}), 404

    chapter = structure["chapters"][chapter_idx]
    try:
        questions = generate_quiz(
            book_id, chapter_idx,
            chapter["chapter_title"], chapter.get("topics", []),
            difficulty=difficulty,
        )
        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebook/<book_id>/cheatsheet")
def notebook_cheatsheet(book_id):
    """Generate or return cached whole-book cheat sheet."""
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    cached = get_cached_cheatsheet(book_id)
    if cached:
        return jsonify(cached)

    structure = get_book_structure(book_id)
    if not structure:
        return jsonify({"error": "Book structure not found"}), 404

    try:
        result = generate_cheatsheet(book_id, structure)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# ANSWER EVALUATION — AI-powered Mains answer review
# ═══════════════════════════════════════════════════════════════════════════

EVAL_STATUS = {}  # eval_id -> {"status": "processing"/"done"/"error", "error": None}


@app.route("/evaluate")
def evaluate_page():
    """Show the evaluation form."""
    recent = get_recent_evaluations()
    return render_template("evaluate.html", recent_evals=recent)


@app.route("/evaluate/submit", methods=["POST"])
def evaluate_submit():
    """Accept answers and start AI evaluation in background."""
    subject = request.form.get("subject", "GS1")
    question_count = int(request.form.get("question_count", 1))
    max_marks = int(request.form.get("max_marks", 10))
    input_method = request.form.get("input_method", "text")
    answer_text = request.form.get("answer_text", "").strip()

    eval_id = uuid.uuid4().hex[:12]

    # Determine input
    file = request.files.get("answer_file")
    has_file = file and file.filename
    has_text = bool(answer_text)

    if input_method == "file" and not has_file:
        flash("Please upload a file.", "error")
        return redirect(url_for("evaluate_page"))
    if input_method == "text" and not has_text:
        flash("Please paste your answers.", "error")
        return redirect(url_for("evaluate_page"))

    file_bytes = None
    file_ext = None
    use_text = input_method == "text" and has_text

    if not use_text and has_file:
        ext = Path(file.filename).suffix.lower()
        if ext not in (".pdf", ".jpg", ".jpeg", ".png"):
            flash("Please upload PDF, JPG, or PNG files only.", "error")
            return redirect(url_for("evaluate_page"))
        file_bytes = file.read()
        file_ext = ext
        save_eval_upload(eval_id, file_bytes, ext)

    EVAL_STATUS[eval_id] = {"status": "processing", "error": None}

    def _run():
        try:
            if use_text:
                result = evaluate_text(subject, answer_text, question_count, max_marks)
            else:
                result = evaluate_file_bytes(subject, file_bytes, file_ext, question_count, max_marks)
            save_evaluation(eval_id, result, subject, "text" if use_text else "file")
            EVAL_STATUS[eval_id] = {"status": "done"}
        except Exception as e:
            print(f"Evaluation error: {e}")
            EVAL_STATUS[eval_id] = {"status": "error", "error": str(e)}

    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()

    return redirect(url_for("evaluate_processing", eval_id=eval_id))


@app.route("/evaluate/processing/<eval_id>")
def evaluate_processing(eval_id):
    """Show the 'Evaluating...' page with status polling."""
    status = EVAL_STATUS.get(eval_id)
    if not status:
        flash("Evaluation not found.", "error")
        return redirect(url_for("evaluate_page"))
    if status["status"] == "done":
        return redirect(url_for("evaluate_result", eval_id=eval_id))
    return render_template("evaluate_processing.html", eval_id=eval_id)


@app.route("/evaluate/check/<eval_id>")
def evaluate_check(eval_id):
    """API: poll evaluation status."""
    return jsonify(EVAL_STATUS.get(eval_id, {"status": "unknown"}))


@app.route("/evaluate/result/<eval_id>")
def evaluate_result(eval_id):
    """Display the evaluation report."""
    data = load_evaluation(eval_id)
    if not data:
        flash("Evaluation not found.", "error")
        return redirect(url_for("evaluate_page"))

    evaluation = data["evaluation"]
    questions = evaluation.get("questions", [])
    overall = evaluation.get("overall_feedback", {})

    # Normalize data for safe template access
    for q in questions:
        q.setdefault("key_strengths", [])
        q.setdefault("areas_for_improvement", {})
        for sec in ("introduction", "body", "conclusion"):
            q["areas_for_improvement"].setdefault(sec, [])
        q.setdefault("max_marks", 10)
        q.setdefault("score", 0)

    overall.setdefault("competencies", {})
    for key in ("contextual", "content", "language", "introduction", "presentation", "conclusion"):
        overall["competencies"].setdefault(key, {"strengths": [], "improvements": []})

    total = overall.get("total_score", 0)
    max_total = overall.get("max_total_score", 1)
    pct = round(total / max_total * 100) if max_total > 0 else 0

    return render_template(
        "evaluate_result.html",
        eval_data=data,
        questions=questions,
        overall=overall,
        total_score=total,
        max_score=max_total,
        score_pct=pct,
    )


# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# NEWS — Daily current affairs from RSS feeds
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/news")
def news_page():
    """Daily news dashboard."""
    news_data = fetch_all_news()
    return render_template("news.html", news=news_data)


@app.route("/news/refresh")
def news_refresh():
    """Force refresh news from RSS feeds."""
    news_data = fetch_all_news(force_refresh=True)
    return redirect(url_for("news_page"))


@app.route("/news/analyze", methods=["POST"])
def news_analyze():
    """AI-powered article analysis."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    article_id = data.get("article_id", "")
    title = data.get("title", "")
    url = data.get("url", "")
    summary = data.get("summary", "")

    if not url:
        return jsonify({"error": "Article URL is required"}), 400

    try:
        result = analyze_article(article_id, title, url, summary)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/news/deepdive", methods=["POST"])
def news_deepdive():
    """AI-powered deep dive — causes, effects, implications."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    article_id = data.get("article_id", "")
    title = data.get("title", "")
    url = data.get("url", "")
    summary = data.get("summary", "")

    if not url:
        return jsonify({"error": "Article URL is required"}), 400

    try:
        result = deep_dive_article(article_id, title, url, summary)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# PREVIOUS YEAR QUESTIONS — PYQ Study + Quiz
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/pyq")
def pyq_page():
    """Previous Year Questions — Study & Quiz."""
    return render_template("pyq.html", topics=PYQ_TOPICS, years=PYQ_YEARS)


@app.route("/pyq/data")
def pyq_data():
    """Return all classified PYQ data (triggers classification on first call)."""
    data, status = get_master_data()
    if data is not None:
        return jsonify({"status": "ready", "questions": data})
    return jsonify(status)


@app.route("/pyq/classify-status")
def pyq_classify_status():
    """Poll classification progress."""
    return jsonify(get_classify_status())


@app.route("/pyq/explain", methods=["POST"])
def pyq_explain():
    """Generate AI explanation for a PYQ question."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    qid = data.get("question_id", "")
    question = data.get("question", "")
    options = data.get("options", {})
    answer = data.get("answer", "")

    if not all([qid, question, options, answer]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        result = pyq_get_explanation(qid, question, options, answer)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# ASK A BOT — UPSC AI Chat Assistant
# ═══════════════════════════════════════════════════════════════════════════

_UPSC_SYSTEM_PROMPT = """You are an expert UPSC (Union Public Service Commission) AI assistant.
You help students preparing for the UPSC Civil Services Examination — both Prelims and Mains.

Your capabilities:
- Answer factual questions about Indian Polity, Economy, History, Geography, Science & Tech, Environment, Ethics
- Explain concepts clearly with examples relevant to UPSC
- Help with Mains answer structuring (introduction, body, conclusion format)
- Provide preparation strategies, booklists, and time-management tips
- Discuss Current Affairs and their UPSC relevance
- Generate MCQ-style practice questions when asked
- Explain previous year questions and their answers
- Cover all GS papers (GS1-GS4) and Essay paper topics

═══ CONVERSATION STYLE (EXTREMELY IMPORTANT) ═══

1. BE CONCISE & CONVERSATIONAL — like a knowledgeable friend, NOT a textbook.
   • Give a crisp, focused answer covering the core ask in 150-300 words max.
   • Do NOT dump the entire syllabus, all sub-topics, or multi-page explanations in one go.
   • Think: "What's the minimum the student needs right now?" — give that.

2. KEEP THE USER ENGAGED — after every answer, end with a follow-up nudge:
   • "Want me to break down the GS Paper I syllabus topic by topic?" 
   • "Shall I compare Prelims vs Mains strategy for you?"
   • "Would you like me to explain any of these topics in detail?"
   • "Need a quick practice MCQ on this?"
   This makes the conversation interactive and prevents information overload.

3. USE TABLES WHEN COMPARING DATA — whenever there's a comparison (papers, marks,
   features, schemes, articles), format it as a proper markdown table with | pipes.
   Tables are much clearer than paragraphs for structured data.

4. PROGRESSIVE DISCLOSURE — reveal depth in layers:
   • First response: Overview + key highlights + follow-up question
   • If they ask for more: Detailed breakdown of that specific sub-topic
   • If they ask further: Examples, PYQs, mnemonics, practice questions

5. FORMATTING RULES:
   • Use **bold** for key terms, article numbers, scheme names
   • Use bullet points for lists (not giant paragraphs)
   • Use markdown tables (| col1 | col2 |) for comparisons
   • Use numbered lists for steps/sequences
   • Keep paragraphs to 2-3 sentences max

6. PERSONALITY:
   • Warm, encouraging, and practical
   • Use occasional emojis (📝 📋 🎯 ✅) but don't overdo it
   • Relate everything back to "how does this help in the exam"
   • Be accurate and factual — if unsure, say so

Remember: A student who gets overwhelmed with info will leave. A student who stays
curious through short, punchy answers will keep coming back. Optimize for engagement.
"""


@app.route("/ask-bot")
def askbot_page():
    """Ask a Bot — UPSC AI Chat Assistant."""
    return render_template("askbot.html")


@app.route("/ask-bot/chat", methods=["POST"])
def askbot_chat():
    """Chat endpoint for the UPSC AI assistant."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "No question provided"}), 400

    history = data.get("history", [])

    try:
        from llm.gemini_client import call_gemini

        # Build conversation context from history
        conversation = _UPSC_SYSTEM_PROMPT + "\n\n"
        for msg in history[:-1]:  # exclude the current query (already in 'query')
            role = "Student" if msg.get("role") == "user" else "Assistant"
            conversation += f"{role}: {msg.get('text', '')}\n\n"

        conversation += f"Student: {query}\n\nAssistant:"

        answer = call_gemini(conversation)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Chat error: {str(e)}"}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  UPSC Prelims & Mains Engine — Dashboard")
    print("  http://localhost:5001")
    print("=" * 50)
    app.run(debug=True, port=5001, host="0.0.0.0")
