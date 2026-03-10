# pipeline.py — Main orchestrator for UPSC Prelims & Mains Engine
#
# Flow:
# 1. Read input (PDF / text / image)
# 2. Compress & clean text
# 3. Split into semantic chunks (one topic per chunk)
# 4. For each chunk:
#    a. Classify → Prelims (main_topic, subtopic, sub_subtopic)
#    b. Generate Prelims Content / Summary / MCQs
#    c. Classify → Mains (GS1–GS4 topic path)
#    d. Generate Mains Content / Summary / Q&A
#    e. Append to organized text files + regenerate PDFs
# 5. Store raw content in the single majority topic (prelims + mains)

import os
import sys
from collections import Counter
from pathlib import Path

from config import (
    ALL_TOPIC_FILE_MAP, MAINS_TOPIC_FILE_MAP, DELIMITER, INPUT_DIR,
)
from ocr.pdf_loader import extract_text_from_pdf
from chunking.text_chunker import chunk_text, semantic_split
from llm.gemini_client import call_gemini
from llm.text_cleaner import zero_loss_compress, clean_text

# Prelims
from llm.topic_classifier import classify_topic
from llm.content_generator import generate_content
from llm.summary_generator import generate_summary
from llm.qa_generator import generate_mcqs
from utils.file_manager import (
    append_content, append_summary, append_qa, append_raw_content,
    append_mains_content, append_mains_summary, append_mains_qa, append_mains_raw_content,
)
# Mains
from llm.mains_topic_classifier import classify_mains_topic
from llm.mains_content_generator import generate_mains_content
from llm.mains_summary_generator import generate_mains_summary
from llm.mains_qa_generator import generate_mains_qa


def _get_file_stem(topic: str) -> str:
    """Convert prelims topic name to file stem."""
    return ALL_TOPIC_FILE_MAP.get(topic, "current_affairs")


def _get_mains_file_stem(topic: str) -> str:
    """Convert mains topic name to file stem."""
    return MAINS_TOPIC_FILE_MAP.get(topic, "gs3_economy")


