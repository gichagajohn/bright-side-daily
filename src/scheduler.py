"""
Daily Scheduler — Bright Side Daily
Orchestrates all 7 daily posts. Called by GitHub Actions.

Usage:
  python src/scheduler.py --slot morning_motivation
  python src/scheduler.py --all
  python src/scheduler.py --retry-failed
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agents.content_agent import ContentAgent
from generators.image_generator import ImageGenerator
from agents.facebook_publisher import FacebookPublisher

LOGS_DIR = ROOT / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scheduler.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scheduler")

# ── Daily slot schedule ────────────────────────────────────────────────────────
# These map to UTC times (GitHub Actions cron uses UTC)
DAILY_SCHEDULE = [
    {"slot": "morning_motivation",   "cron_utc": "0 5 * * *",   "label": "Morning Motivation  (8AM EAT)"},
    {"slot": "positive_quote",       "cron_utc": "0 7 * * *",   "label": "Positive Quote      (10AM EAT)"},
    {"slot": "funny_meme",           "cron_utc": "0 9 * * *",   "label": "Funny Meme          (12PM EAT)"},
    {"slot": "self_improvement",     "cron_utc": "0 11 * * *",  "label": "Self Improvement    (2PM EAT)"},
    {"slot": "midday_encouragement", "cron_utc": "0 13 * * *",  "label": "Midday Encouragement(4PM EAT)"},
    {"slot": "evening_reflection",   "cron_utc": "0 16 * * *",  "label": "Evening Reflection  (7PM EAT)"},
    {"slot": "engagement_question",  "cron_utc": "0 18 * * *",  "label": "Engagement Question (9PM EAT)"},
]


def run_slot(slot: str, dry_run: bool = False) -> dict:
    """Execute a single daily slot: pick → generate image → publish."""
    log.info(f"{'─' * 50}")
    log.info(f"▶  Running slot: {slot}")
    log.info(f"{'─' * 50}")

    results = {"slot": slot, "timestamp": datetime.utcnow().isoformat()}

    # 1. Select content
    try:
        agent = ContentAgent()
        post = agent.pick(slot)
        log.info(f"📝 Content selected: {post['content'][:80]}...")
        results["post"] = post
    except Exception as e:
        log.error(f"❌ Content selection failed: {e}")
        results["error"] = f"content_agent: {e}"
        return results

    # 2. Generate image
    image_path = None
    try:
        gen = ImageGenerator()
        image_path = gen.generate(post)
        results["image_path"] = image_path
    except Exception as e:
        log.warning(f"⚠️  Image generation failed: {e}. Will post text only.")
        results["image_warning"] = str(e)

    # 3. Publish to Facebook
    try:
        if dry_run:
            os.environ["DRY_RUN"] = "true"
        publisher = FacebookPublisher()
        result = publisher.publish(post, image_path)
        results["publish_result"] = result
        if result.get("success"):
            log.info(f"✅ Slot [{slot}] published successfully!")
        else:
            log.error(f"❌ Slot [{slot}] failed to publish.")
    except Exception as e:
        log.error(f"❌ Publisher failed: {e}")
        results["error"] = f"publisher: {e}"

    return results


def run_all(dry_run: bool = False) -> list:
    """Run all 7 daily slots."""
    log.info(f"🌟 Starting full daily run — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    results = []
    for schedule in DAILY_SCHEDULE:
        result = run_slot(schedule["slot"], dry_run=dry_run)
        results.append(result)

    # Summary
    successes = sum(1 for r in results if r.get("publish_result", {}).get("success"))
    log.info(f"\n{'═' * 50}")
    log.info(f"Daily run complete: {successes}/{len(results)} posts successful")
    log.info(f"{'═' * 50}\n")
    return results


def retry_failed():
    """Retry all failed posts from the failure log."""
    from agents.facebook_publisher import FacebookPublisher
    publisher = FacebookPublisher()
    publisher.publish_failed()


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bright Side Daily Scheduler")
    parser.add_argument("--slot", type=str, help="Run a specific slot")
    parser.add_argument("--all", action="store_true", help="Run all 7 daily slots")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed posts")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual FB posting)")
    parser.add_argument("--schedule", action="store_true", help="Print the daily schedule")
    args = parser.parse_args()

    if args.schedule:
        print("\n📅  Bright Side Daily — Post Schedule")
        print("=" * 55)
        for s in DAILY_SCHEDULE:
            print(f"  {s['label']}  │  cron: {s['cron_utc']}")
        print("=" * 55)

    elif args.retry_failed:
        retry_failed()

    elif args.all:
        results = run_all(dry_run=args.dry_run)
        print(json.dumps(results, indent=2, default=str))

    elif args.slot:
        result = run_slot(args.slot, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))

    else:
        parser.print_help()
