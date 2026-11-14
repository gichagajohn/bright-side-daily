"""
Instagram Insights Collector — Bright Side Daily

Pulls reach / saves / shares / comments for recently published posts into
data/metrics/instagram_insights.json, then nudges the category weights used by
ContentAgent so the best-performing themes get picked more often.

Run:
    python src/agents/instagram_insights.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agents.instagram_publisher import InstagramPublisher

METRICS_DIR = ROOT / "data" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

INSIGHTS_FILE = METRICS_DIR / "instagram_insights.json"
POSTED_LOG = ROOT / "data" / "state" / "instagram_posted.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ig_insights")

# How much each signal says about whether a post deserves to be repeated.
# Saves and shares are weighted above likes because they predict reach.
SIGNAL_WEIGHTS = {
    "saved": 3.0,
    "shares": 3.0,
    "comments": 2.0,
    "likes": 1.0,
}

LOOKBACK_DAYS = 30


def _load(path, default):
    if not path.exists():
        return default

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _score(metrics):
    """Weighted engagement score for one post."""

    total = 0.0

    for key, weight in SIGNAL_WEIGHTS.items():
        value = metrics.get(key) or 0

        try:
            total += float(value) * weight
        except (TypeError, ValueError):
            continue

    return round(total, 2)


def collect(dry_run=False):
    entries = _load(POSTED_LOG, [])

    if not entries:
        log.info("No Instagram posts recorded yet at %s", POSTED_LOG)
        return []

    publisher = InstagramPublisher()

    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)

    results = []

    for entry in entries:
        post = entry.get("post", {})
        response = entry.get("ig_response", {})
        media_id = response.get("id")

        if not media_id:
            continue

        logged_at = entry.get("timestamp", "")

        try:
            when = datetime.fromisoformat(logged_at)
        except Exception:
            when = datetime.utcnow()

        if when < cutoff:
            continue

        product = "REELS" if response.get("media_type") == "REELS" else "FEED"
        insights = publisher.fetch_media_insights(media_id, product)

        if not insights.get("success"):
            log.warning("No insights for %s: %s", media_id, insights.get("error"))
            continue

        metrics = insights["metrics"]

        results.append(
            {
                "media_id": media_id,
                "slot": post.get("slot"),
                "category": post.get("category"),
                "bible_reference": post.get("bible_reference"),
                "published_at": logged_at,
                "metrics": metrics,
                "score": _score(metrics),
            }
        )

        log.info(
            "%-22s reach=%-6s saves=%-4s shares=%-4s score=%s",
            post.get("slot"),
            metrics.get("reach"),
            metrics.get("saved"),
            metrics.get("shares"),
            _score(metrics),
        )

    return results


def update_weights(results):
    """
    Translate scores into per-category weights for ContentAgent.

    Category weight = its average score divided by the overall average, clamped
    to 0.6-1.6 so one lucky post cannot dominate the rotation.
    """

    by_category = {}

    for item in results:
        category = item.get("category")

        if not category:
            continue

        by_category.setdefault(category, []).append(item["score"])

    if not by_category:
        return {}

    averages = {
        category: sum(scores) / len(scores)
        for category, scores in by_category.items()
    }

    overall = sum(averages.values()) / len(averages)

    if overall <= 0:
        return {category: 1.0 for category in averages}

    weights = {}

    for category, average in averages.items():
        raw = average / overall
        weights[category] = round(min(1.6, max(0.6, raw)), 3)

    return weights


def main():
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    results = collect(dry_run=dry_run)
    weights = update_weights(results)

    existing = _load(INSIGHTS_FILE, {"history": [], "weights": {}})
    existing["history"] = (existing.get("history") or [])[-500:]
    existing["history"].extend(results)
    existing["updated_at"] = datetime.utcnow().isoformat()

    summary = {}

    for item in results:
        category = item.get("category", "unknown")
        summary.setdefault(category, []).append(item["score"])

    existing["category_averages"] = {
        category: round(sum(scores) / len(scores), 2)
        for category, scores in summary.items()
    }

    if weights:
        existing["weights"] = weights

        # Write weights where ContentAgent reads them.
        weights_path = METRICS_DIR / "engagement.json"
        _save(weights_path, {"weights": weights, "updated_at": existing["updated_at"]})
        log.info("Updated weights: %s", weights)

    _save(INSIGHTS_FILE, existing)

    print(json.dumps(
        {
            "collected": len(results),
            "weights": weights,
            "averages": existing["category_averages"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
