"""Create a respectful daily KJV Bible post informed by world headlines."""
import json
import random
from datetime import date
from pathlib import Path

import feedparser

from utils.logger import setup_logger

ROOT = Path(__file__).resolve().parents[2]
VERSES_FILE = ROOT / "content" / "bible" / "verses.json"
logger = setup_logger("world_bible_agent")

WORLD_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]

KEYWORDS = {
    "conflict": ["war", "conflict", "attack", "fighting", "missile", "ceasefire", "troops"],
    "disaster": ["earthquake", "flood", "storm", "wildfire", "hurricane", "disaster", "rescue"],
    "grief": ["death", "killed", "mourning", "victims", "tragedy", "funeral"],
    "injustice": ["rights", "justice", "protest", "violence", "abuse", "discrimination"],
    "leadership": ["president", "government", "leaders", "election", "parliament", "minister"],
    "hope": ["peace", "recovery", "help", "救", "aid", "agreement", "hope"],
    "fear": ["warning", "threat", "crisis", "uncertainty", "fear", "danger"],
}


def _load_verses():
    with open(VERSES_FILE, encoding="utf-8") as handle:
        return json.load(handle)["items"]


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
    best = max(scores, key=scores.get) if scores else "general"
    return best if scores.get(best, 0) else "general"


def build_bible_post(post):
    headlines = _headlines()
    theme = _theme_for(headlines)
    verses = _load_verses()
    candidates = [v for v in verses if theme in v["themes"]]
    verse = random.choice(candidates or verses)

    context = {
        "conflict": "For everyone affected by conflict and uncertainty, may this be a reminder to seek peace and protection.",
        "disaster": "Our thoughts and prayers are with communities facing hardship and loss.",
        "grief": "We remember those who are grieving and pray for comfort for every affected family.",
        "injustice": "May compassion, justice, and humility guide people and leaders everywhere.",
        "leadership": "May leaders act with wisdom, justice, and concern for the people they serve.",
        "hope": "May hope and peace reach people and communities around the world.",
        "fear": "For anyone feeling afraid or uncertain today, may these words bring courage.",
        "general": "Whatever today brings, may these words bring faith, peace, and encouragement.",
    }[theme]

    post = dict(post)
    post["category"] = "bible_quotes"
    post["content"] = f"{verse['reference']} KJV\n\n{verse['text']}\n\n{context}"
    post["bible_reference"] = verse["reference"]
    post["world_theme"] = theme
    post["source_headlines_count"] = len(headlines)
    post["date"] = date.today().isoformat()
    return post
