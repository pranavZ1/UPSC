# ocr/pdf_loader.py — Extract text from PDF files

from pypdf import PdfReader


def extract_text_from_pdf(path: str) -> str:
    """Extract all text from a PDF file using pypdf."""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)
