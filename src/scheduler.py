"""
Daily Scheduler — Bright Side Daily

Runs Bright Side Daily posts and publishes each one to:
  - Facebook  (real Pexels photo)
  - Instagram (black-background card with @handle watermark)

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
from agents.social_publisher import SocialPublisher
from agents.facebook_publisher import FacebookPublisher
from generators.pexels_photo_generator import PexelsPhotoGenerator

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

# Slot schedule (UTC). GitHub Actions cron uses UTC; EAT is UTC+3.
DAILY_SCHEDULE = [
    {"slot": "morning_motivation",   "cron_utc": "0 5 * * *",  "label": "Morning Motivation  (8AM EAT)"},
    {"slot": "positive_quote",       "cron_utc": "0 7 * * *",  "label": "Positive Quote      (10AM EAT)"},
    {"slot": "funny_meme",           "cron_utc": "0 9 * * *",  "label": "Funny Meme          (12PM EAT)"},
    {"slot": "self_improvement",     "cron_utc": "0 11 * * *", "label": "Self Improvement    (2PM EAT)"},
    {"slot": "midday_encouragement", "cron_utc": "0 13 * * *", "label": "Midday Encouragement(4PM EAT)"},
    {"slot": "evening_reflection",   "cron_utc": "0 16 * * *", "label": "Evening Reflection  (7PM EAT)"},
    {"slot": "engagement_question",  "cron_utc": "0 18 * * *", "label": "Engagement Question (9PM EAT)"},
]


def run_slot(slot: str, dry_run: bool = False, platforms: str = None) -> dict:
    """Pick content → Pexels photo → publish to Facebook and Instagram."""

    log.info("%s", "─" * 50)
    log.info("▶  Running slot: %s", slot)
    log.info("%s", "─" * 50)

    results = {"slot": slot, "timestamp": datetime.utcnow().isoformat()}

    # 1. Select content
    try:
        post = ContentAgent().pick(slot)
        log.info("📝 Content selected: %s...", post["content"][:80])
        results["post"] = post
    except Exception as exc:
        log.error("❌ Content selection failed: %s", exc)
        results["error"] = f"content_agent: {exc}"
        return results

    # 2. Generate the Facebook Pexels photo (required — never text-only)
    try:
        image_path = PexelsPhotoGenerator().generate(post)
        results["image_path"] = image_path
        log.info("🖼️  Photo ready: %s", image_path)
    except Exception as exc:
        log.error("❌ Photo generation failed: %s. Skipping slot.", exc)
        results["image_error"] = str(exc)
        return results

    # 3. Publish to every enabled platform
    try:
        if dry_run:
            os.environ["DRY_RUN"] = "true"

        publisher = SocialPublisher(platforms=platforms)
        result = publisher.publish(post, image_path)

        results["publish_result"] = result

        for platform in ("facebook", "instagram"):
            platform_result = result.get(platform)

            if not isinstance(platform_result, dict):
                continue

            if platform_result.get("success"):
                log.info("✅ %s published [%s]", platform.title(), slot)
            elif platform_result.get("skipped"):
                log.warning(
                    "⚠️  %s skipped [%s]: %s",
                    platform.title(),
                    slot,
                    platform_result.get("error"),
                )
            else:
                log.error(
                    "❌ %s failed [%s]: %s",
                    platform.title(),
                    slot,
                    platform_result.get("error"),
                )

    except Exception as exc:
        log.error("❌ Publisher failed: %s", exc)
        results["error"] = f"publisher: {exc}"

    return results


def run_all(dry_run: bool = False, platforms: str = None) -> list:
    """Run every scheduled slot."""

    log.info(
        "🌟 Starting full daily run — %s",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )

    results = [
        run_slot(item["slot"], dry_run=dry_run, platforms=platforms)
        for item in DAILY_SCHEDULE
    ]

    successful = sum(
        1
        for result in results
        if result.get("publish_result", {}).get("success")
    )

    log.info("%s", "═" * 50)
    log.info(
        "Daily run complete: %s/%s posts successful",
        successful,
        len(results),
    )
    log.info("%s", "═" * 50)

    return results


def retry_failed():
    """Retry previously failed Facebook posts."""

    FacebookPublisher().publish_failed()


def print_schedule():
    print("\n📅  Bright Side Daily — Post Schedule")
    print("=" * 55)

    for item in DAILY_SCHEDULE:
        print(f"  {item['label']}  │  cron: {item['cron_utc']}")

    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bright Side Daily Scheduler")
    parser.add_argument("--slot", type=str, help="Run a specific slot")
    parser.add_argument("--all", action="store_true", help="Run all slots")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed posts")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no real posting)")
    parser.add_argument("--schedule", action="store_true", help="Print the schedule")
    parser.add_argument(
        "--platforms",
        type=str,
        default=None,
        help="Comma separated platforms, e.g. facebook,instagram",
    )
    args = parser.parse_args()

    if args.schedule:
        print_schedule()
    elif args.retry_failed:
        retry_failed()
    elif args.all:
        print(json.dumps(
            run_all(dry_run=args.dry_run, platforms=args.platforms),
            indent=2,
            default=str,
        ))
    elif args.slot:
        print(json.dumps(
            run_slot(args.slot, dry_run=args.dry_run, platforms=args.platforms),
            indent=2,
            default=str,
        ))
    else:
        parser.print_help()
