"""
Schedule Optimizer — Bright Side Daily

Reads data/metrics/instagram_insights.json and recommends which hours to post,
based on when past posts actually reached people.

It never rewrites the workflow files itself (that would need write access to
.github). Instead it writes data/metrics/schedule_recommendation.json and prints
a ready-to-paste cron set.

Run:
    python src/agents/schedule_optimizer.py
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

METRICS_DIR = ROOT / "data" / "metrics"
INSIGHTS_FILE = METRICS_DIR / "instagram_insights.json"
OUTPUT_FILE = METRICS_DIR / "schedule_recommendation.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("schedule_optimizer")

# Slots Instagram actually publishes to (meme and question are Facebook-only).
INSTAGRAM_SLOTS = [
    ("morning_motivation", 5),
    ("positive_quote", 7),
    ("self_improvement", 11),
    ("midday_encouragement", 13),
    ("evening_reflection", 16),
    ("bible_world_encouragement", 14),
]

# Fallback hours from general East Africa audience behaviour when there is not
# yet enough data to say otherwise.
DEFAULT_HOURS = {
    "morning_motivation": 5,
    "positive_quote": 7,
    "self_improvement": 11,
    "midday_encouragement": 13,
    "evening_reflection": 16,
    "bible_world_encouragement": 14,
}

MIN_SAMPLES = 5


def _load(path, default):
    if not path.exists():
        return default

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def analyse():
    insights = _load(INSIGHTS_FILE, {})
    history = insights.get("history") or []

    by_hour = defaultdict(list)

    for item in history:
        published_at = item.get("published_at", "")

        try:
            hour = datetime.fromisoformat(published_at).hour
        except Exception:
            continue

        score = item.get("score")

        if isinstance(score, (int, float)):
            by_hour[hour].append(score)

    averages = {
        hour: round(sum(scores) / len(scores), 2)
        for hour, scores in by_hour.items()
        if len(scores) >= MIN_SAMPLES
    }

    return averages, len(history)


def recommend():
    averages, sample_size = analyse()

    recommendation = {
        "generated_at": datetime.utcnow().isoformat(),
        "sample_posts": sample_size,
        "hourly_averages": averages,
        "hours": dict(DEFAULT_HOURS),
        "confident": sample_size >= MIN_SAMPLES * len(INSTAGRAM_SLOTS),
        "notes": [],
    }

    if not averages:
        recommendation["notes"].append(
            "Not enough published data yet. Keeping the default schedule."
        )
        return recommendation

    ranked = sorted(averages.items(), key=lambda item: item[1], reverse=True)
    best_hours = [hour for hour, _score in ranked[: len(INSTAGRAM_SLOTS)]]

    recommendation["best_hours"] = sorted(best_hours)

    if recommendation["confident"]:
        # Assign the best hours to slots in order of their current hour.
        for (slot, _default), hour in zip(
            sorted(INSTAGRAM_SLOTS, key=lambda item: item[1]),
            best_hours,
        ):
            recommendation["hours"][slot] = hour

        recommendation["notes"].append(
            "Hours reassigned from measured engagement. Update the cron entries "
            "in .github/workflows/post_scheduler.yml to match."
        )
    else:
        recommendation["notes"].append(
            f"Only {sample_size} posts measured; "
            f"need {MIN_SAMPLES * len(INSTAGRAM_SLOTS)} for a confident "
            "recommendation. Default hours retained."
        )

    return recommendation


def cron_lines(hours):
    return [
        f"    - cron: \"0 {hour} * * *\"   # {hour:02d}:00 UTC "
        f"= {(hour + 3) % 24:02d}:00 EAT"
        for hour in sorted(set(hours.values()))
    ]


def main():
    recommendation = recommend()

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(recommendation, handle, indent=2, ensure_ascii=False)

    print(json.dumps(recommendation, indent=2))
    print("\nSuggested crons:")
    print("\n".join(cron_lines(recommendation["hours"])))


if __name__ == "__main__":
    main()
