# pyq/data_loader.py — Load, classify & serve UPSC Prelims PYQ data
#
# On first load, reads all JSON year-files, extracts existing topic tags
# (2025 only), then uses Gemini to classify the rest in batches.
# Results are cached in a master JSON file.

import json
import re
import threading
from pathlib import Path

from config import PYQ_DATA_DIR, PYQ_CACHE_DIR

# ── Standard UPSC Prelims GS-I topics ──────────────────────────────────
PYQ_TOPICS = [
    "History",
    "Art & Culture",
    "Geography",
    "Environment & Ecology",
    "Polity & Governance",
    "Economy",
    "Science & Technology",
    "International Relations",
    "Current Affairs",
]

YEARS = list(range(2025, 2014, -1))  # 2025 → 2015

MASTER_FILE = PYQ_CACHE_DIR / "pyq_classified.json"

# ── Map 2025 inline tags → standard topics ──────────────────────────────
_TAG_MAP = {
    "Ancient History": "History",
    "Medieval History": "History",
    "Modern History": "History",
    "Art & Culture": "Art & Culture",
    "Fundamental Rights": "Polity & Governance",
    "Local Government": "Polity & Governance",
    "Salient Features of Indian Constitution": "Polity & Governance",
    "State Legislature & Executive": "Polity & Governance",
    "The Judiciary": "Polity & Governance",
    "Union Executive": "Polity & Governance",
    "Union Legislature": "Polity & Governance",
    "Fiscal Policy": "Economy",
    "Monetary Policy": "Economy",
    "External Sector": "Economy",
    "Public Finance in India": "Economy",
    "Agriculture": "Economy",
    "Basic Biology": "Science & Technology",
    "Chemistry": "Science & Technology",
    "Nanotechnology": "Science & Technology",
    "Electronics & Communication": "Science & Technology",
    "Space": "Science & Technology",
    "Defence": "Science & Technology",
    "Disease": "Science & Technology",
    "International Relations": "International Relations",
    "Government programs & schemes": "Current Affairs",
    "Miscellaneous": "Current Affairs",
}

# ── Classification state (module-level) ─────────────────────────────────
_classify_lock = threading.Lock()
_classify_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "done": False,
    "error": None,
}


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_tag(text: str) -> tuple[str, str | None]:
    """Pull [Topic Tag] out of question text. Return (cleaned_text, tag)."""
    m = re.search(r'\[([^\]]+)\]', text)
    if m:
        tag = m.group(1)
        clean = (text[:m.start()] + text[m.end():]).strip()
        return clean, tag
    return text, None


def _load_raw() -> list[dict]:
    """Read every year-file and return a flat list of question dicts."""
    questions: list[dict] = []
    for year in YEARS:
        fp = PYQ_DATA_DIR / f"upsc_prelims_{year}.json"
        if not fp.exists():
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        for q in data:
            clean_text, tag = _extract_tag(q["question"])
            topic = _TAG_MAP.get(tag) if tag else None
            questions.append({
                "id": f"{year}_q{q['question_number']}",
                "year": year,
                "question_number": q["question_number"],
                "question": clean_text,
                "options": q["options"],
                "answer": q["answer"],
                "topic": topic,          # None → needs classification
                "original_tag": tag,
            })
    return questions


# ── Public API ───────────────────────────────────────────────────────────

def get_master_data() -> tuple[list[dict] | None, dict]:
    """Return (questions_list, status_dict).

    If the master file exists → instant return.
    Otherwise kick off background classification.
    """
    if MASTER_FILE.exists():
        data = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
        return data, {"status": "ready"}

    with _classify_lock:
        if _classify_status["running"]:
            return None, {
                "status": "classifying",
                "progress": _classify_status["progress"],
                "total": _classify_status["total"],
            }
        # Start classification
        all_q = _load_raw()
        unclassified = [q for q in all_q if q["topic"] is None]
        _classify_status.update({
            "running": True,
            "progress": 0,
            "total": len(unclassified),
            "done": False,
            "error": None,
        })

    t = threading.Thread(target=_run_classification, args=(all_q, unclassified), daemon=True)
    t.start()
    return None, {
        "status": "classifying",
        "progress": 0,
        "total": _classify_status["total"],
    }


