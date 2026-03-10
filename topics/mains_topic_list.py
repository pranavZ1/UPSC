# topics/mains_topic_list.py
# Complete topic hierarchy from Main topic.txt (GS1–GS4)

import re as _re

MAINS_TOPIC_HIERARCHY = {
    # ─── GS1: History, Culture, Society, Geography ────────────
    "Indian Art & Culture": {
        "Architecture": [
            "Temple architecture: Nagara / Dravida / Vesara",
            "Buddhist/Jain: stupas, viharas, chaityas; rock-cut architecture",
            "Indo-Islamic: arches, domes, minarets, calligraphy, pietra dura",
            "Regional/period styles: Chola, Hoysala, Vijayanagara, Mughal, Sultanate",
            "Colonial & modern: Indo-Saracenic, public buildings",
        ],
        "Sculpture & Painting": [
            "Mauryan, Gupta, Chola sculpture characteristics",
            "Schools of painting: Mughal, Rajput, Pahari, Deccan",
            "Modern art movements",
        ],
        "Performing Arts": [
            "Classical dances: origin, themes, key features, instruments",
            "Music: Hindustani vs Carnatic, gharanas, instruments",
            "Theatre, puppetry, folk traditions",
        ],
        "Literature & Philosophy": [
            "Vedic literature, epics, Sangam literature",
            "Bhakti & Sufi traditions: major saints, messages, social impact",
            "Schools of philosophy: Nyaya, Vedanta, Buddhism/Jainism basics",
        ],
    },
    "History": {
        "Modern India (1750s-1947)": [
            "British expansion: wars, annexations, policies",
            "Administrative systems: civil services, police, judiciary",
            "Economic impact: deindustrialization, land revenue systems",
            "Socio-religious reforms: Brahmo, Arya Samaj, Aligarh, others",
            "Peasant/tribal movements",
        ],
        "Freedom Struggle": [
            "Moderate vs extremist strategies",
            "Gandhian movements: NCM, CDM, Quit India",
            "Constitutional developments: 1909/1919/1935 Acts, Cabinet Mission",
            "Revolutionaries, INA, role of press, students, women",
        ],
        "Post-independence consolidation": [
            "Integration of princely states, reorganization of states",
            "Language, regionalism, national unity challenges",
            "Early policy choices: planning, institutions, political consolidation",
        ],
        "World History (18th century onwards)": [
            "Enlightenment, industrial revolution, capitalism/socialism",
            "American/French/Russian revolutions",
            "Colonialism & decolonization",
            "World Wars, Cold War, formation of UN system",
            "Globalization, new world order, regional conflicts",
        ],
    },
    "Indian Society": {
        "Social Structure": [
            "Unity in diversity, pluralism, syncretism",
            "Social institutions: family, marriage, kinship, caste dynamics",
            "Religion, communalism, secularism",
            "Regionalism, linguistic identity, ethnicity",
        ],
        "Social Issues": [
            "Women: empowerment, workforce participation, safety, laws",
            "Population: demographic dividend, aging, migration",
            "Urbanization: slums, housing, sanitation, transport",
            "Poverty, inequality, social mobility",
            "Globalization impacts: culture, economy, social change",
            "Vulnerable groups: tribes, minorities, elderly, disabled",
        ],
    },
    "Geography": {
        "Physical Geography": [
            "Geomorphology: plate tectonics, earthquakes, volcanoes, landforms",
            "Climatology: monsoon, jet streams, ENSO/IOD, cyclones",
            "Oceanography: currents, upwelling, coral reefs",
        ],
        "Indian Geography": [
            "Physiography: Himalayas, plains, plateau, coastal plains, islands",
            "Rivers & basins: Himalayan vs Peninsular, floods/droughts",
            "Soils & natural vegetation; agro-climatic regions",
            "Minerals & energy distribution; water resources",
        ],
        "Human & Economic Geography": [
            "Population distribution, migration patterns",
            "Agriculture geography: cropping patterns, irrigation",
            "Industrial location factors, corridors, SEZs",
            "Transport networks, ports, logistics geography",
        ],
        "Geophysical phenomena": [
            "Earthquakes, tsunamis, landslides, avalanches, cloudbursts",
            "Vulnerability mapping + mitigation frameworks",
        ],
    },

    # ─── GS2: Polity, Governance, Social Justice, IR ──────────
    "Constitution & Polity": {
        "Constitution framework": [
            "Preamble, basic structure, amendment process",
            "FR, DPSP, Fundamental Duties: conflicts, balance",
        ],
        "Parliament & State Legislatures": [
            "Law-making process, bill types, budget process",
            "Parliamentary control: questions, motions, committees",
            "Anti-defection, privileges, disruptions and reforms",
        ],
        "Executive": [
            "President/Governor: powers, ordinances, discretionary space",
            "PM/CM + Council of Ministers: responsibility, role of cabinet",
            "Bureaucracy: neutrality vs accountability; reforms",
        ],
        "Judiciary": [
            "Judicial review, PIL, judicial activism vs overreach",
            "Tribunals, pendency, access to justice",
        ],
        "Federalism": [
            "Centre-State relations (legislative/executive/financial)",
            "Inter-state disputes: water, boundaries; cooperative federalism",
            "Finance Commission / GST Council",
        ],
        "Constitutional/Statutory Bodies": [
            "ECI, CAG, UPSC, FC: role, independence issues",
            "CBI, NHRC, CIC, Lokpal: mandate + limitations",
        ],
    },
    "Governance": {
        "Good Governance": [
            "Transparency, accountability, efficiency, participation",
            "RTI, social audit, citizen charter, grievance redressal",
            "E-governance: models, digital divide, privacy",
        ],
        "Civil Society & Development": [
            "Role of NGOs/SHGs/pressure groups",
            "Policy making cycle: design to evaluation",
            "Local governance: devolution, funds-functions-functionaries",
        ],
    },
    "Social Justice": {
        "Health & Education": [
            "Public health system, financing, HR, access, NCD burden",
            "Education: learning outcomes, teacher quality, digital education",
        ],
        "Welfare & Inclusion": [
            "Hunger, malnutrition, PDS, nutrition missions",
            "Poverty alleviation, inclusion, social security",
            "Welfare schemes: targeting vs universalization, leakages, DBT",
            "Vulnerable sections: SC/ST/OBC/minorities/women/children",
        ],
    },
    "International Relations": {
        "India's Neighbourhood": [
            "Security, connectivity, water/border issues",
        ],
        "Major Powers & Groupings": [
            "US, Russia, EU, China: broad themes",
            "UN, G20, BRICS, SCO, QUAD, ASEAN: purpose + India interest",
        ],
        "Global Issues": [
            "India's diaspora, soft power, development partnerships",
            "Global commons: climate, oceans, space, cyber norms",
            "Trade & tech diplomacy: supply chains, FTA logic",
        ],
    },

    # ─── GS3: Economy, Agriculture, S&T, Environment, Security, DM ──
    "Economy": {
        "Macroeconomics": [
            "Growth vs development; inclusion; inequality",
            "Fiscal policy: deficits, debt, subsidies, budgeting",
            "Monetary policy: inflation targeting, RBI tools",
        ],
        "Banking & Finance": [
            "NPAs, financial inclusion, NBFCs",
            "External sector: BoP, forex, exchange rate, trade policy",
        ],
        "Infrastructure & Growth": [
            "Infrastructure: power, roads, rail, ports, digital infra",
            "Investment: PPP models, regulatory certainty, ease of business",
            "Employment: jobless growth, skilling, informal sector",
            "MSMEs, startups, manufacturing competitiveness",
        ],
    },
    "Agriculture": {
        "Farm Economy": [
            "Cropping patterns, diversification, allied activities",
            "Irrigation, watershed, micro-irrigation, water-use efficiency",
            "Marketing: APMC, MSP/procurement, supply chains, e-NAM",
        ],
        "Farm Issues": [
            "Storage/cold chain, food wastage, price stability",
            "Agri credit, insurance, farm distress",
            "Land reforms, tenancy, fragmentation",
            "Food processing: value addition, logistics, standards",
            "Technology in agriculture: precision farming, digital advisory",
        ],
    },
    "Science & Technology": {
        "R&D & Innovation": [
            "R&D ecosystem: institutions, funding, indigenization",
            "IPR: patents basics, innovation policy themes",
        ],
        "Emerging Technology": [
            "IT: AI, data, cybersecurity, emerging tech",
            "Space tech and applications",
            "Biotech: vaccines, GM crops, bio-safety",
        ],
    },
    "Environment": {
        "Biodiversity & Conservation": [
            "Ecosystems, biodiversity conservation strategies",
            "Protected areas, wildlife protection challenges",
        ],
        "Pollution & Climate": [
            "Pollution: air, water, soil; waste management",
            "Climate change: mitigation/adaptation, carbon markets, NDC",
            "Environmental governance: EIA, compliance challenges",
        ],
    },
    "Internal Security": {
        "Threats": [
            "Terrorism: causes, financing, propaganda, counter-measures",
            "Insurgency, extremism, border issues",
            "Coastal security, maritime threats",
        ],
        "Cyber & Organized Crime": [
            "Cybersecurity: cybercrime, critical infrastructure protection",
            "Organized crime: money laundering, drugs, trafficking",
            "Security forces & agencies: coordination and reform",
        ],
    },
    "Disaster Management": {
        "DM Framework": [
            "Disaster cycle: mitigation, preparedness, response, recovery",
            "Risk reduction: resilient infrastructure, early warning systems",
            "Community-based DM; role of local bodies",
            "Urban floods, heatwaves, cyclones, earthquakes",
        ],
    },

    # ─── GS4: Ethics ─────────────────────────────────────────────
    "Ethics": {
        "Ethics Foundations": [
            "Ethics vs morality; values; human conduct",
            "Determinants of ethics: family, society, education, institutions",
            "Ethical issues in public life: nepotism, favoritism, conflict of interest",
        ],
        "Attitude & Aptitude": [
            "Formation of attitude, components, moral attitude",
            "Integrity, impartiality, objectivity",
            "Empathy, compassion, tolerance",
            "Emotional Intelligence: components and application",
        ],
        "Probity in Governance": [
            "Concept of probity; corruption types",
            "Transparency & accountability mechanisms",
            "Codes of ethics vs codes of conduct",
            "Work culture, service delivery ethics",
        ],
        "Thinkers & Case Studies": [
            "Indian + Western thinkers: core idea + application",
            "Ethical dilemmas, stakeholder analysis, decision frameworks",
        ],
    },
}

