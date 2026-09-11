"""Create a daily Bible encouragement post from world-news themes."""

import json
import logging
import random
from datetime import date
from pathlib import Path

import feedparser


ROOT = Path(__file__).resolve().parents[2]

VERSES_FILE = ROOT / "content" / "bible" / "verses.json"
STATE_FILE = ROOT / "data" / "state" / "bible_used.json"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("world_bible_agent")


WORLD_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]


KEYWORDS = {
    "conflict": [
        "war",
        "conflict",
        "attack",
        "fighting",
        "missile",
        "ceasefire",
        "troops",
        "battle",
    ],
    "disaster": [
        "earthquake",
        "flood",
        "storm",
        "wildfire",
        "hurricane",
        "disaster",
        "rescue",
        "eruption",
    ],
    "grief": [
        "death",
        "killed",
        "mourning",
        "victims",
        "tragedy",
        "funeral",
        "dead",
    ],
    "injustice": [
        "rights",
        "justice",
        "protest",
        "violence",
        "abuse",
        "discrimination",
        "oppression",
    ],
    "leadership": [
        "president",
        "government",
        "leaders",
        "election",
        "parliament",
        "minister",
        "leader",
    ],
    "hope": [
        "peace",
        "recovery",
        "help",
        "aid",
        "agreement",
        "hope",
        "support",
    ],
    "fear": [
        "warning",
        "threat",
        "crisis",
        "uncertainty",
        "fear",
        "danger",
        "emergency",
    ],
}


THEME_MESSAGES = {
    "conflict": (
        "For everyone affected by conflict and uncertainty, "
        "may this be a reminder to seek peace and protection."
    ),
    "disaster": (
        "Our thoughts and prayers are with communities facing "
        "hardship and loss."
    ),
    "grief": (
        "We remember those who are grieving and pray for comfort "
        "for every affected family."
    ),
    "injustice": (
        "May compassion, justice, and humility guide people "
        "and leaders everywhere."
    ),
    "leadership": (
        "May leaders act with wisdom, justice, and concern "
        "for the people they serve."
    ),
    "hope": (
        "May hope and peace reach people and communities "
        "around the world."
    ),
    "fear": (
        "For anyone feeling afraid or uncertain today, "
        "may these words bring courage."
    ),
    "general": (
        "Whatever today brings, may these words bring faith, "
        "peace, and encouragement."
    ),
}


def load_verses():
    """Load the verified KJV verse library."""

    if not VERSES_FILE.exists():
        raise FileNotFoundError(
            f"Bible verse file not found: {VERSES_FILE}"
        )

    with open(VERSES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    verses = data.get("items", [])

    if not verses:
        raise RuntimeError("Bible verse library is empty")

    return verses


def load_used_references():
    """Load references already used by previous Bible posts."""

    if not STATE_FILE.exists():
        return set()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            values = json.load(file)

        return set(values)

    except Exception as exc:
        logger.warning(
            "Could not read Bible history. Starting safely: %s",
            exc,
        )
        return set()


def save_used_references(references):
    """Save used verse references."""

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(references),
            file,
            indent=2,
        )


def fetch_world_headlines():
    """Fetch short world-news headlines from RSS feeds."""

    headlines = []

    for feed_url in WORLD_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()

                if title:
                    headlines.append(title)

        except Exception as exc:
            logger.warning(
                "World news feed failed: %s",
                exc,
            )

    logger.info(
        "World headlines collected: %d",
        len(headlines),
    )

    return headlines


def detect_theme(headlines):
    """Choose the strongest theme found in the headlines."""

    combined_text = " ".join(headlines).lower()

    scores = {}

    for theme, words in KEYWORDS.items():
        score = 0

        for word in words:
            if word in combined_text:
                score += 1

        scores[theme] = score

    if not scores:
        return "general"

    best_theme = max(
        scores,
        key=scores.get,
    )

    if scores[best_theme] == 0:
        return "general"

    return best_theme


def choose_unused_verse(theme, verses):
    """
    Select a verse without repeating until the full library is used.
    """

    used_references = load_used_references()

    theme_candidates = [
        verse
        for verse in verses
        if theme in verse.get("themes", [])
    ]

    if not theme_candidates:
        theme_candidates = verses

    unused_theme_candidates = [
        verse
        for verse in theme_candidates
        if verse.get("reference") not in used_references
    ]

    if unused_theme_candidates:
        candidates = unused_theme_candidates
    else:
        candidates = [
            verse
            for verse in verses
            if verse.get("reference") not in used_references
        ]

    if not candidates:
        logger.info(
            "All Bible verses have been used. Starting a new cycle."
        )

        used_references = set()
        candidates = theme_candidates or verses

    selected = random.choice(candidates)

    used_references.add(selected["reference"])
    save_used_references(used_references)

    return selected


def build_bible_post(post):
    """
    Build the Bible post.

    The Bible verse comes only from the verified local KJV library.
    World headlines are used only to choose the theme.
    """

    verses = load_verses()
    headlines = fetch_world_headlines()
    theme = detect_theme(headlines)
    verse = choose_unused_verse(theme, verses)

    message = THEME_MESSAGES.get(
        theme,
        THEME_MESSAGES["general"],
    )

    result = dict(post)

    result["slot"] = "bible_world_encouragement"
    result["category"] = "bible_quotes"

    result["content"] = (
        f"{verse['reference']} KJV\n\n"
        f"{verse['text']}\n\n"
        f"{message}"
    )

    result["bible_reference"] = verse["reference"]
    result["world_theme"] = theme
    result["source_headlines_count"] = len(headlines)
    result["date"] = date.today().isoformat()

    logger.info(
        "Bible post prepared: %s | theme: %s",
        verse["reference"],
        theme,
    )

    return result
