# topics/topic_list.py
# Complete topic hierarchy from Prelims topics.txt

import re as _re

TOPIC_HIERARCHY = {
    "Current Affairs": {
        "Polity & Governance in News": [
            "Bills/Acts/Amendments: what changed, why, key features",
            "Supreme Court/High Court judgments: issue, impact",
            "Constitutional/Statutory bodies in news (roles, powers)",
        ],
        "Economy in News": [
            "Budget/Economic Survey themes",
            "RBI policy: repo, inflation, liquidity tools",
            "Banking/markets: NPAs, digital payments, bonds",
            "Schemes: target group, funding pattern, implementation",
        ],
        "International Relations": [
            "Neighbourhood: major disputes, connectivity projects",
            "Groupings: QUAD/BRICS/G20/SCO/ASEAN",
            "India's agreements: defence, trade, climate, tech",
        ],
        "Science/Tech in News": [
            "Space missions, new tech terms (AI, quantum, semiconductors)",
            "Health: outbreaks, new vaccines/drugs",
        ],
        "Environment in News": [
            "COP outcomes, IUCN/CITES updates",
            "Species in news; protected areas in news",
        ],
        "Reports/Indices": [
            "Who releases, what it measures, India rank",
        ],
        "People/Places/Events": [
            "Awards, books, obituaries, important anniversaries",
        ],
    },
    "History": {
        "Ancient India": [
            "Prehistory & Indus Valley",
            "Vedic Age",
            "Mahajanapadas & Religious Movements",
            "Mauryan Period",
            "Post-Mauryan Period",
            "Gupta & Post-Gupta Period",
            "South India (Sangam Age)",
            "Ancient Art & Culture",
        ],
        "Medieval India": [
            "Early Medieval (Cholas)",
            "Delhi Sultanate",
            "Vijayanagara & Bahmani",
            "Mughal Period",
            "Bhakti & Sufi Movements",
        ],
        "Modern India (1700s-1947)": [
            "Advent of Europeans",
            "British Expansion",
            "Administration & Policies",
            "Land Revenue Systems",
            "Socio-Religious Reform",
            "Revolt of 1857",
            "National Movement",
            "Gandhian Phase",
            "Constitutional Development",
        ],
    },
    "Geography": {
        "Physical Geography": [
            "Earth Fundamentals",
            "Geomorphology",
            "Climatology",
            "Oceanography",
        ],
        "Indian Geography": [
            "Physiographic Divisions",
            "Drainage",
            "Soils",
            "Climate & Agriculture",
            "Minerals & Energy",
            "Disasters",
        ],
        "Human & Economic Geography": [
            "Population & Demography",
            "Migration & Urbanization",
            "Industry & Transport",
        ],
        "Mapping": [
            "India: passes, straits, gulfs, rivers, dams, parks",
            "World: countries, capitals, seas, straits, choke points",
            "Hotspots: conflict zones, key ports, mountains, rivers",
        ],
    },
    "Polity & Governance": {
        "Constitution Basics": [
            "Making of Constitution",
            "Preamble",
            "Schedules",
            "Amendments",
        ],
        "Rights & Principles": [
            "Fundamental Rights",
            "DPSP",
            "Fundamental Duties",
        ],
        "Union Government": [
            "President/VP",
            "PM & Council of Ministers",
            "Parliament",
            "Parliamentary Committees",
        ],
        "State Government": [
            "Governor",
            "CM & Council, State Legislature",
        ],
        "Federalism & Local Bodies": [
            "Centre-State Relations",
            "Panchayati Raj (73rd Amendment)",
            "Municipalities (74th Amendment)",
        ],
        "Judiciary": [
            "SC/HC/Subordinate Courts",
            "Judicial Review, PIL, Tribunals",
        ],
        "Constitutional & Statutory Bodies": [
            "ECI, CAG, UPSC, Finance Commission, GST Council",
            "CBI, NIA, NHRC, CIC",
        ],
        "Governance (Issue-Based)": [
            "Transparency: RTI, social audit, e-governance",
            "Accountability: citizen charter, grievance redressal",
            "Welfare delivery: DBT, targeting, leakages",
            "Pressure groups, NGOs, SHGs, cooperatives",
        ],
    },
    "Economy": {
        "Basic Concepts": [
            "GDP/GNP, real vs nominal, per capita",
            "Inflation: CPI/WPI, demand vs cost-push",
            "Unemployment types, labour force terms",
        ],
        "Money & Banking": [
            "RBI functions, monetary policy tools",
            "Repo/reverse repo, CRR/SLR, OMO",
            "Banking: NPAs, Basel norms, priority sector lending",
            "Digital payments: UPI, wallets, CBDC",
        ],
        "Public Finance": [
            "Budget: revenue vs capital, fiscal deficit",
            "Taxation: direct/indirect, GST basics",
            "FRBM, public debt, subsidies",
        ],
        "External Sector": [
            "BoP: current vs capital account",
            "Forex reserves, exchange rate",
            "Trade policy: tariffs, FTAs",
            "FDI vs FPI",
        ],
        "Agriculture": [
            "MSP, procurement, PDS",
            "APMC, e-NAM, agri marketing",
            "Irrigation, crop insurance",
            "Allied sectors: dairy, fisheries",
        ],
        "Industry & Services": [
            "MSME, startups, manufacturing",
            "Infrastructure: roads/ports/power/logistics",
            "Services: IT, tourism, finance",
        ],
        "Inclusive Growth & Development": [
            "Poverty measurement, HDI indicators",
            "Financial inclusion: Jan Dhan, microfinance",
            "Social sector: health/education spending",
        ],
    },
    "Science & Technology": {
        "Biology": [
            "Human systems, immunity, vaccines",
            "Genetics: DNA/RNA, GM crops, CRISPR",
        ],
        "Health": [
            "Communicable vs non-communicable diseases",
            "Antimicrobial resistance (AMR)",
        ],
        "Space": [
            "Orbits, satellite types, launch vehicles",
        ],
        "IT & Emerging Tech": [
            "AI/ML basics, blockchain, quantum",
            "Cybersecurity: phishing, encryption, CERT-In",
        ],
        "Energy": [
            "Nuclear basics, renewables, hydrogen",
        ],
        "Defence Tech": [
            "Missiles, drones, radars",
        ],
    },
    "Environment & Ecology": {
        "Ecology Basics": [
            "Ecosystem structure, trophic levels",
            "Biomes, ecological pyramids",
            "Biodiversity: levels, hotspots, endemism",
            "Succession, adaptation",
        ],
        "Conservation": [
            "Protected areas: NP/WLS/Conservation/Community reserve",
            "Biosphere reserves, Ramsar sites",
            "Wildlife laws & institutions",
        ],
        "Climate Change": [
            "Greenhouse gases, carbon cycle",
            "Mitigation vs adaptation",
            "Carbon markets, NDCs",
            "UNFCCC, Paris Agreement",
        ],
        "Pollution & Waste": [
            "Air: AQI, PM2.5/PM10",
            "Water: eutrophication, groundwater issues",
            "Solid waste, e-waste, plastic rules",
        ],
        "Environmental Geography": [
            "Forest types in India",
            "Coastal regulation basics",
            "Disaster risk reduction concepts",
        ],
    },
    "Art & Culture": {
        "Architecture": [
            "Temple styles: Nagara/Dravida/Vesara",
            "Indo-Islamic: arches, domes, minarets",
            "Buddhist architecture: stupas, viharas, chaityas",
        ],
        "Sculpture & Painting": [
            "Mauryan, Gupta, Chola sculpture",
            "Painting: Mughal, Rajput, Pahari",
            "Modern: Bengal school",
        ],
        "Performing Arts": [
            "Classical dances: features, states",
            "Music: Hindustani vs Carnatic",
            "Folk arts",
        ],
        "Literature & Philosophy": [
            "Vedas/Upanishads, Epics",
            "Bhakti/Sufi literature",
            "Languages in medieval/modern",
        ],
        "Heritage & Culture in News": [
            "UNESCO sites in India",
            "GI tags, festivals in news",
        ],
    },
}