# Flat list for LLM classification
MAINS_FLAT_TOPIC_LIST = []
for main_topic, subtopics in MAINS_TOPIC_HIERARCHY.items():
    for subtopic, sub_subtopics in subtopics.items():
        for sst in sub_subtopics:
            MAINS_FLAT_TOPIC_LIST.append(f"{main_topic} | {subtopic} | {sst}")

MAINS_MAIN_TOPICS = list(MAINS_TOPIC_HIERARCHY.keys())

# Reverse lookup
MAINS_SUBTOPIC_TO_MAIN = {}
for _main, _subs in MAINS_TOPIC_HIERARCHY.items():
    for _sub in _subs:
        MAINS_SUBTOPIC_TO_MAIN[_sub] = _main


# ─── Helper functions ─────────────────────────────────────────────────────

def get_mains_subtopics(main_topic: str) -> list[str]:
    return list(MAINS_TOPIC_HIERARCHY.get(main_topic, {}).keys())


def get_mains_sub_subtopics(main_topic: str, subtopic: str) -> list[str]:
    return MAINS_TOPIC_HIERARCHY.get(main_topic, {}).get(subtopic, [])


def parse_mains_topic_path(path_str: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in path_str.split("|")]
    main = parts[0] if len(parts) > 0 else "Economy"
    sub = parts[1] if len(parts) > 1 else ""
    subsub = parts[2] if len(parts) > 2 else ""
    return (main, sub, subsub)


