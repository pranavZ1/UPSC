# utils/pdf_creator.py — Generate well-styled PDFs using ReportLab
#
# Uses reportlab (pure Python, no system deps) to create clean A4 PDFs.
# Recognizes [SUBTOPIC] and [FOCUS] markers for hierarchy display.
# Section names: A. Core Information, B. Significance & Impact, etc.

import io
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

# ─── Custom Styles ────────────────────────────────────────────────────────

def _build_styles():
    """Build custom paragraph styles for UPSC notes."""
    styles = getSampleStyleSheet()

    # ── Subtopic banner (top-level grouping) ──
    styles.add(ParagraphStyle(
        name="UPSCSubtopic",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=HexColor("#ffffff"),
        backColor=HexColor("#1a237e"),
        spaceAfter=4,
        spaceBefore=20,
        leading=22,
        leftIndent=8,
        rightIndent=8,
        borderPadding=(8, 10, 8, 10),
        alignment=TA_LEFT,
    ))

    # ── Focus area (sub-subtopic) ──
    styles.add(ParagraphStyle(
        name="UPSCFocus",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=HexColor("#1a237e"),
        backColor=HexColor("#e8eaf6"),
        spaceAfter=8,
        spaceBefore=14,
        leading=18,
        leftIndent=8,
        rightIndent=8,
        borderPadding=(6, 8, 6, 8),
        alignment=TA_LEFT,
    ))

    # ── Title of individual content block ──
    styles.add(ParagraphStyle(
        name="UPSCTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=HexColor("#1a237e"),
        spaceAfter=6,
        spaceBefore=10,
        leading=18,
    ))

    # ── Source / metadata line ──
    styles.add(ParagraphStyle(
        name="UPSCMeta",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=HexColor("#546e7a"),
        spaceAfter=8,
        spaceBefore=1,
        leading=12,
    ))

    # ── Section header (A. Core Information, etc.) ──
    styles.add(ParagraphStyle(
        name="UPSCSection",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=HexColor("#283593"),
        spaceAfter=5,
        spaceBefore=14,
        leading=15,
    ))

    # ── Sub-section / Q-numbers ──
    styles.add(ParagraphStyle(
        name="UPSCSubSection",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=HexColor("#37474f"),
        spaceAfter=4,
        spaceBefore=10,
        leading=14,
    ))

    # ── Body text ──
    styles.add(ParagraphStyle(
        name="UPSCBody",
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#1a1a1a"),
        spaceAfter=4,
        spaceBefore=2,
        leading=14,
        alignment=TA_JUSTIFY,
    ))

    # ── Bullet point ──
    styles.add(ParagraphStyle(
        name="UPSCBullet",
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#1a1a1a"),
        spaceAfter=2,
        spaceBefore=1,
        leading=13,
        leftIndent=20,
        bulletIndent=8,
        alignment=TA_LEFT,
    ))

    return styles


# ─── Text → PDF flowables ────────────────────────────────────────────────

