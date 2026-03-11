# ocr/image_loader.py — Extract text from images using Gemini Vision
#
# Uses Gemini's multimodal capability instead of Tesseract OCR.
# Much more accurate for photos of printed/handwritten UPSC content.
#
# Uses the Gemini **File API** (upload → reference) instead of inline
# base64.  This is more reliable for non-standard JPEG encodings
# (e.g. WhatsApp images) that trigger INVALID_ARGUMENT with inline_data.

from pathlib import Path
from google import genai
from dotenv import load_dotenv
import os, time

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

_PROMPT = """Extract ALL text from this image. 
- Reproduce every word, number, heading, bullet point, and footnote exactly as it appears.
- Preserve the original structure (headings, paragraphs, lists, tables).
- If text is partially obscured, do your best to infer it.
- Output plain text only — no markdown formatting.
- If the image contains a table, reproduce it in a readable text format.
"""


def extract_text_from_image(path: str) -> str:
    """Extract text from an image file using Gemini Vision (File API)."""
    img_path = Path(path)

    # Upload via Gemini File API — handles encoding/metadata automatically
    uploaded = _client.files.upload(file=str(img_path))

    # Wait for ACTIVE state (usually instant, but just in case)
    for _ in range(10):
        if uploaded.state.name == "ACTIVE":
            break
        time.sleep(1)
        uploaded = _client.files.get(name=uploaded.name)

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[_PROMPT, uploaded],
        )
        return response.text.strip()
    finally:
        # Clean up uploaded file
        try:
            _client.files.delete(name=uploaded.name)
        except Exception:
            pass
