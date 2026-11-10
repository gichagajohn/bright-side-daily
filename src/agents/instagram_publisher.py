"""
Instagram Publisher — Bright Side Daily

Publishes single-image feed posts to an Instagram Business / Creator
account through the Instagram Graph API.

Flow (Instagram requires two steps):
    1. Create a media container from a public image URL.
    2. Publish the container.

Required environment variables:
    IG_USER_ID            Instagram Business account ID
    IG_ACCESS_TOKEN       Long-lived token with
                          instagram_basic + instagram_content_publish
    SUPABASE_*            used to host the image publicly
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests

from agents.supabase_storage import SupabaseStorage

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

IG_STATE_LOG = STATE_DIR / "instagram_posted.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("instagram")

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
MAX_RETRIES = 3
RETRY_DELAY = 20
CONTAINER_POLL_INTERVAL = 5
CONTAINER_POLL_ATTEMPTS = 12


class InstagramPublisher:
    def __init__(self):
        self.user_id = os.environ.get("IG_USER_ID", "")
        self.token = os.environ.get("IG_ACCESS_TOKEN", "")
        self.dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

        if not self.dry_run and (not self.user_id or not self.token):
            raise EnvironmentError(
                "Missing IG_USER_ID or IG_ACCESS_TOKEN environment variables."
            )

    # ── Caption ───────────────────────────────────────────────────────────────

    def build_caption(self, post):
        """Instagram caption: quote, context, hashtags, handle."""

        content = post.get("content", "").strip()
        category = post.get("category", "")
        theme = post.get("world_theme", "")

        hashtags = {
            "motivational_quotes":
                "#Motivation #Mindset #DailyMotivation #Growth",
            "positive_life_quotes":
                "#PositiveVibes #GoodVibes #HappyLife #Positivity",
            "self_improvement_quotes":
                "#SelfImprovement #GrowthMindset #Discipline #Habits",
            "gratitude_quotes":
                "#Gratitude #Thankful #GratefulHeart #Blessed",
            "encouragement_quotes":
                "#YouGotThis #KeepGoing #StayStrong #Encouragement",
            "meme_captions":
                "#Relatable #Funny #Mood #DailyLaughs",
            "engagement_questions":
                "#Community #QuestionOfTheDay #ShareYourThoughts",
            "bible_quotes":
                "#BibleVerse #KJV #Faith #Hope #DailyVerse",
        }.get(category, "#BrightSideDaily #DailyQuotes")

        parts = [content]

        if category == "engagement_questions":
            parts.append("Drop your answer in the comments 👇")
        elif category == "bible_quotes":
            parts.append(
                "Shared with respect for everyone facing difficult news today. 🙏"
            )
        else:
            parts.append(
                "Share this with someone who needs it today 💛"
            )

        if theme and category == "bible_quotes":
            parts.append(f"#WorldNews #Theme_{theme.title()}")

        parts.append(f"{hashtags} #BrightSideDaily")

        return "\n\n".join(parts)

    # ── API calls ─────────────────────────────────────────────────────────────

    def _create_container(self, image_url, caption):
        response = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            },
            timeout=60,
        )

        payload = response.json()

        if response.status_code != 200 or "id" not in payload:
            return {
                "success": False,
                "error": payload.get("error", payload),
                "status_code": response.status_code,
            }

        return {"success": True, "container_id": payload["id"]}

    def _wait_for_container(self, container_id):
        """Instagram needs a moment to fetch and process the image."""

        for attempt in range(CONTAINER_POLL_ATTEMPTS):
            response = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": self.token,
                },
                timeout=30,
            )

            status = (
                response.json().get("status_code", "")
                if response.status_code == 200
                else ""
            )

            if status == "FINISHED":
                return True

            if status == "ERROR":
                log.error("Instagram container error: %s", response.text[:300])
                return False

            log.info(
                "Container %s status: %s (%d/%d)",
                container_id,
                status or "pending",
                attempt + 1,
                CONTAINER_POLL_ATTEMPTS,
            )

            time.sleep(CONTAINER_POLL_INTERVAL)

        return False

    def _publish_container(self, container_id):
        response = requests.post(
            f"{GRAPH_API_BASE}/{self.user_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self.token,
            },
            timeout=60,
        )

        payload = response.json()

        if response.status_code == 200 and "id" in payload:
            return {"success": True, "data": payload}

        return {
            "success": False,
            "error": payload.get("error", payload),
            "status_code": response.status_code,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def publish(self, post, image_path):
        """Upload image, create container, publish. Returns result dict."""

        slot = post.get("slot", "unknown")
        caption = self.build_caption(post)

        log.info("Instagram publish [%s] | image: %s", slot, image_path)

        if self.dry_run:
            log.info("[DRY RUN] Instagram caption:\n%s", caption)
            return {
                "success": True,
                "dry_run": True,
                "platform": "instagram",
                "slot": slot,
            }

        if not image_path or not Path(image_path).exists():
            return {
                "success": False,
                "platform": "instagram",
                "error": "Instagram requires an image; none was generated.",
            }

        storage = None
        public_url = None

        try:
            storage = SupabaseStorage()
            public_url = storage.upload(image_path)

            for attempt in range(1, MAX_RETRIES + 1):
                container = self._create_container(public_url, caption)

                if not container["success"]:
                    log.warning(
                        "Attempt %d/%d container failed: %s",
                        attempt,
                        MAX_RETRIES,
                        container.get("error"),
                    )

                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                        continue

                    return {
                        "success": False,
                        "platform": "instagram",
                        **container,
                    }

                container_id = container["container_id"]

                if not self._wait_for_container(container_id):
                    return {
                        "success": False,
                        "platform": "instagram",
                        "error": "Container did not finish processing.",
                    }

                result = self._publish_container(container_id)

                if result["success"]:
                    log.info("Instagram post published [%s]", slot)
                    self._log_success(post, caption, result.get("data", {}))
                    return {
                        "success": True,
                        "platform": "instagram",
                        **result,
                    }

                log.warning(
                    "Attempt %d/%d publish failed: %s",
                    attempt,
                    MAX_RETRIES,
                    result.get("error"),
                )

                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

            return {
                "success": False,
                "platform": "instagram",
                "error": "All retries exhausted.",
            }

        except Exception as exc:
            log.exception("Instagram publishing failed: %s", exc)
            return {
                "success": False,
                "platform": "instagram",
                "error": str(exc),
            }

        finally:
            # The public object is only needed while Instagram fetches it.
            if storage and public_url:
                storage.delete(public_url)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log_success(self, post, caption, data):
        entries = []

        if IG_STATE_LOG.exists():
            try:
                with open(IG_STATE_LOG) as file:
                    entries = json.load(file)
            except Exception:
                entries = []

        entries.append(
            {
                "post": post,
                "caption": caption,
                "ig_response": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        with open(IG_STATE_LOG, "w") as file:
            json.dump(entries, file, indent=2)
