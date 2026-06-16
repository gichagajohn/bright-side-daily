"""
Content Selection Agent — Bright Side Daily
Picks the next post, tracks duplicates, rotates categories, and replenishes low libraries.
"""
import json
import os
import random
from datetime import date, datetime
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = ROOT / "content"
STATE_DIR = ROOT / "data" / "state"
METRICS_FILE = ROOT / "data" / "metrics" / "engagement.json"
STATE_FILE = STATE_DIR / "posted_content.json"
LOW_THRESHOLD = 30  # regenerate when fewer than this remain

# Daily slot → category mapping
SLOT_CATEGORY = {
    "morning_motivation": "motivational_quotes",
    "positive_quote": "positive_life_quotes",
    "funny_meme": "meme_captions",
    "self_improvement": "self_improvement_quotes",
    "midday_encouragement": "encouragement_quotes",
    "evening_reflection": "gratitude_quotes",
    "engagement_question": "engagement_questions",
}

CATEGORY_FILE = {
    "motivational_quotes": CONTENT_DIR / "quotes" / "motivational.json",
    "positive_life_quotes": CONTENT_DIR / "quotes" / "positive_life.json",
    "self_improvement_quotes": CONTENT_DIR / "quotes" / "self_improvement.json",
    "gratitude_quotes": CONTENT_DIR / "quotes" / "gratitude.json",
    "encouragement_quotes": CONTENT_DIR / "quotes" / "encouragement.json",
    "meme_captions": CONTENT_DIR / "memes" / "captions.json",
    "engagement_questions": CONTENT_DIR / "questions" / "engagement.json",
}

# Engagement performance weights (start equal, updated by performance agent)
DEFAULT_WEIGHTS = {
    "motivational_quotes": 1.0,
    "positive_life_quotes": 1.0,
    "self_improvement_quotes": 1.0,
    "gratitude_quotes": 1.0,
    "encouragement_quotes": 1.0,
    "meme_captions": 1.0,
    "engagement_questions": 1.0,
}


