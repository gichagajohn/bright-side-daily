"""Create a respectful daily KJV Bible post informed by world headlines."""

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

# Keywords used to classify the day's headlines.
KEYWORDS = {
    "conflict": [
        "war", "conflict", "attack", "fighting", "missile",
        "ceasefire", "troops", "battle", "airstrike", "invasion",
    ],
    "disaster": [
        "earthquake", "flood", "storm", "wildfire", "hurricane",
        "disaster", "rescue", "eruption", "landslide", "drought",
    ],
    "grief": [
        "death", "killed", "mourning", "victims", "tragedy",
        "funeral", "dead", "loss",
    ],
    "injustice": [
        "rights", "justice", "protest", "violence", "abuse",
        "discrimination", "oppression", "corruption",
    ],
    "leadership": [
        "president", "government", "leaders", "election",
        "parliament", "minister", "summit", "official",
    ],
    "hope": [
        "peace", "recovery", "help", "aid", "agreement",
        "hope", "support", "truce", "breakthrough",
    ],
    "fear": [
        "warning", "threat", "crisis", "uncertainty", "fear",
        "danger", "emergency", "alert",
    ],
}

# Verse tags come from keywords, not tone, so a lament can carry a "peace" tag.
# These aliases connect each news theme to verse themes that actually exist in
# the library, otherwise selection silently falls back to a random verse.
THEME_ALIASES = {
    "conflict": ["peace", "hope", "faith", "wisdom"],
    "disaster": ["hope", "faith", "grief", "gratitude"],
    "grief": ["grief", "hope", "faith"],
    "injustice": ["justice", "hope", "wisdom"],
    "leadership": ["leadership", "wisdom", "justice"],
    "hope": ["hope", "gratitude", "faith", "peace"],
    "fear": ["fear", "hope", "faith", "peace"],
    "general": ["hope", "gratitude", "faith", "wisdom"],
}

# Rank verses by how they actually read, so an encouragement card gets
# encouragement rather than a psalm about ambush.
UPLIFTING_MARKERS = [
    "trust in the lord",
    "hope thou in god",
    "be of good courage",
    "fear not",
    "the lord is my shepherd",
    "my refuge",
    "he restoreth my soul",
    "peace i leave",
    "the lord is my light",
    "the lord is my strength",
    "he healeth",
    "his mercy endureth",
    "rejoice and be glad",
    "cast thy burden",
    "wait on the lord",
    "perfect peace",
    "the joy of the lord",
    "he giveth power to the faint",
    "everlasting arms",
    "god is our refuge and strength",
    "goodness and mercy",
    "shall give thee light",
    "sing praise",
    "glad and rejoice",
    "lovingkindness",
    "put gladness in my heart",
    "will put their trust in thee",
]

HARSH_MARKERS = [
    "lieth in wait",
    "wicked",
    "mine enemies",
    "my enemies",
    "lion",
    "blood",
    "smite",
    "cut off",
    "destruction",
    "desolate",
    "hast thou forsaken",
    "hearest not",
    "slay",
    "destroy me",
    "wretched man",
    "iniquity",
    "abomination",
    "grievous",
    "croucheth",
    "dried up",
]

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


def _load_verses():
    with open(VERSES_FILE, encoding="utf-8") as handle:
        return json.load(handle)["items"]


def _load_used():
    if not STATE_FILE.exists():
        return set()

    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except Exception as exc:
        logger.warning("Could not read Bible history: %s", exc)
        return set()


def _save_used(used):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(sorted(used), indent=2),
        encoding="utf-8",
    )


def _tier(verse):
    """
    Rank a verse for tone.

    0 = explicitly encouraging wording
    1 = neutral
    2 = harsh or despairing wording
    """

    text = verse.get("text", "").lower()

    if any(marker in text for marker in HARSH_MARKERS):
        return 2

    if any(marker in text for marker in UPLIFTING_MARKERS):
        return 0

    return 1


def _candidates_for(theme, verses):
    """Verses for a theme, ordered by relevance through the alias chain."""

    wanted = [theme] + THEME_ALIASES.get(theme, [])

    seen = set()
    ordered = []

    for wanted_theme in wanted:
        for verse in verses:
            reference = verse["reference"]

            if reference in seen:
                continue

            if wanted_theme in verse.get("themes", []):
                seen.add(reference)
                ordered.append(verse)

    return ordered


def _choose_unused(candidates, all_verses):
    """Pick an unused verse, preferring the most encouraging wording."""

    used = _load_used()

    tiers = {0: [], 1: [], 2: []}

    for verse in candidates:
        tiers[_tier(verse)].append(verse)

    for tier in (0, 1, 2):
        available = [v for v in tiers[tier] if v["reference"] not in used]

        if available:
            verse = random.choice(available)
            used.add(verse["reference"])
            _save_used(used)
            return verse

    available = [v for v in all_verses if v["reference"] not in used]

    if not available:
        logger.info("All Bible verses used. Starting a new cycle.")
        used = set()
        available = candidates or all_verses

    verse = random.choice(available)
    used.add(verse["reference"])
    _save_used(used)

    return verse


def _headlines():
    stories = []

    for url in WORLD_FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()

                if title:
                    stories.append(title)

        except Exception as exc:
            logger.warning("World feed failed: %s", exc)

    return stories


def _theme_for(headlines):
    text = " ".join(headlines).lower()

    scores = {
        theme: sum(1 for word in words if word in text)
        for theme, words in KEYWORDS.items()
    }

    if not scores:
        return "general"

    best = max(scores, key=scores.get)

    return best if scores.get(best, 0) else "general"


def build_bible_post(post):
    headlines = _headlines()
    theme = _theme_for(headlines)

    verses = _load_verses()

    candidates = _candidates_for(theme, verses)

    if not candidates:
        logger.warning("No tagged verses for %s; using full library.", theme)
        candidates = verses

    verse = _choose_unused(candidates, verses)

    context = THEME_MESSAGES.get(theme, THEME_MESSAGES["general"])

    post = dict(post)
    post["category"] = "bible_quotes"
    post["content"] = (
        f"{verse['reference']} KJV\n\n"
        f"{verse['text']}\n\n"
        f"{context}"
    )
    post["bible_reference"] = verse["reference"]
    post["world_theme"] = theme
    post["source_headlines_count"] = len(headlines)
    post["date"] = date.today().isoformat()

    logger.info(
        "Bible post prepared: %s | theme: %s | candidates: %d | tone: %d",
        verse["reference"],
        theme,
        len(candidates),
        _tier(verse),
    )

    return post
