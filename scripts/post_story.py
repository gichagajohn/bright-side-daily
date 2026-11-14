"""
Publish one Instagram Story for the current part of the day.

Picks content from the matching slot, renders a 1080x1920 story with a poll
holder, and publishes it through the Instagram API.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agents.content_agent import ContentAgent
from agents.instagram_publisher import InstagramPublisher
from generators.story_generator import generate as generate_story

# Morning story uses the motivation library, evening uses gratitude.
SLOT_BY_HOUR = [
    (0, 11, "morning_motivation"),
    (11, 24, "evening_reflection"),
]


def pick_slot():
    hour = datetime.utcnow().hour

    for start, end, slot in SLOT_BY_HOUR:
        if start <= hour < end:
            return slot

    return "morning_motivation"


def main():
    slot = pick_slot()

    post = ContentAgent().pick(slot)

    # Stories are Instagram-only: no Pexels photo needed.
    story_path = generate_story(post, variant="poll")

    result = InstagramPublisher().publish_story(story_path)

    print(json.dumps(
        {
            "slot": slot,
            "story": story_path,
            "result": result,
        },
        indent=2,
        default=str,
    ))

    if not result.get("success"):
        raise SystemExit(f"Story failed: {result}")


if __name__ == "__main__":
    main()
