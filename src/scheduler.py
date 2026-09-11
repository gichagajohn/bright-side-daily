"""
Daily Scheduler — Bright Side Daily

Runs Bright Side Daily posts using:
- Pexels photos
- Category-specific fonts
- Facebook photo publishing

Bible posts are handled separately by:
.github/workflows/bible_post.yml
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
from generators.pexels_photo_generator import PexelsPhotoGenerator
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


DAILY_SCHEDULE = [
    {
        "slot": "morning_motivation",
        "cron_utc": "0 5 * * *",
        "label": "Morning Motivation (8AM EAT)",
    },
    {
        "slot": "positive_quote",
        "cron_utc": "0 7 * * *",
        "label": "Positive Quote (10AM EAT)",
    },
    {
        "slot": "funny_meme",
        "cron_utc": "0 9 * * *",
        "label": "Funny Meme (12PM EAT)",
    },
    {
        "slot": "self_improvement",
        "cron_utc": "0 11 * * *",
        "label": "Self Improvement (2PM EAT)",
    },
    {
        "slot": "midday_encouragement",
        "cron_utc": "0 13 * * *",
        "label": "Midday Encouragement (4PM EAT)",
    },
    {
        "slot": "evening_reflection",
        "cron_utc": "0 16 * * *",
        "label": "Evening Reflection (7PM EAT)",
    },
    {
        "slot": "engagement_question",
        "cron_utc": "0 18 * * *",
        "label": "Engagement Question (9PM EAT)",
    },
]


def run_slot(slot: str, dry_run: bool = False) -> dict:
    """
    Run one slot:

    1. Select content.
    2. Download a Pexels photo.
    3. Add the caption and category font.
    4. Publish the photo to Facebook.
    """

    log.info("=" * 60)
    log.info("Running slot: %s", slot)
    log.info("=" * 60)

    results = {
        "slot": slot,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ─────────────────────────────────────────────────────────────────────
    # 1. Select content
    # ─────────────────────────────────────────────────────────────────────

    try:
        agent = ContentAgent()
        post = agent.pick(slot)

        log.info(
            "Content selected: %s",
            post.get("content", "")[:100],
        )

        results["post"] = post

    except Exception as exc:
        log.exception("Content selection failed: %s", exc)
        results["error"] = f"content_agent: {exc}"
        return results

    # ─────────────────────────────────────────────────────────────────────
    # 2. Generate Pexels photo
    # ─────────────────────────────────────────────────────────────────────

    try:
        generator = PexelsPhotoGenerator()
        image_path = generator.generate(post)

        results["image_path"] = image_path

        log.info("Photo created: %s", image_path)

    except Exception as exc:
        # Never silently publish a caption-only post.
        log.exception(
            "Photo generation failed. Post will be skipped: %s",
            exc,
        )

        results["image_error"] = str(exc)
        return results

    # ─────────────────────────────────────────────────────────────────────
    # 3. Publish photo and caption to Facebook
    # ─────────────────────────────────────────────────────────────────────

    try:
        if dry_run:
            os.environ["DRY_RUN"] = "true"

        publisher = FacebookPublisher()

        result = publisher.publish(
            post,
            image_path,
        )

        results["publish_result"] = result

        if result.get("success"):
            log.info("Slot published successfully: %s", slot)
        else:
            log.error("Facebook publishing failed: %s", result)

    except Exception as exc:
        log.exception("Publisher failed: %s", exc)
        results["error"] = f"publisher: {exc}"

    return results


def run_all(dry_run: bool = False) -> list:
    """Run all normal Bright Side Daily slots."""

    log.info(
        "Starting Bright Side Daily run: %s UTC",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    )

    results = []

    for schedule in DAILY_SCHEDULE:
        result = run_slot(
            schedule["slot"],
            dry_run=dry_run,
        )
        results.append(result)

    successful = sum(
        1
        for result in results
        if result.get("publish_result", {}).get("success")
    )

    log.info(
        "Daily run complete: %d/%d posts successful",
        successful,
        len(results),
    )

    return results


def retry_failed():
    """Retry previous failed posts."""

    publisher = FacebookPublisher()
    publisher.publish_failed()


def print_schedule():
    """Print the Bright Side Daily schedule."""

    print()
    print("Bright Side Daily Schedule")
    print("=" * 60)

    for schedule in DAILY_SCHEDULE:
        print(
            f"{schedule['label']} | "
            f"cron: {schedule['cron_utc']}"
        )

    print("=" * 60)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bright Side Daily Scheduler"
    )

    parser.add_argument(
        "--slot",
        type=str,
        help="Run one specific slot",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all normal slots",
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed posts",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and log without publishing",
    )

    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Print the schedule",
    )

    args = parser.parse_args()

    if args.schedule:
        print_schedule()

    elif args.retry_failed:
        retry_failed()

    elif args.all:
        output = run_all(
            dry_run=args.dry_run,
        )
        print(json.dumps(output, indent=2, default=str))

    elif args.slot:
        output = run_slot(
            args.slot,
            dry_run=args.dry_run,
        )
        print(json.dumps(output, indent=2, default=str))

    else:
        parser.print_help()
