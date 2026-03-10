# ocr/image_loader.py — Extract text from images using Gemini Vision
#
# Uses Gemini's multimodal capability instead of Tesseract OCR.
# Much more accurate for photos of printed/handwritten UPSC content.

import base64
from pathlib import Path
from google import genai
from dotenv import load_dotenv
import os

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
    """Extract text from an image file using Gemini Vision."""
    img_path = Path(path)
    img_bytes = img_path.read_bytes()
    img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")

    # Detect MIME type
    ext = img_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }
    mime = mime_map.get(ext, "image/jpeg")

    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "parts": [
                    {"text": _PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime,
                            "data": img_b64,
                        }
                    },
                ]
            }
        ],
    )
    return response.text.strip()