# Flat list of all topic paths for LLM classification
FLAT_TOPIC_LIST = []
for main_topic, subtopics in TOPIC_HIERARCHY.items():
    for subtopic, sub_subtopics in subtopics.items():
        for sst in sub_subtopics:
            FLAT_TOPIC_LIST.append(f"{main_topic} | {subtopic} | {sst}")

# Main topic names
MAIN_TOPICS = list(TOPIC_HIERARCHY.keys())

# ─── Reverse lookup: subtopic name → main topic ──────────────────────────
SUBTOPIC_TO_MAIN = {}
for _main, _subs in TOPIC_HIERARCHY.items():
    for _sub in _subs:
        SUBTOPIC_TO_MAIN[_sub] = _main


# ─── Helper functions ─────────────────────────────────────────────────────

def get_subtopics(main_topic: str) -> list[str]:
    """Return list of subtopic names for a main topic."""
    return list(TOPIC_HIERARCHY.get(main_topic, {}).keys())


def get_sub_subtopics(main_topic: str, subtopic: str) -> list[str]:
    """Return list of sub-subtopic names for a main topic + subtopic."""
    return TOPIC_HIERARCHY.get(main_topic, {}).get(subtopic, [])


def parse_topic_path(path_str: str) -> tuple[str, str, str]:
    """
    Parse a classification string like
      'Current Affairs | Economy in News | Budget/Economic Survey themes'
    into (main_topic, subtopic, sub_subtopic).
    """
    parts = [p.strip() for p in path_str.split("|")]
    main = parts[0] if len(parts) > 0 else "Current Affairs"
    sub = parts[1] if len(parts) > 1 else ""
    subsub = parts[2] if len(parts) > 2 else ""
    return (main, sub, subsub)


