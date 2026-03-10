# news/fetcher.py — Fetch UPSC-relevant news from RSS feeds
#
# Sources: The Hindu, PIB, Indian Express, Economic Times, Google News
# Focus: Current affairs useful for UPSC Prelims & Mains preparation

import feedparser
import hashlib
import json
import re
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import BASE_DIR

# ── Cache directory ───────────────────────────────────────────────────────
NEWS_CACHE_DIR = BASE_DIR / "news_cache"
NEWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── RSS Feed Sources ──────────────────────────────────────────────────────
RSS_FEEDS = {
    # The Hindu
    "hindu_national": "https://www.thehindu.com/news/national/feeder/default.rss",
    "hindu_international": "https://www.thehindu.com/news/international/feeder/default.rss",
    "hindu_economy": "https://www.thehindu.com/business/Economy/feeder/default.rss",
    "hindu_business": "https://www.thehindu.com/business/feeder/default.rss",
    "hindu_science": "https://www.thehindu.com/sci-tech/science/feeder/default.rss",
    "hindu_technology": "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
    "hindu_sport": "https://www.thehindu.com/sport/feeder/default.rss",
    "hindu_environment": "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss",

    # Indian Express
    "ie_india": "https://indianexpress.com/section/india/feed/",
    "ie_world": "https://indianexpress.com/section/world/feed/",
    "ie_business": "https://indianexpress.com/section/business/feed/",
    "ie_technology": "https://indianexpress.com/section/technology/feed/",
    "ie_sports": "https://indianexpress.com/section/sports/feed/",

    # Economic Times
    "et_markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "et_economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "et_politics": "https://economictimes.indiatimes.com/news/politics-and-nation/rssfeeds/1052732854.cms",
    "et_tech": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "et_infra": "https://economictimes.indiatimes.com/news/economy/infrastructure/rssfeeds/20997916.cms",
    "et_defence": "https://economictimes.indiatimes.com/news/defence/rssfeeds/68aborede.cms",

    # PIB — Government press releases (very UPSC-relevant)
    "pib": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",

    # Google News — India
    "google_india": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNREp0Y0RjU0FtVnVLQUFQAQ?hl=en-IN&gl=IN&ceid=IN:en",
    "google_world": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "google_business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "google_tech": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "google_sports": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
}

# ── UPSC-focused category mapping ─────────────────────────────────────────
FEED_CATEGORY_MAP = {
    # International Relations
    "hindu_international": "international",
    "ie_world": "international",
    "google_world": "international",

    # Polity & Governance
    "hindu_national": "polity",
    "ie_india": "polity",
    "et_politics": "polity",
    "pib": "polity",
    "google_india": "polity",

    # Economy & Trade
    "hindu_economy": "economy",
    "hindu_business": "economy",
    "ie_business": "economy",
    "et_economy": "economy",
    "et_markets": "economy",
    "google_business": "economy",

    # Science & Technology
    "hindu_science": "science_tech",
    "hindu_technology": "science_tech",
    "ie_technology": "science_tech",
    "et_tech": "science_tech",
    "google_tech": "science_tech",

    # Environment & Ecology
    "hindu_environment": "environment",

    # Defence & Security
    "et_defence": "defence",

    # Infrastructure
    "et_infra": "infrastructure",

    # Sports
    "hindu_sport": "sports",
    "ie_sports": "sports",
    "google_sports": "sports",
}