def _safe(text: str) -> str:
    """Escape XML-special characters for ReportLab."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text_to_flowables(text: str, styles) -> list:
    """
    Parse organized text (with [SUBTOPIC]/[FOCUS] markers, section headers
    like A. Core Information, bullets, Q&A patterns) into ReportLab flowables.
    """
    flowables = []
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flowables.append(Spacer(1, 4))
            continue

        safe = _safe(stripped)

        # ── Skip article ID markers (invisible in PDF) ──
        if stripped.startswith("[AID:"):
            continue

        # ── [SUBTOPIC] marker → big colored banner ──
        m = re.match(r'^\[SUBTOPIC\]\s*(.+)', stripped)
        if m:
            flowables.append(Spacer(1, 12))
            flowables.append(Paragraph(_safe(m.group(1).strip()), styles["UPSCSubtopic"]))
            flowables.append(Spacer(1, 2))
            continue

        # ── [FOCUS] marker → colored sub-banner ──
        m = re.match(r'^\[FOCUS\]\s*(.+)', stripped)
        if m:
            flowables.append(Paragraph(_safe(m.group(1).strip()), styles["UPSCFocus"]))
            continue

        # ── Title: line ──
        m = re.match(r'^Title:\s*(.+)', stripped, re.IGNORECASE)
        if m:
            flowables.append(Paragraph(_safe(m.group(1).strip()), styles["UPSCTitle"]))
            flowables.append(HRFlowable(
                width="100%", thickness=1.5,
                color=HexColor("#1a237e"), spaceAfter=6
            ))
            continue

        # ── Source: / Tags: lines → metadata ──
        if re.match(r'^(Source|Tags|Date):', stripped, re.IGNORECASE):
            flowables.append(Paragraph(safe, styles["UPSCMeta"]))
            continue

        # ── Thin separator (between blocks in same focus) ──
        if re.match(r'^[─]{10,}$', stripped):
            flowables.append(Spacer(1, 8))
            flowables.append(HRFlowable(
                width="80%", thickness=1, dash=(4, 4),
                color=HexColor("#b0bec5"), spaceAfter=8
            ))
            continue

        # ── Thick separator (between subtopics) ──
        if re.match(r'^[═]{10,}$', stripped):
            flowables.append(Spacer(1, 10))
            flowables.append(HRFlowable(
                width="100%", thickness=2,
                color=HexColor("#1a237e"), spaceAfter=10
            ))
            continue

        # ── Section headers: "A. Core Information", "B. Significance & Impact", etc. ──
        section_match = re.match(r'^([A-G])\.\s+(.+)', stripped)
        if section_match:
            label = section_match.group(1)
            title = section_match.group(2)
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(
                f"{label}. {_safe(title)}", styles["UPSCSection"]
            ))
            flowables.append(HRFlowable(
                width="50%", thickness=0.5,
                color=HexColor("#90a4ae"), spaceAfter=4
            ))
            continue

        # ── ANSWER KEY WITH EXPLANATIONS header ──
        if "ANSWER KEY" in stripped.upper():
            flowables.append(Spacer(1, 10))
            flowables.append(Paragraph(safe, styles["UPSCSection"]))
            flowables.append(HRFlowable(
                width="60%", thickness=0.5,
                color=HexColor("#90a4ae"), spaceAfter=6
            ))
            continue

        # ── Bullet points: •, -, * ──
        if re.match(r'^[\u2022\-\*]\s', stripped):
            bullet_text = re.sub(r'^[\u2022\-\*]\s*', '', safe)
            flowables.append(Paragraph(f"• {bullet_text}", styles["UPSCBullet"]))
            continue

        # ── Question numbers: Q1., Q2., etc. ──
        q_match = re.match(r'^(Q\d+\.)\s*(.*)', stripped)
        if q_match:
            flowables.append(Spacer(1, 6))
            q_text = _safe(q_match.group(2))
            flowables.append(Paragraph(
                f"<b>{q_match.group(1)}</b> {q_text}", styles["UPSCSubSection"]
            ))
            continue

        # ── Option lines: (a), (b), (c), (d) ──
        opt_match = re.match(r'^\(([a-d])\)\s*(.*)', stripped)
        if opt_match:
            opt_text = _safe(opt_match.group(2))
            flowables.append(Paragraph(
                f"({opt_match.group(1)}) {opt_text}", styles["UPSCBullet"]
            ))
            continue

        # ── Answer: lines ──
        if re.match(r'^(Q\d+\.)?\s*Answer:', stripped, re.IGNORECASE):
            flowables.append(Paragraph(f"<b>{safe}</b>", styles["UPSCBody"]))
            continue

        # ── Explanation: lines ──
        if re.match(r'^Explanation:', stripped, re.IGNORECASE):
            flowables.append(Paragraph(f"<i>{safe}</i>", styles["UPSCBody"]))
            continue

        # ── Separator-like lines (===, ---) ──
        if re.match(r'^[=\-]{5,}$', stripped):
            flowables.append(Spacer(1, 4))
            flowables.append(HRFlowable(
                width="100%", thickness=1, dash=(3, 3),
                color=HexColor("#90a4ae"), spaceAfter=4
            ))
            continue

        # ── Regular paragraph ──
        flowables.append(Paragraph(safe, styles["UPSCBody"]))

    return flowables


# ─── Public API ───────────────────────────────────────────────────────────

def build_pdf_bytes(text: str) -> bytes:
    """Build a PDF from structured plain text and return the raw bytes."""
    styles = _build_styles()
    flowables = _text_to_flowables(text, styles)

    if not flowables:
        flowables = [Paragraph("(No content)", styles["UPSCBody"])]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(flowables)
    return buf.getvalue()
