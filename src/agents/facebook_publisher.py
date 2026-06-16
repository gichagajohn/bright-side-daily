"""
Facebook Publishing Agent — Bright Side Daily
Posts images and captions to a Facebook Page via the Graph API.
"""
import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = ROOT / "data" / "logs"
STATE_DIR = ROOT / "data" / "state"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "publisher.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("publisher")

FAILED_LOG = STATE_DIR / "failed_posts.json"
POSTED_LOG = STATE_DIR / "successfully_posted.json"

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds


class FacebookPublisher:
    def __init__(self):
        self.page_id = os.environ.get("FB_PAGE_ID", "")
        self.access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
        self.dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

        if not self.dry_run:
            if not self.page_id or not self.access_token:
                raise EnvironmentError(
                    "Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN environment variables."
                )

    # ── Core API calls ─────────────────────────────────────────────────────────

    def _post_photo(self, image_path: str, caption: str) -> dict:
        """Upload a photo with caption to the Facebook Page."""
        url = f"{GRAPH_API_BASE}/{self.page_id}/photos"

        with open(image_path, "rb") as f:
            files = {"source": f}
            data = {
                "caption": caption,
                "access_token": self.access_token,
            }
            response = requests.post(url, data=data, files=files, timeout=60)

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            error = response.json().get("error", {})
            return {
                "success": False,
                "error": error,
                "status_code": response.status_code,
            }

    def _post_text_only(self, message: str) -> dict:
        """Post a text-only message (fallback)."""
        url = f"{GRAPH_API_BASE}/{self.page_id}/feed"
        data = {"message": message, "access_token": self.access_token}
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        return {"success": False, "error": response.json().get("error", {})}

    # ── Post formatting ────────────────────────────────────────────────────────

    def _build_caption(self, post: dict) -> str:
        """Build the Facebook caption from a post payload."""
        content = post.get("content", "")
        slot = post.get("slot", "")
        category = post.get("category", "")

        slot_emojis = {
            "morning_motivation": "☀️",
            "positive_quote": "🌟",
            "funny_meme": "😄",
            "self_improvement": "📈",
            "midday_encouragement": "💪",
            "evening_reflection": "🌙",
            "engagement_question": "💬",
        }

        hashtag_sets = {
            "motivational_quotes": "#Motivation #Success #MindsetMatters #DailyMotivation #GoalSetter",
            "positive_life_quotes": "#PositiveVibes #HappyLife #GoodVibesOnly #LifeIsBeautiful #Positivity",
            "self_improvement_quotes": "#PersonalGrowth #SelfImprovement #BetterEveryDay #GrowthMindset #Habits",
            "gratitude_quotes": "#Gratitude #Thankful #CountYourBlessings #GratefulHeart #Blessed",
            "encouragement_quotes": "#YouGotThis #KeepGoing #NeverGiveUp #StayStrong #Encouragement",
            "meme_captions": "#RelatableLife #Funny #MondayMood #TooReal #WeekdayVibes",
            "engagement_questions": "#Community #ShareYourThoughts #QuestionOfTheDay #ChatWithUs #BrightSideFamily",
        }

        emoji = slot_emojis.get(slot, "✨")
        hashtags = hashtag_sets.get(category, "#BrightSideDaily #PositiveVibes")

        if category == "engagement_questions":
            caption = (
                f"{emoji} {content}\n\n"
                f"Drop your answer in the comments below 👇\n\n"
                f"{hashtags} #BrightSideDaily"
            )
        elif category == "meme_captions":
            caption = (
                f"{emoji} {content}\n\n"
                f"Tag someone who can relate! 😂\n\n"
                f"{hashtags} #BrightSideDaily"
            )
        else:
            caption = (
                f"{emoji} {content}\n\n"
                f"Share this with someone who needs it today! 💛\n\n"
                f"{hashtags} #BrightSideDaily"
            )

        return caption

    # ── Retry logic ────────────────────────────────────────────────────────────

    def publish(self, post: dict, image_path: str = None) -> dict:
        """Publish a post with retries. Returns result dict."""
        caption = self._build_caption(post)
        slot = post.get("slot", "unknown")

        log.info(f"Publishing [{slot}] | image: {image_path or 'none'}")
        log.info(f"Caption preview: {caption[:120]}...")

        if self.dry_run:
            log.info("[DRY RUN] Post would be published:")
            log.info(caption)
            return {
                "success": True,
                "dry_run": True,
                "slot": slot,
                "timestamp": datetime.utcnow().isoformat(),
            }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if image_path and Path(image_path).exists():
                    result = self._post_photo(image_path, caption)
                else:
                    log.warning("No image found — posting text only.")
                    result = self._post_text_only(caption)

                if result["success"]:
                    log.info(f"✅ Posted successfully [{slot}]")
                    self._log_success(post, result, caption)
                    return result
                else:
                    error = result.get("error", {})
                    log.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {error}")
                    if attempt < MAX_RETRIES:
                        log.info(f"Retrying in {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)

            except Exception as e:
                log.error(f"Exception on attempt {attempt}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

        # All retries failed
        log.error(f"❌ All retries failed for [{slot}]")
        self._log_failure(post, caption)
        return {"success": False, "slot": slot, "retries_exhausted": True}

    def publish_failed(self):
        """Retry all previously failed posts."""
        if not FAILED_LOG.exists():
            log.info("No failed posts to retry.")
            return

        with open(FAILED_LOG) as f:
            failed = json.load(f)

        if not failed:
            log.info("Failed posts list is empty.")
            return

        log.info(f"Retrying {len(failed)} failed posts...")
        still_failed = []

        for item in failed:
            result = self.publish(item["post"])
            if not result.get("success"):
                still_failed.append(item)

        with open(FAILED_LOG, "w") as f:
            json.dump(still_failed, f, indent=2)

        log.info(f"Retry complete. {len(still_failed)} still failing.")

    # ── Logging ────────────────────────────────────────────────────────────────

    def _log_success(self, post: dict, result: dict, caption: str):
        data = []
        if POSTED_LOG.exists():
            with open(POSTED_LOG) as f:
                data = json.load(f)
        data.append({
            "post": post,
            "caption": caption,
            "fb_response": result.get("data", {}),
            "timestamp": datetime.utcnow().isoformat(),
        })
        with open(POSTED_LOG, "w") as f:
            json.dump(data, f, indent=2)

    def _log_failure(self, post: dict, caption: str):
        data = []
        if FAILED_LOG.exists():
            with open(FAILED_LOG) as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = []
        data.append({
            "post": post,
            "caption": caption,
            "timestamp": datetime.utcnow().isoformat(),
        })
        with open(FAILED_LOG, "w") as f:
            json.dump(data, f, indent=2)

    # ── Engagement collection ──────────────────────────────────────────────────

    def fetch_post_insights(self, post_id: str) -> dict:
        """Fetch likes, comments, shares for a published post."""
        url = f"{GRAPH_API_BASE}/{post_id}"
        params = {
            "fields": "id,message,likes.summary(true),comments.summary(true),shares",
            "access_token": self.access_token,
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            log.error(f"Error fetching insights for {post_id}: {e}")
        return {}


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    publisher = FacebookPublisher()

    if len(sys.argv) > 1 and sys.argv[1] == "retry-failed":
        publisher.publish_failed()
    else:
        # Test post
        test_post = {
            "slot": "morning_motivation",
            "category": "motivational_quotes",
            "content": "Success begins when excuses end.",
        }
        result = publisher.publish(test_post)
        print(json.dumps(result, indent=2))