# Source display names
SOURCE_MAP = {
    "hindu": "The Hindu",
    "ie": "Indian Express",
    "et": "Economic Times",
    "pib": "PIB",
    "google": "Google News",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ── Banner / Breaking news relevance filters ──────────────────────────────
# Only truly important / breaking / UPSC-relevant stories become banners.
# Exclude cheap politics, entertainment, gossip, movie/trailer/celebrity.

BANNER_EXCLUDE_KEYWORDS = [
    "trailer", "movie", "film", "bollywood", "hollywood", "celebrity",
    "gossip", "bigg boss", "reality show", "song launch", "web series",
    "actress", "selfie", "wedding", "divorce", "affair", "viral video",
    "meme", "instagram", "tiktok", "reel", "mukesh khanna",
    "horoscope", "zodiac", "astrology", "cricket score", "ipl auction",
    "match preview", "playing xi", "dream11",
]

BANNER_BOOST_KEYWORDS = [
    # Major international events
    "summit", "treaty", "war", "ceasefire", "sanctions", "united nations",
    "nato", "g20", "g7", "brics", "who", "imf", "world bank", "icj",
    "refugee", "genocide", "nuclear", "missile",
    # National significance
    "supreme court", "parliament", "lok sabha", "rajya sabha",
    "constitution", "amendment", "bill passed", "ordinance", "president",
    "prime minister", "cabinet", "election commission", "governor",
    "central government", "union budget", "fiscal deficit",
    # Economy / policy
    "rbi", "gdp", "inflation", "trade deficit", "fdi", "monetary policy",
    "interest rate", "rupee", "forex", "stock market crash",
    # Science / environment
    "isro", "nasa", "satellite", "climate change", "cyclone", "earthquake",
    "flood", "drought", "emission", "paris agreement", "biodiversity",
    "endangered", "conservation", "renewable", "solar", "carbon",
    # Defence / security
    "defence", "army", "navy", "air force", "border", "terrorism",
    "ceasefire violation", "surgical strike", "drdo",
    # Governance
    "scheme launch", "digital india", "make in india", "niti aayog",
    "smart city", "aadhaar", "upi", "disinvestment",
]

# ── IST timezone (UTC+5:30) ───────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist():
    """Current time in IST."""
    return datetime.now(IST)


def _today_str():
    return _now_ist().strftime("%Y-%m-%d")


def _cache_path():
    return NEWS_CACHE_DIR / f"news_{_today_str()}.json"


def _article_id(title: str, link: str) -> str:
    return hashlib.md5(f"{title}:{link}".encode()).hexdigest()[:12]


def _get_source(feed_key: str) -> str:
    prefix = feed_key.split("_")[0]
    return SOURCE_MAP.get(prefix, prefix.upper())


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)[:300]


def _parse_pub_date(entry) -> str:
    """Extract publication date string from feed entry, converted to IST."""
    for attr in ("published_parsed", "updated_parsed"):
        ts = getattr(entry, attr, None)
        if ts:
            try:
                # RSS timestamps are typically UTC
                dt_utc = datetime(*ts[:6], tzinfo=timezone.utc)
                dt_ist = dt_utc.astimezone(IST)
                return dt_ist.strftime("%d %b %Y, %I:%M %p IST")
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            return val[:25]
    return ""


def _is_recent(entry, hours=36) -> bool:
    """Check if entry is within the last N hours (IST-aware)."""
    for attr in ("published_parsed", "updated_parsed"):
        ts = getattr(entry, attr, None)
        if ts:
            try:
                dt_utc = datetime(*ts[:6], tzinfo=timezone.utc)
                return dt_utc > _now_ist() - timedelta(hours=hours)
            except Exception:
                pass
    return True  # If we can't parse date, include it


def _fetch_single_feed(feed_key: str, url: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        category = FEED_CATEGORY_MAP.get(feed_key, "general")
        source = _get_source(feed_key)

        for entry in feed.entries[:15]:  # Max 15 per feed
            if not _is_recent(entry):
                continue

            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            # Get summary/description
            summary = ""
            for attr in ("summary", "description", "content"):
                val = getattr(entry, attr, None)
                if val:
                    if isinstance(val, list):
                        val = val[0].get("value", "") if val else ""
                    summary = _clean_html(str(val))
                    break

            # Get image
            image = ""
            if hasattr(entry, "media_content") and entry.media_content:
                image = entry.media_content[0].get("url", "")
            elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                image = entry.media_thumbnail[0].get("url", "")
            # Try og:image from enclosures
            if not image and hasattr(entry, "enclosures") and entry.enclosures:
                for enc in entry.enclosures:
                    if "image" in enc.get("type", ""):
                        image = enc.get("href", "")
                        break

            articles.append({
                "id": _article_id(title, link),
                "title": title,
                "summary": summary,
                "link": link,
                "source": source,
                "category": category,
                "image": image,
                "published": _parse_pub_date(entry),
                "feed_key": feed_key,
            })
    except Exception as e:
        print(f"[NEWS] Error fetching {feed_key}: {e}")

    return articles


def fetch_all_news(force_refresh=False) -> dict:
    """
    Fetch news from all RSS feeds, deduplicate, categorize,
    and pick high-impact banners for UPSC aspirants.

    Returns: {
        "date": "2026-03-05",
        "fetched_at": "...",
        "banners": [...],   # high-impact breaking/UPSC-relevant only
        "categories": {
            "international": [...],
            "polity": [...],
            "economy": [...],
            "science_tech": [...],
            "environment": [...],
            "defence": [...],
            "infrastructure": [...],
            "sports": [...]
        }
    }
    """
    cache = _cache_path()

    # Return cached if fresh (less than 2 hours old)
    if not force_refresh and cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(data.get("fetched_at", "2000-01-01"))
            if _now_ist() - fetched < timedelta(hours=2):
                return data
        except (json.JSONDecodeError, ValueError, OSError):
            pass

    # Fetch all feeds in parallel
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_single_feed, key, url): key
            for key, url in RSS_FEEDS.items()
        }
        for future in as_completed(futures):
            try:
                articles = future.result()
                all_articles.extend(articles)
            except Exception as e:
                print(f"[NEWS] Feed error: {e}")

    # Deduplicate by similar titles
    seen_titles = {}
    unique = []
    for art in all_articles:
        norm = re.sub(r'[^a-z0-9\s]', '', art["title"].lower())
        norm_short = norm[:60]
        if norm_short not in seen_titles:
            seen_titles[norm_short] = True
            unique.append(art)

    # Categorize
    categories = {
        "international": [],
        "polity": [],
        "economy": [],
        "science_tech": [],
        "environment": [],
        "defence": [],
        "infrastructure": [],
        "sports": [],
    }

    for art in unique:
        cat = art["category"]
        if cat in categories:
            categories[cat].append(art)
        else:
            # Fallback: try to classify by keywords
            categories.setdefault("polity", []).append(art)

    # Sort each category by published date (newest first)
    for cat in categories:
        categories[cat].sort(key=lambda x: x.get("published", ""), reverse=True)

    # ── Pick banners: only high-impact UPSC-relevant breaking news ─────
    banners = _pick_banners(unique)

    # Limit each category
    limits = {
        "international": 10,
        "polity": 10,
        "economy": 8,
        "science_tech": 8,
        "environment": 6,
        "defence": 6,
        "infrastructure": 6,
        "sports": 5,
    }
    for cat, limit in limits.items():
        categories[cat] = categories[cat][:limit]

    result = {
        "date": _today_str(),
        "fetched_at": _now_ist().isoformat(),
        "banners": banners,
        "categories": categories,
    }

    # Cache
    cache.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return result