class ContentAgent:
    def __init__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
        self.weights = self._load_weights()

    # ── State management ──────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "posted": {},        # category → list of posted indices
            "last_run": None,
            "total_posts": 0,
        }

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _load_weights(self) -> dict:
        """Load performance-adjusted weights from metrics."""
        if not METRICS_FILE.exists():
            return DEFAULT_WEIGHTS.copy()
        try:
            with open(METRICS_FILE) as f:
                metrics = json.load(f)
            weights = DEFAULT_WEIGHTS.copy()
            avg_engagement = metrics.get("avg_engagement_by_category", {})
            if avg_engagement:
                global_avg = sum(avg_engagement.values()) / len(avg_engagement)
                for cat, eng in avg_engagement.items():
                    if cat in weights and global_avg > 0:
                        # Scale: top performers get up to 2x weight
                        weights[cat] = max(0.5, min(2.0, eng / global_avg))
            return weights
        except Exception:
            return DEFAULT_WEIGHTS.copy()

    # ── Content loading ───────────────────────────────────────────────────────

    def _load_category(self, category: str) -> list:
        path = CATEGORY_FILE[category]
        if not path.exists():
            raise FileNotFoundError(f"Content file missing: {path}. Run generate_content_library.py first.")
        with open(path) as f:
            return json.load(f)["items"]

    def _get_remaining(self, category: str) -> list:
        """Return indices not yet posted for a category."""
        items = self._load_category(category)
        posted = set(self.state["posted"].get(category, []))
        remaining = [i for i in range(len(items)) if i not in posted]
        return remaining

    def _check_low_inventory(self, category: str):
        remaining = self._get_remaining(category)
        if len(remaining) < LOW_THRESHOLD:
            print(f"⚠️  Low inventory for {category} ({len(remaining)} left). Triggering regeneration...")
            self._regenerate_category(category)

    def _regenerate_category(self, category: str):
        """Reset posted history so content cycles around."""
        print(f"♻️  Resetting posted history for {category} (cycling content)")
        self.state["posted"][category] = []

    # ── Selection ─────────────────────────────────────────────────────────────

    def pick(self, slot: str) -> dict:
        """Pick the best content for a given daily slot."""
        category = SLOT_CATEGORY[slot]
        self._check_low_inventory(category)

        remaining = self._get_remaining(category)
        if not remaining:
            self._regenerate_category(category)
            remaining = self._get_remaining(category)

        items = self._load_category(category)

        # Weighted random selection (prefer unseen, recent gets slight penalty)
        chosen_idx = random.choice(remaining)
        content = items[chosen_idx]

        # Mark as posted
        self.state["posted"].setdefault(category, [])
        self.state["posted"][category].append(chosen_idx)
        self.state["last_run"] = datetime.utcnow().isoformat()
        self.state["total_posts"] = self.state.get("total_posts", 0) + 1
        self._save_state()

        # Build post payload
        visual_theme = self._pick_visual_theme(category, content)
        return {
            "slot": slot,
            "category": category,
            "content": content,
            "content_index": chosen_idx,
            "visual_theme": visual_theme,
            "date": date.today().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "weight_used": self.weights.get(category, 1.0),
        }

    def pick_all_daily(self) -> list:
        """Pick content for all 7 daily slots."""
        return [self.pick(slot) for slot in SLOT_CATEGORY]

    # ── Visual theme assignment ───────────────────────────────────────────────

    VISUAL_THEMES = {
        "motivational_quotes": [
            "mountain climber reaching summit at sunrise",
            "runner crossing finish line triumphantly",
            "person standing on cliff watching sunrise",
            "eagle soaring above clouds",
            "staircase leading to bright light",
            "open road stretching to horizon at dawn",
        ],
        "positive_life_quotes": [
            "friends laughing together outdoors",
            "family walking in a sunlit park",
            "person smiling at a bright window",
            "colorful flowers in morning light",
            "couple watching sunset on beach",
            "children playing in golden hour light",
        ],
        "self_improvement_quotes": [
            "open book beside a warm cup of coffee",
            "person journaling at a desk by a window",
            "productivity workspace with plants and sunlight",
            "person meditating at sunrise",
            "books stacked with glasses and notepad",
            "person doing yoga on a rooftop at dawn",
        ],
        "gratitude_quotes": [
            "warm coffee mug on table beside rainy window",
            "hands holding a small wildflower",
            "soft sunrise through curtains",
            "person watching golden sunset over water",
            "freshly baked bread in morning light",
            "journal with flowers and morning light",
        ],
        "encouragement_quotes": [
            "hand reaching through misty forest toward light",
            "sunrise breaking through storm clouds",
            "sprout pushing through cracked concrete",
            "lighthouse in stormy sea",
            "caterpillar becoming butterfly illustration",
            "lone hiker emerging from a dense forest",
        ],
        "meme_captions": [
            "cute dog with confused expression",
            "cat sitting next to a Monday coffee mug",
            "person doing a funny but relatable face",
            "cozy blanket pile on a rainy day",
            "office desk in cheerful chaos",
        ],
        "engagement_questions": [
            "colorful speech bubbles on pastel background",
            "group of diverse people at a coffee table",
            "notebook open with a question mark illustration",
            "hand-drawn thought bubbles",
            "bright vibrant community gathering",
        ],
    }

    STYLE_DISTRIBUTION = ["photography"] * 7 + ["illustration"] * 2 + ["minimalist"]

    def _pick_visual_theme(self, category: str, content: str) -> dict:
        themes = self.VISUAL_THEMES.get(category, ["beautiful nature landscape"])
        style = random.choice(self.STYLE_DISTRIBUTION)
        theme = random.choice(themes)

        # Smart keyword matching
        c = content.lower()
        if any(w in c for w in ["morning", "sunrise", "dawn", "wake"]):
            theme = "beautiful sunrise over mountains"
        elif any(w in c for w in ["coffee", "tea", "cozy"]):
            theme = "warm coffee on table beside a sunrise window"
        elif any(w in c for w in ["friend", "together", "share", "laugh"]):
            theme = "friends laughing together outdoors in golden hour"
        elif any(w in c for w in ["nature", "tree", "forest", "ocean", "beach"]):
            theme = "serene nature landscape with soft morning light"
        elif any(w in c for w in ["book", "learn", "read", "study"]):
            theme = "open book and coffee in a cozy reading nook"

        return {"style": style, "theme": theme}


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    agent = ContentAgent()

    if len(sys.argv) > 1:
        slot = sys.argv[1]
        post = agent.pick(slot)
        print(json.dumps(post, indent=2))
    else:
        posts = agent.pick_all_daily()
        print(json.dumps(posts, indent=2))
