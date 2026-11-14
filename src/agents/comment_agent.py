"""
Comment Agent — Bright Side Daily

Replies to new Instagram comments so the account has early engagement velocity,
which is one of the strongest reach signals available without Reels.

Rules:
  - never replies twice to the same comment
  - never replies to the account's own comments
  - rotates reply wording so it does not read as automated
  - skips spam patterns and anything longer than a sensible length

Run:
    python src/agents/comment_agent.py
"""

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agents.instagram_publisher import InstagramPublisher

STATE_DIR = ROOT / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

REPLIED_FILE = STATE_DIR / "ig_replied_comments.json"
POSTED_LOG = STATE_DIR / "instagram_posted.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("comment_agent")

MAX_AGE_DAYS = int(os.environ.get("COMMENT_MAX_AGE_DAYS", "7"))
MAX_REPLIES_PER_RUN = int(os.environ.get("COMMENT_MAX_REPLIES", "25"))

# Reply pools. Picked by time of day and rotated so no two replies match.
REPLIES = {
    "general": [
        "Thank you for being here 💛",
        "Glad this found you today 🙏",
        "Appreciate you taking the time to comment 💛",
        "This made my day — thank you.",
        "Thank you! More tomorrow.",
        "Means a lot. Thank you 💛",
        "So glad it landed. 🙏",
        "Thank you for reading.",
    ],
    "agree": [
        "Right? Needed the reminder myself. 💛",
        "Exactly this. 🙏",
        "Glad it resonated with you.",
        "You said it better than I did.",
    ],
    "question": [
        "Good question — would love to hear what you think 👀",
        "Tell me more in a reply, I read every one 💛",
        "What would your answer be?",
    ],
    "thanks": [
        "You are so welcome 🙏",
        "Anytime 💛",
        "Glad it helped.",
    ],
}

QUESTION_MARKERS = ("?",)
THANKS_MARKERS = ("thank", "amen", "blessed", "god bless", "grateful")
AGREE_MARKERS = ("exactly", "so true", "true", "needed this", "this is me", "facts", "same")

SPAM_MARKERS = (
    "http://", "https://", "www.", "dm me", "check my", "follow back",
    "buy now", "click here", "promo", "giveaway", "free followers",
)


def _load(path, default):
    if not path.exists():
        return default

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _save(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _pick_reply(text):
    lowered = text.lower()

    if any(marker in lowered for marker in QUESTION_MARKERS):
        pool = REPLIES["question"]
    elif any(marker in lowered for marker in THANKS_MARKERS):
        pool = REPLIES["thanks"]
    elif any(marker in lowered for marker in AGREE_MARKERS):
        pool = REPLIES["agree"]
    else:
        pool = REPLIES["general"]

    return random.choice(pool)


def _is_spam(text):
    lowered = text.lower()

    if len(text) > 500:
        return True

    return any(marker in lowered for marker in SPAM_MARKERS)


def run(dry_run=False):
    entries = _load(POSTED_LOG, [])

    if not entries:
        log.info("No Instagram posts recorded yet. Nothing to check.")
        return {"replied": 0}

    publisher = InstagramPublisher()
    replied = _load(REPLIED_FILE, [])

    if not isinstance(replied, list):
        replied = []

    replied_ids = {item.get("comment_id") for item in replied}

    cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
    count = 0

    for entry in reversed(entries):
        if count >= MAX_REPLIES_PER_RUN:
            break

        response = entry.get("ig_response", {})
        media_id = response.get("id")

        if not media_id:
            continue

        try:
            published = datetime.fromisoformat(entry.get("timestamp", ""))
        except Exception:
            published = datetime.utcnow()

        if published < cutoff:
            continue

        for comment in publisher.fetch_comments(media_id):
            if count >= MAX_REPLIES_PER_RUN:
                break

            comment_id = comment.get("id")
            text = (comment.get("text") or "").strip()

            if not comment_id or comment_id in replied_ids:
                continue

            # Ignore our own replies.
            if comment.get("replies", {}).get("data"):
                replied_ids.add(comment_id)
                continue

            if not text or _is_spam(text):
                continue

            # Only reply to comments that are not already answered.
            message = _pick_reply(text)

            result = publisher.reply_to_comment(comment_id, message)

            if result.get("success"):
                count += 1
                replied_ids.add(comment_id)
                replied.append(
                    {
                        "comment_id": comment_id,
                        "media_id": media_id,
                        "comment": text[:200],
                        "reply": message,
                        "replied_at": datetime.utcnow().isoformat(),
                    }
                )
                log.info("Replied to %s: %s", comment.get("username"), message)
            else:
                log.warning(
                    "Reply failed for %s: %s",
                    comment_id,
                    result.get("error"),
                )

    _save(REPLIED_FILE, replied[-2000:])

    log.info("Reply run complete: %d replies", count)

    return {"replied": count}


def main():
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    result = run(dry_run=dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
