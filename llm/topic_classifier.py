# llm/topic_classifier.py — Classify input text into UPSC topic path
#
# Returns (main_topic, subtopic, sub_subtopic) for precise placement
# inside the topic hierarchy from Prelims topics.txt.

from llm.gemini_client import call_gemini
from config import VALID_TOPICS
from topics.topic_list import (
    FLAT_TOPIC_LIST, TOPIC_HIERARCHY,
    parse_topic_path, find_best_subtopic, find_best_sub_subtopic,
)


def classify_topic(text: str) -> tuple[str, str, str]:
    """
    Classify a chunk of text into a 3-level UPSC topic path.

    Returns:
        (main_topic, subtopic, sub_subtopic)
        e.g. ("Current Affairs", "Polity & Governance in News",
              "Bills/Acts/Amendments: what changed, why, key features")
    """
    # Build flat list for the prompt
    topic_str = "\n".join(f"  - {t}" for t in FLAT_TOPIC_LIST)

    prompt = f"""You are an expert UPSC Prelims syllabus classifier.

TASK:
Read the content below and classify it into exactly ONE topic path from the list.
A topic path has 3 levels separated by ' | ':
    Main Topic | Subtopic | Sub-subtopic

Return ONLY the topic path — nothing else.

VALID TOPIC PATHS:
{topic_str}

RULES:
- Pick the SINGLE BEST matching topic path.
- Return the path EXACTLY as written above (case-sensitive, pipe-separated).
- Do NOT explain your reasoning.
- Do NOT return anything other than the topic path.
- If unsure, default to "Current Affairs | Polity & Governance in News | Bills/Acts/Amendments: what changed, why, key features".

CONTENT:
{text[:6000]}

YOUR ANSWER (topic path only):"""

    raw = call_gemini(prompt).strip()

    # Parse the response
    main, sub, subsub = parse_topic_path(raw)

    # Validate and fuzzy-match the main topic
    matched_main = None
    for t in VALID_TOPICS:
        if t.lower() in main.lower() or main.lower() in t.lower():
            matched_main = t
            break
    if not matched_main:
        matched_main = "Current Affairs"

    # Validate subtopic
    matched_sub = find_best_subtopic(matched_main, sub) if sub else ""
    if not matched_sub:
        subtopics = list(TOPIC_HIERARCHY.get(matched_main, {}).keys())
        matched_sub = subtopics[0] if subtopics else ""

    # Validate sub-subtopic
    matched_subsub = find_best_sub_subtopic(matched_main, matched_sub, subsub) if subsub else ""
    if not matched_subsub:
        subs = TOPIC_HIERARCHY.get(matched_main, {}).get(matched_sub, [])
        matched_subsub = subs[0] if subs else ""

    return (matched_main, matched_sub, matched_subsub)