def _banner_score(article: dict) -> int:
    """Score an article for banner worthiness. Higher = more important."""
    title_lower = (article["title"] + " " + article.get("summary", "")).lower()

    # Exclude tabloid / entertainment / cheap news
    for kw in BANNER_EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return -100

    score = 0

    # Boost for UPSC-relevant keywords
    for kw in BANNER_BOOST_KEYWORDS:
        if kw in title_lower:
            score += 3

    # Boost international & polity stories
    cat = article.get("category", "")
    if cat == "international":
        score += 5
    elif cat in ("polity", "economy", "defence", "environment"):
        score += 4
    elif cat == "science_tech":
        score += 3
    elif cat == "infrastructure":
        score += 2
    # Sports get no boost for banners

    # Prefer articles with images (look better in carousel)
    if article.get("image"):
        score += 2

    # Prefer authoritative sources
    src = article.get("source", "")
    if src in ("The Hindu", "PIB"):
        score += 2
    elif src == "Indian Express":
        score += 1

    return score


def _pick_banners(articles: list[dict], max_banners: int = 8) -> list[dict]:
    """Pick the top breaking/UPSC-relevant articles for the banner carousel."""
    scored = []
    for art in articles:
        s = _banner_score(art)
        if s > 0:
            scored.append((s, art))

    # Sort by score descending, then by published date
    scored.sort(key=lambda x: (x[0], x[1].get("published", "")), reverse=True)

    # Take top N, ensuring category diversity
    banners = []
    cat_counts = {}
    for _, art in scored:
        cat = art.get("category", "general")
        if cat_counts.get(cat, 0) >= 3:  # max 3 per category in banners
            continue
        banners.append(art)
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if len(banners) >= max_banners:
            break

    return banners


def fetch_article_content(url: str) -> str:
    """Fetch the full text content of an article from its URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Try common article selectors
        article_selectors = [
            "article",
            ".article-body",
            ".article__content",
            ".story-element",
            ".full-details",
            ".article_content",
            "[itemprop='articleBody']",
            ".paywall",
            ".content-area",
            ".story_details",
            "#article-body",
            ".post-content",
            ".entry-content",
            "main",
        ]

        text = ""
        for selector in article_selectors:
            el = soup.select_one(selector)
            if el:
                paragraphs = el.find_all("p")
                if paragraphs:
                    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                    if len(text) > 200:
                        break

        # Fallback: all paragraphs
        if len(text) < 200:
            paragraphs = soup.find_all("p")
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)

        return text[:5000]  # Cap at 5000 chars
    except Exception as e:
        return f"Could not fetch article content: {e}"
