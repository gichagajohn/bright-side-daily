"""
Social Publisher — Bright Side Daily

Publishes one post to every enabled platform:

    Facebook   → every slot, real Pexels photo (unchanged)
    Instagram  → every slot EXCEPT funny_meme (daily humor) and
                 engagement_question (question of the day), using an
                 elegant black-background card with a JG monogram

Instagram failures never block a Facebook post. If Instagram is not
configured, it is simply skipped.
"""

import logging
import os

from agents.facebook_publisher import FacebookPublisher
from agents.instagram_publisher import InstagramPublisher
from generators.black_card_generator import BlackCardGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("social_publisher")


# These slots stay Facebook-only.
INSTAGRAM_EXCLUDED_SLOTS = {
    "funny_meme",
    "engagement_question",
}

INSTAGRAM_EXCLUDED_CATEGORIES = {
    "meme_captions",
    "engagement_questions",
}


def _instagram_enabled():
    return bool(
        os.environ.get("IG_USER_ID")
        and os.environ.get("IG_ACCESS_TOKEN")
        and os.environ.get("SUPABASE_URL")
        and os.environ.get("SUPABASE_SERVICE_KEY")
    )


class SocialPublisher:
    def __init__(self, platforms=None):
        requested = platforms or os.environ.get(
            "PLATFORMS", "facebook,instagram"
        )

        self.platforms = [
            name.strip().lower()
            for name in requested.split(",")
            if name.strip()
        ]

    def publish(self, post, image_path):
        """Publish to each requested platform. Returns per-platform results."""

        results = {}
        slot = post.get("slot", "unknown")

        # ── Facebook ──────────────────────────────────────────────────────────
        if "facebook" in self.platforms:
            try:
                results["facebook"] = FacebookPublisher().publish(
                    post,
                    image_path,
                )
            except Exception as exc:
                log.exception("Facebook publishing failed: %s", exc)
                results["facebook"] = {
                    "success": False,
                    "platform": "facebook",
                    "error": str(exc),
                }

        # ── Instagram ─────────────────────────────────────────────────────────
        if "instagram" in self.platforms:
            facebook_only = (
                slot in INSTAGRAM_EXCLUDED_SLOTS
                or post.get("category", "") in INSTAGRAM_EXCLUDED_CATEGORIES
            )

            if facebook_only:
                log.info(
                    "Instagram skipped for [%s]: this slot is Facebook-only.",
                    slot,
                )
                results["instagram"] = {
                    "success": False,
                    "platform": "instagram",
                    "skipped": True,
                    "facebook_only": True,
                    "error": "Slot is Facebook-only.",
                }
            elif not _instagram_enabled():
                log.warning(
                    "Instagram skipped for [%s]: IG_* or SUPABASE_* secrets "
                    "are not configured.",
                    slot,
                )
                results["instagram"] = {
                    "success": False,
                    "platform": "instagram",
                    "skipped": True,
                    "error": "Instagram credentials not configured.",
                }
            else:
                try:
                    ig_image = BlackCardGenerator().generate(post)
                    results["instagram"] = InstagramPublisher().publish(
                        post,
                        ig_image,
                    )
                except Exception as exc:
                    log.exception("Instagram publishing failed: %s", exc)
                    results["instagram"] = {
                        "success": False,
                        "platform": "instagram",
                        "error": str(exc),
                    }

        results["success"] = any(
            result.get("success")
            for key, result in results.items()
            if isinstance(result, dict) and key != "success"
        )

        return results
