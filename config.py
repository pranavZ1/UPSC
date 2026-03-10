# config.py — Central configuration for UPSC Prelims & Mains Engine

from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"

# Books library (only FAISS indexes stored locally)
BOOKS_DIR = BASE_DIR / "books"
BOOKS_INDEX_DIR = BOOKS_DIR / "indexes"

# Previous Year Questions
PYQ_DATA_DIR = BASE_DIR.parent / "data" / "upsc_prelims_gs"
PYQ_CACHE_DIR = BASE_DIR / "pyq" / "cache"

# Create required directories on import
for d in [INPUT_DIR, BOOKS_INDEX_DIR, PYQ_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── RAG Settings ─────────────────────────────────────────────────────────
EMBEDDING_MODEL = "gemini-embedding-001"
RAG_CHUNK_SIZE = 800       # tokens per chunk
RAG_CHUNK_OVERLAP = 100    # overlap tokens
RAG_TOP_K = 5              # top-k chunks for context

# ─── LLM Settings ────────────────────────────────────────────────────────
MAX_TOKENS_PER_CHUNK = 8000
TOKEN_BUFFER = 200
DELIMITER = "\n////////////**////////////\n"

# ─── Topic → File name mapping ───────────────────────────────────────────
# Main topics from Prelims topics.txt  (Paper I)
TOPIC_FILE_MAP = {
    "Current Affairs": "current_affairs",
    "History": "history",
    "Geography": "geography",
    "Polity & Governance": "polity_governance",
    "Economy": "economy",
    "Science & Technology": "science_technology",
    "Environment & Ecology": "environment_ecology",
    "Art & Culture": "art_culture",
}

# Paper II (CSAT) — kept separate; same 3-folder treatment
CSAT_TOPIC_FILE_MAP = {
    "Comprehension": "csat_comprehension",
    "Reasoning": "csat_reasoning",
    "Quantitative Aptitude": "csat_quantitative",
    "Data Interpretation": "csat_data_interpretation",
    "Decision Making": "csat_decision_making",
    "Data Sufficiency": "csat_data_sufficiency",
}

ALL_TOPIC_FILE_MAP = {**TOPIC_FILE_MAP, **CSAT_TOPIC_FILE_MAP}

# Valid main-topic names (for classifier)
VALID_TOPICS = list(TOPIC_FILE_MAP.keys())

# ─── Mains Topic → File name mapping ─────────────────────────────────────
# GS1: History, Culture, Society, Geography
# GS2: Polity, Governance, Social Justice, IR
# GS3: Economy, Agriculture, S&T, Environment, Security, DM
# GS4: Ethics

MAINS_TOPIC_FILE_MAP = {
    # GS1
    "Indian Art & Culture":     "gs1_art_culture",
    "History":                  "gs1_history",
    "Indian Society":           "gs1_society",
    "Geography":                "gs1_geography",
    # GS2
    "Constitution & Polity":    "gs2_polity",
    "Governance":               "gs2_governance",
    "Social Justice":           "gs2_social_justice",
    "International Relations":  "gs2_international_relations",
    # GS3
    "Economy":                  "gs3_economy",
    "Agriculture":              "gs3_agriculture",
    "Science & Technology":     "gs3_science_technology",
    "Environment":              "gs3_environment",
    "Internal Security":        "gs3_internal_security",
    "Disaster Management":      "gs3_disaster_management",
    # GS4
    "Ethics":                   "gs4_ethics",
}

VALID_MAINS_TOPICS = list(MAINS_TOPIC_FILE_MAP.keys())

# GS Paper labels for display
MAINS_PAPER_MAP = {
    "gs1_art_culture": "GS1", "gs1_history": "GS1", "gs1_society": "GS1", "gs1_geography": "GS1",
    "gs2_polity": "GS2", "gs2_governance": "GS2", "gs2_social_justice": "GS2", "gs2_international_relations": "GS2",
    "gs3_economy": "GS3", "gs3_agriculture": "GS3", "gs3_science_technology": "GS3",
    "gs3_environment": "GS3", "gs3_internal_security": "GS3", "gs3_disaster_management": "GS3",
    "gs4_ethics": "GS4",
}