def _read_input(file_path: str) -> str:
    """Read input file and return raw text."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        print(f"📖 Extracting text from PDF: {path.name}")
        return extract_text_from_pdf(str(path))
    elif ext == ".txt":
        print(f"📖 Reading text file: {path.name}")
        return path.read_text(encoding="utf-8")
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        print(f"📖 Running OCR on image: {path.name}")
        from ocr.image_loader import extract_text_from_image
        return extract_text_from_image(str(path))
    else:
        # Try reading as text
        print(f"📖 Reading file as text: {path.name}")
        return path.read_text(encoding="utf-8")


def run_pipeline(file_path: str, article_id: str = None):
    """
    Main pipeline: process an input file end-to-end.

    Accepts: PDF, TXT, or image file path.
    Outputs: Raw Content PDF, Content PDF, Summary PDF, Q&A PDF — per topic.
    Each PDF is organized by subtopic → sub-subtopic hierarchy.
    """
    from utils.article_registry import update_status, add_topic, set_title

    if article_id:
        update_status(article_id, "processing")

    print("=" * 60)
    print("  UPSC PRELIMS & MAINS ENGINE — Processing Started")
    print("=" * 60)

    # ── Step 1: Read input ──────────────────────────────────────
    raw_text = _read_input(file_path)
    if not raw_text.strip():
        print("❌ No text extracted from input. Exiting.")
        if article_id:
            update_status(article_id, "error", "No text extracted from input")
        return

    print(f"✅ Text extracted ({len(raw_text)} chars)")

    # ── Step 2: Compress (zero-loss) ────────────────────────────
    print("🔄 Compressing text (zero-loss)...")
    pre_chunks = chunk_text(raw_text, max_tokens=7000)
    compressed_parts = []
    for i, ch in enumerate(pre_chunks, 1):
        print(f"   → Compressing chunk {i}/{len(pre_chunks)}")
        compressed_parts.append(zero_loss_compress(ch))
    compressed_text = "\n\n".join(compressed_parts)

    print("✅ Compression done")

    # ── Step 3: Semantic split into topic-wise chunks ───────────
    print("🔄 Splitting into topic-wise chunks...")
    topic_chunks = semantic_split(compressed_text, call_gemini, DELIMITER)
    print(f"✅ Got {len(topic_chunks)} topic chunks")

    # ── Step 4: Process each chunk (Prelims + Mains) ──────────────
    total = len(topic_chunks)
    prelims_stem_counter = Counter()   # stem → count (for majority topic)
    mains_stem_counter = Counter()     # stem → count (for majority topic)
    prelims_stem_map = {}              # stem → topic_name
    mains_stem_map = {}                # stem → topic_name

    for idx, chunk in enumerate(topic_chunks, 1):
        print(f"\n{'─' * 50}")
        print(f"  Processing chunk {idx}/{total}")
        print(f"{'─' * 50}")

        # ══════════════════════════════════════════════════════
        #  PRELIMS PROCESSING
        # ══════════════════════════════════════════════════════

        # ── 4a. Classify topic (Prelims 3-level) ──────────────
        main_topic, subtopic, sub_subtopic = classify_topic(chunk)
        file_stem = _get_file_stem(main_topic)
        prelims_stem_counter[file_stem] += 1
        prelims_stem_map[file_stem] = main_topic
        print(f"  📌 Prelims: {main_topic} → {subtopic} → {sub_subtopic}")

        # Track topic in article registry
        if article_id:
            add_topic(article_id, main_topic, subtopic, file_stem)

        # ── 4b. Generate Prelims Content (A–G) ───────────────
        print("  📝 Generating prelims content...")
        content_text = generate_content(chunk, subtopic, sub_subtopic)
        cleaned_content = clean_text(content_text)
        append_content(file_stem, cleaned_content, article_id)

        # ── 4c. Generate Prelims Summary (A–E) ───────────────
        print("  📋 Generating prelims summary...")
        summary_text = generate_summary(cleaned_content, subtopic, sub_subtopic)
        cleaned_summary = clean_text(summary_text)
        append_summary(file_stem, cleaned_summary, article_id)

        # ── 4d. Generate Prelims MCQs ─────────────────────────
        print("  ❓ Generating prelims MCQs...")
        qa_text = generate_mcqs(cleaned_content, subtopic, sub_subtopic)
        cleaned_qa = clean_text(qa_text)
        append_qa(file_stem, cleaned_qa, article_id)

        print(f"  ✅ Prelims chunk {idx}/{total} → {main_topic}")

        # ══════════════════════════════════════════════════════
        #  MAINS PROCESSING
        # ══════════════════════════════════════════════════════

        # ── 4f. Classify topic (Mains GS1–GS4) ──────────────
        m_topic, m_subtopic, m_sub_subtopic = classify_mains_topic(chunk)
        m_file_stem = _get_mains_file_stem(m_topic)
        mains_stem_counter[m_file_stem] += 1
        mains_stem_map[m_file_stem] = m_topic
        print(f"  📌 Mains: {m_topic} → {m_subtopic} → {m_sub_subtopic}")

        # Track mains topic in article registry
        if article_id:
            add_topic(article_id, f"[M] {m_topic}", m_subtopic, m_file_stem)

        # ── 4g. Generate Mains Content ────────────────────────
        print("  📝 Generating mains content...")
        m_content = generate_mains_content(chunk, m_file_stem, m_subtopic, m_sub_subtopic)
        m_cleaned_content = clean_text(m_content)
        append_mains_content(m_file_stem, m_cleaned_content, article_id)

        # ── 4h. Generate Mains Summary ────────────────────────
        print("  📋 Generating mains summary...")
        m_summary = generate_mains_summary(m_cleaned_content, m_file_stem, m_subtopic, m_sub_subtopic)
        m_cleaned_summary = clean_text(m_summary)
        append_mains_summary(m_file_stem, m_cleaned_summary, article_id)

        # ── 4i. Generate Mains Q&A ───────────────────────────
        print("  ❓ Generating mains Q&A...")
        m_qa = generate_mains_qa(m_cleaned_content, m_file_stem, m_subtopic, m_sub_subtopic)
        m_cleaned_qa = clean_text(m_qa)
        append_mains_qa(m_file_stem, m_cleaned_qa, article_id)

        print(f"  ✅ Mains chunk {idx}/{total} → {m_topic}")

    # ── Step 5: Store raw content in SINGLE majority topic ──────────
    #    Prelims: pick the stem with most chunk hits
    #    Mains:   pick the stem with most chunk hits
    print(f"\n{'─' * 50}")
    print(f"  📦 Storing raw content in majority topic(s)")
    print(f"{'─' * 50}")

    # Prelims raw content → single majority topic
    if prelims_stem_counter:
        majority_p_stem = prelims_stem_counter.most_common(1)[0][0]
        majority_p_topic = prelims_stem_map.get(majority_p_stem, "")
        append_raw_content(majority_p_stem, compressed_text, majority_p_topic, article_id)
        print(f"  ✅ Prelims raw content → {majority_p_stem} ({majority_p_topic})")

    # Mains raw content → single majority topic
    if mains_stem_counter:
        majority_m_stem = mains_stem_counter.most_common(1)[0][0]
        majority_m_topic = mains_stem_map.get(majority_m_stem, "")
        append_mains_raw_content(majority_m_stem, compressed_text, majority_m_topic, article_id)
        print(f"  ✅ Mains raw content → {majority_m_stem} ({majority_m_topic})")

    print(f"\n{'=' * 60}")
    print("  ✅ ALL DONE — Prelims + Mains Processing Complete!")
    print(f"{'=' * 60}")
    print(f"  PRELIMS:")
    print(f"    Raw Content → output/pdf/raw_content/")
    print(f"    Content     → output/pdf/content/")
    print(f"    Summary     → output/pdf/summary/")
    print(f"    Q&A         → output/pdf/questions/")
    print(f"  MAINS:")
    print(f"    Raw Content → output/pdf/mains_raw_content/")
    print(f"    Content     → output/pdf/mains_content/")
    print(f"    Summary     → output/pdf/mains_summary/")
    print(f"    Q&A         → output/pdf/mains_questions/")
    print(f"{'=' * 60}")

    # Generate article title using Gemini and update registry
    if article_id:
        try:
            title_prompt = (
                "Generate a short, descriptive title (max 10 words) for this article/document. "
                "Return ONLY the title, nothing else.\n\n"
                + raw_text[:2000]
            )
            title = call_gemini(title_prompt).strip().strip('"').strip("'")
            if title:
                set_title(article_id, title)
        except Exception:
            pass
        update_status(article_id, "processed")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default: look for any file in input/
        input_files = list(INPUT_DIR.glob("*"))
        input_files = [f for f in input_files if f.is_file()]
        if not input_files:
            print("❌ No input file provided. Usage:")
            print("   python pipeline.py <path-to-pdf-or-txt>")
            print("   Or place a file in input/ folder.")
            sys.exit(1)
        input_file = str(input_files[0])

    run_pipeline(input_file)
