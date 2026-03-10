# pyq/data_loader.py — Load, classify & serve UPSC Prelims PYQ data (MongoDB)
#
# Questions live in pyq_questions collection. On first access, if un-classified
# questions exist, a background thread batch-classifies them via Gemini
# and writes topic labels back to MongoDB.

import threading
from db import pyq_questions_col

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

# ── Classification state (module-level) ─────────────────────────────────
_classify_lock = threading.Lock()
_classify_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "done": False,
    "error": None,
}


# ── Public API ───────────────────────────────────────────────────────────

def get_master_data() -> tuple[list[dict] | None, dict]:
    """Return (questions_list, status_dict).

    If every question has a topic → instant return from MongoDB.
    Otherwise kick off background classification.
    """
    col = pyq_questions_col()
    unclassified_count = col.count_documents({"topic": None})

    if unclassified_count == 0:
        # All classified → return full dataset
        questions = list(col.find({}, {"_id": 0}).sort([("year", -1), ("question_number", 1)]))
        return questions, {"status": "ready"}

    with _classify_lock:
        if _classify_status["running"]:
            return None, {
                "status": "classifying",
                "progress": _classify_status["progress"],
                "total": _classify_status["total"],
            }
        # Start background classification
        _classify_status.update({
            "running": True,
            "progress": 0,
            "total": unclassified_count,
            "done": False,
            "error": None,
        })

    t = threading.Thread(target=_run_classification, daemon=True)
    t.start()
    return None, {
        "status": "classifying",
        "progress": 0,
        "total": unclassified_count,
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


def _run_classification():
    global _classify_status
    from llm.gemini_client import call_gemini

    col = pyq_questions_col()
    unclassified = list(col.find({"topic": None}, {"_id": 0}))

    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i : i + BATCH_SIZE]
        try:
            result = _classify_batch(batch, call_gemini)
        except Exception as e:
            print(f"[PYQ] Classification batch error: {e}")
            result = {q["qid"]: "Current Affairs" for q in batch}

        # Write classifications back to MongoDB
        for qid, topic in result.items():
            col.update_one({"qid": qid}, {"$set": {"topic": topic}})

        _classify_status["progress"] = min(i + BATCH_SIZE, len(unclassified))

    # Clean up original_tag field
    col.update_many({}, {"$unset": {"original_tag": ""}})

    _classify_status["running"] = False
    _classify_status["done"] = True
    total = col.count_documents({})
    print(f"[PYQ] Classification complete — {total} questions in MongoDB.")


def _classify_batch(questions: list[dict], call_gemini) -> dict[str, str]:
    """Send a batch of questions to Gemini for topic classification."""
    q_lines = []
    for q in questions:
        snippet = q["question"][:250].replace("\n", " ")
        opts = " | ".join(v[:60] for v in q["options"].values())
        q_lines.append(f'{q["qid"]}: {snippet} [{opts}]')

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

    import json
    response = call_gemini(prompt)

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

    validated: dict[str, str] = {}
    for qid, topic in result.items():
        if topic in PYQ_TOPICS:
            validated[qid] = topic
        else:
            matched = False
            for t in PYQ_TOPICS:
                if t.lower() in topic.lower() or topic.lower() in t.lower():
                    validated[qid] = t
                    matched = True
                    break
            if not matched:
                validated[qid] = "Current Affairs"

    return validated
