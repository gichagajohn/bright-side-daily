"""
Social Publisher — Bright Side Daily

Publishes one post to every enabled platform:

    Facebook  → every slot, real Pexels photo (unchanged)

    Instagram → every slot EXCEPT funny_meme (daily humor) and
                engagement_question (question of the day).

                Format is chosen with IG_MEDIA_TYPE:
                  IMAGE    (default) black card with JG monogram
                  CAROUSEL three slides — quote, actions, signature
                  REELS    15s vertical video built from the card

Instagram failures never block a Facebook post. If Instagram is not
configured, it is simply skipped.
"""

import logging
import os

from agents.facebook_publisher import FacebookPublisher
from agents.instagram_publisher import InstagramPublisher
from generators.black_card_generator import BlackCardGenerator
from generators.carousel_generator import generate as generate_carousel
from generators.reel_generator import generate as generate_reel

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
    """True when the platform has everything it needs for the chosen mode."""

    mode = (os.environ.get("IG_LOGIN_MODE") or "facebook").strip().lower()

    has_account = bool(
        os.environ.get("IG_ACCESS_TOKEN")
        and (
            mode == "instagram"
            or os.environ.get("IG_USER_ID")
        )
    )

    has_storage = bool(
        os.environ.get("SUPABASE_URL")
        and os.environ.get("SUPABASE_SERVICE_KEY")
    )

    return bool(has_account and has_storage)


def _publish_instagram(post):
    """Publish to Instagram using the configured media type."""

    media_type = (os.environ.get("IG_MEDIA_TYPE") or "IMAGE").strip().upper()
    publisher = InstagramPublisher()

    if media_type == "REELS":
        try:
            card = BlackCardGenerator().generate(post)
            video = generate_reel(card)

            if not video:
                log.warning("Reel rendering unavailable; posting the card instead.")
                return publisher.publish(post, card)

            return publisher.publish_reel(post, video)

        except Exception as exc:
            log.warning("Reel path failed (%s); falling back to a card.", exc)
            card = BlackCardGenerator().generate(post)
            return publisher.publish(post, card)

    if media_type == "CAROUSEL":
        try:
            slides = generate_carousel(post)
            return publisher.publish_carousel(post, slides)
        except Exception as exc:
            log.warning("Carousel path failed (%s); falling back to a card.", exc)
            card = BlackCardGenerator().generate(post)
            return publisher.publish(post, card)

    card = BlackCardGenerator().generate(post)
    return publisher.publish(post, card)


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
                    results["instagram"] = _publish_instagram(post)
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