def get_classify_status() -> dict:
    return {
        "status": "ready" if _classify_status["done"] else (
            "error" if _classify_status["error"] else "classifying"
        ),
        "progress": _classify_status["progress"],
        "total": _classify_status["total"],
        "error": _classify_status.get("error"),
    }


# ── Background classification ────────────────────────────────────────────

BATCH_SIZE = 50


def _run_classification(all_questions: list[dict], unclassified: list[dict]):
    global _classify_status
    from llm.gemini_client import call_gemini

    classified_map: dict[str, str] = {}

    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i : i + BATCH_SIZE]
        try:
            result = _classify_batch(batch, call_gemini)
            classified_map.update(result)
            _classify_status["progress"] = min(i + BATCH_SIZE, len(unclassified))
        except Exception as e:
            print(f"[PYQ] Classification batch error: {e}")
            # On error, fall back to "Current Affairs" for this batch
            for q in batch:
                classified_map[q["id"]] = "Current Affairs"
            _classify_status["progress"] = min(i + BATCH_SIZE, len(unclassified))

    # Apply classifications
    for q in all_questions:
        if q["topic"] is None:
            q["topic"] = classified_map.get(q["id"], "Current Affairs")

    # Remove helper field before saving
    for q in all_questions:
        q.pop("original_tag", None)

    # Save master file
    PYQ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_FILE.write_text(
        json.dumps(all_questions, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _classify_status["running"] = False
    _classify_status["done"] = True
    print(f"[PYQ] Classification complete — {len(all_questions)} questions saved.")


def _classify_batch(questions: list[dict], call_gemini) -> dict[str, str]:
    """Send a batch of questions to Gemini for topic classification."""
    q_lines = []
    for q in questions:
        # Send first 250 chars of question + option keywords for context
        snippet = q["question"][:250].replace("\n", " ")
        opts = " | ".join(v[:60] for v in q["options"].values())
        q_lines.append(f'{q["id"]}: {snippet} [{opts}]')

    q_list = "\n".join(q_lines)
    topics_str = ", ".join(PYQ_TOPICS)

    prompt = f"""Classify each UPSC Civil Services Preliminary Examination (GS Paper I) question into EXACTLY ONE of these topics:
{topics_str}

Classification guide:
- Ancient / Medieval / Modern history, freedom movement, revolts, empires, reform movements → History
- Temples, paintings, music, dance forms, literature, UNESCO heritage → Art & Culture
- Rivers, climate, soil, minerals, crops, maps, monsoon, ocean currents → Geography
- Biodiversity, ecology, pollution, national parks, wildlife, climate change → Environment & Ecology
- Constitution, parliament, judiciary, governance, fundamental rights, elections → Polity & Governance
- GDP, RBI, fiscal policy, trade, banking, budget, inflation, agriculture economics → Economy
- Space, ISRO, biology, physics, chemistry, nuclear, defence tech, IT, biotech → Science & Technology
- UN, treaties, foreign policy, bilateral/multilateral summits, global organizations → International Relations
- Recent govt schemes, awards, sports, current events that don't fit above → Current Affairs

Questions (format — ID: question_text [option_keywords]):
{q_list}

Return ONLY a valid JSON object mapping each question ID to its topic:
{{"2015_q1": "History", "2015_q2": "Economy", ...}}

JSON:"""

    response = call_gemini(prompt)

    # Parse JSON from response
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        cleaned = cleaned[start:end]

    result = json.loads(cleaned)

    # Validate topics
    validated: dict[str, str] = {}
    for qid, topic in result.items():
        if topic in PYQ_TOPICS:
            validated[qid] = topic
        else:
            # Try fuzzy match
            matched = False
            for t in PYQ_TOPICS:
                if t.lower() in topic.lower() or topic.lower() in t.lower():
                    validated[qid] = t
                    matched = True
                    break
            if not matched:
                validated[qid] = "Current Affairs"

    return validated