def _keyword_overlap(a: str, b: str) -> int:
    stop = {"in", "of", "the", "a", "an", "and", "or", "for", "to", "vs", "&"}
    wa = set(_re.findall(r'\w+', a.lower())) - stop
    wb = set(_re.findall(r'\w+', b.lower())) - stop
    return len(wa & wb)


def find_best_mains_subtopic(main_topic: str, candidate: str) -> str:
    subtopics = get_mains_subtopics(main_topic)
    if not subtopics:
        return ""
    cl = candidate.lower().strip()
    for s in subtopics:
        if s.lower() == cl:
            return s
    for s in subtopics:
        if cl in s.lower() or s.lower() in cl:
            return s
    best, best_score = subtopics[0], 0
    for s in subtopics:
        score = _keyword_overlap(candidate, s)
        if score > best_score:
            best_score = score
            best = s
    return best


def find_best_mains_sub_subtopic(main_topic: str, subtopic: str, candidate: str) -> str:
    subs = get_mains_sub_subtopics(main_topic, subtopic)
    if not subs:
        return ""
    cl = candidate.lower().strip()
    for ss in subs:
        if ss.lower() == cl:
            return ss
    for ss in subs:
        if cl in ss.lower() or ss.lower() in cl:
            return ss
    best, best_score = subs[0], 0
    for ss in subs:
        score = _keyword_overlap(candidate, ss)
        if score > best_score:
            best_score = score
            best = ss
    return best
