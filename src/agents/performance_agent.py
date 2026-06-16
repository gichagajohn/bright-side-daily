"""
Content Performance Agent — Bright Side Daily
Tracks engagement metrics per category and adjusts future content frequency.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = ROOT / "data" / "metrics"
STATE_DIR = ROOT / "data" / "state"
METRICS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_FILE = METRICS_DIR / "engagement.json"
HISTORY_FILE = METRICS_DIR / "post_history.json"
POSTED_LOG = STATE_DIR / "successfully_posted.json"

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

log = logging.getLogger("performance_agent")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


class PerformanceAgent:
    def __init__(self):
        self.page_id = os.environ.get("FB_PAGE_ID", "")
        self.access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
        self.metrics = self._load_metrics()

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_metrics(self) -> dict:
        if METRICS_FILE.exists():
            with open(METRICS_FILE) as f:
                return json.load(f)
        return {
            "last_updated": None,
            "total_posts_tracked": 0,
            "engagement_by_category": {},
            "avg_engagement_by_category": {},
            "weights": {},
            "top_performing_content": [],
            "history": [],
        }

    def _save_metrics(self):
        self.metrics["last_updated"] = datetime.utcnow().isoformat()
        with open(METRICS_FILE, "w") as f:
            json.dump(self.metrics, f, indent=2)

    # ── Metrics collection ─────────────────────────────────────────────────────

    def collect_metrics(self):
        """Pull engagement data for all recently posted content."""
        if not POSTED_LOG.exists():
            log.info("No posted content log found.")
            return

        with open(POSTED_LOG) as f:
            posted = json.load(f)

        # Only look at posts from last 30 days
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent = [p for p in posted if p.get("timestamp", "") > cutoff]

        log.info(f"Collecting metrics for {len(recent)} recent posts...")

        for item in recent:
            fb_data = item.get("fb_response", {})
            post_id = fb_data.get("post_id") or fb_data.get("id")
            category = item.get("post", {}).get("category", "unknown")

            if not post_id or not self.access_token:
                # Simulate engagement for dry runs
                engagement = self._simulate_engagement(category)
            else:
                engagement = self._fetch_real_engagement(post_id)

            self._record_engagement(category, engagement, item.get("timestamp"))

        self._compute_averages()
        self._compute_weights()
        self._find_top_content(posted)
        self._save_metrics()
        log.info("✅ Metrics collection complete.")

    def _fetch_real_engagement(self, post_id: str) -> dict:
        url = f"{GRAPH_API_BASE}/{post_id}"
        params = {
            "fields": "likes.summary(true),comments.summary(true),shares,impressions",
            "access_token": self.access_token,
        }
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                return {
                    "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                    "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                    "shares": data.get("shares", {}).get("count", 0),
                    "reach": data.get("impressions", 0),
                }
        except Exception as e:
            log.error(f"Error fetching metrics for {post_id}: {e}")
        return {"likes": 0, "comments": 0, "shares": 0, "reach": 0}

    def _simulate_engagement(self, category: str) -> dict:
        """Simulate realistic engagement for dry runs / testing."""
        import random
        base = {
            "motivational_quotes": (45, 8, 12),
            "positive_life_quotes": (35, 5, 8),
            "meme_captions": (60, 15, 20),
            "self_improvement_quotes": (30, 4, 6),
            "encouragement_quotes": (40, 6, 10),
            "gratitude_quotes": (25, 3, 5),
            "engagement_questions": (20, 30, 3),
        }.get(category, (20, 3, 5))

        likes_base, comments_base, shares_base = base
        return {
            "likes": max(0, int(random.gauss(likes_base, likes_base * 0.3))),
            "comments": max(0, int(random.gauss(comments_base, comments_base * 0.3))),
            "shares": max(0, int(random.gauss(shares_base, shares_base * 0.3))),
            "reach": max(0, int(random.gauss(likes_base * 8, likes_base * 2))),
        }

    def _record_engagement(self, category: str, engagement: dict, timestamp: str = None):
        score = (
            engagement["likes"] * 1.0
            + engagement["comments"] * 3.0
            + engagement["shares"] * 5.0
            + engagement.get("reach", 0) * 0.01
        )

        if category not in self.metrics["engagement_by_category"]:
            self.metrics["engagement_by_category"][category] = []

        self.metrics["engagement_by_category"][category].append({
            "score": score,
            "likes": engagement["likes"],
            "comments": engagement["comments"],
            "shares": engagement["shares"],
            "reach": engagement.get("reach", 0),
            "timestamp": timestamp or datetime.utcnow().isoformat(),
        })
        self.metrics["total_posts_tracked"] += 1

    # ── Analysis ───────────────────────────────────────────────────────────────

    def _compute_averages(self):
        avgs = {}
        for category, records in self.metrics["engagement_by_category"].items():
            if records:
                recent = records[-50:]  # last 50 posts
                avgs[category] = sum(r["score"] for r in recent) / len(recent)
        self.metrics["avg_engagement_by_category"] = avgs

    def _compute_weights(self):
        """
        Adaptive weights: top categories get more frequent slots.
        Normalized so the average weight stays at 1.0.
        High performers get up to 2.0x, low performers floor at 0.5x.
        """
        avgs = self.metrics["avg_engagement_by_category"]
        if not avgs:
            return

        global_avg = sum(avgs.values()) / len(avgs)
        weights = {}

        for category, avg in avgs.items():
            if global_avg > 0:
                raw = avg / global_avg
                # Smooth: dampen extremes
                weights[category] = max(0.5, min(2.0, 0.3 + raw * 0.7))
            else:
                weights[category] = 1.0

        self.metrics["weights"] = weights
        log.info("📊 Adaptive weights updated:")
        for cat, w in sorted(weights.items(), key=lambda x: -x[1]):
            log.info(f"   {cat}: {w:.2f}x")

    def _find_top_content(self, posted: list, top_n: int = 10):
        scored = []
        for item in posted:
            fb_data = item.get("fb_response", {})
            category = item.get("post", {}).get("category", "")
            content = item.get("post", {}).get("content", "")
            # Try to get score from recorded metrics
            records = self.metrics["engagement_by_category"].get(category, [])
            if records:
                latest = records[-1]
                scored.append({
                    "content": content[:100],
                    "category": category,
                    "score": latest["score"],
                    "likes": latest["likes"],
                    "shares": latest["shares"],
                })

        scored.sort(key=lambda x: -x["score"])
        self.metrics["top_performing_content"] = scored[:top_n]

    # ── Reports ────────────────────────────────────────────────────────────────

    def print_report(self):
        print("\n" + "=" * 60)
        print("📊  BRIGHT SIDE DAILY — PERFORMANCE REPORT")
        print("=" * 60)
        print(f"Total posts tracked: {self.metrics['total_posts_tracked']}")
        print(f"Last updated: {self.metrics.get('last_updated', 'Never')}")
        print()

        avgs = self.metrics.get("avg_engagement_by_category", {})
        weights = self.metrics.get("weights", {})

        if avgs:
            print("Category Performance (avg engagement score):")
            for cat, score in sorted(avgs.items(), key=lambda x: -x[1]):
                w = weights.get(cat, 1.0)
                bar = "█" * int(score / 5) + "░" * max(0, 20 - int(score / 5))
                print(f"  {cat:<30} {score:>6.1f}  [{bar}]  weight: {w:.2f}x")
        else:
            print("No engagement data yet. Run collect_metrics() after posting.")

        top = self.metrics.get("top_performing_content", [])
        if top:
            print("\n🏆  Top Performing Content:")
            for i, item in enumerate(top[:5], 1):
                print(f"  {i}. [{item['category']}] {item['content'][:70]}...")
                print(f"     Score: {item['score']:.1f} | Likes: {item['likes']} | Shares: {item['shares']}")
        print("=" * 60 + "\n")


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    agent = PerformanceAgent()

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        agent.print_report()
    else:
        agent.collect_metrics()
        agent.print_report()
