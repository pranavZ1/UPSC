# llm/gemini_client.py — Gemini API wrapper

from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def call_gemini(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """Call Gemini model and return text response."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""


def generate_image(prompt: str) -> bytes | None:
    """Generate an image using Gemini and return raw PNG bytes."""
    import base64 as _b64

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )
    if not response.candidates or not response.candidates[0].content:
        return None
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            raw = part.inline_data.data
            # SDK returns base64-encoded bytes; decode to actual PNG
            if isinstance(raw, bytes) and raw[:4] != b'\x89PNG':
                try:
                    return _b64.b64decode(raw)
                except Exception:
                    return raw
            return raw
    return None