def _keyword_overlap_score(a: str, b: str) -> int:
    """Count overlapping keywords between two strings (ignoring stop words)."""
    stop = {"in", "of", "the", "a", "an", "and", "or", "for", "to", "vs", "&"}
    words_a = set(_re.findall(r'\w+', a.lower())) - stop
    words_b = set(_re.findall(r'\w+', b.lower())) - stop
    return len(words_a & words_b)


def find_best_subtopic(main_topic: str, candidate: str) -> str:
    """Fuzzy-match a candidate subtopic name to the hierarchy. Returns best match or ''."""
    subtopics = get_subtopics(main_topic)
    if not subtopics:
        return ""
    candidate_lower = candidate.lower().strip()

    # 1) Exact match
    for s in subtopics:
        if s.lower() == candidate_lower:
            return s

    # 2) Substring match
    for s in subtopics:
        if candidate_lower in s.lower() or s.lower() in candidate_lower:
            return s

    # 3) Keyword overlap
    best, best_score = subtopics[0], 0
    for s in subtopics:
        score = _keyword_overlap_score(candidate, s)
        if score > best_score:
            best_score = score
            best = s
    return best


def find_best_sub_subtopic(main_topic: str, subtopic: str, candidate: str) -> str:
    """Fuzzy-match a candidate sub-subtopic name. Returns best match or ''."""
    sub_subs = get_sub_subtopics(main_topic, subtopic)
    if not sub_subs:
        return ""
    candidate_lower = candidate.lower().strip()

    # 1) Exact match
    for ss in sub_subs:
        if ss.lower() == candidate_lower:
            return ss

    # 2) Substring match
    for ss in sub_subs:
        if candidate_lower in ss.lower() or ss.lower() in candidate_lower:
            return ss

    # 3) Keyword overlap
    best, best_score = sub_subs[0], 0
    for ss in sub_subs:
        score = _keyword_overlap_score(candidate, ss)
        if score > best_score:
            best_score = score
            best = ss
    return best
