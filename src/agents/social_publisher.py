"""
Social Publisher — Bright Side Daily

Publishes one post to every enabled platform:

    Facebook  → every slot, real Pexels photo (unchanged)

    Instagram → every slot EXCEPT funny_meme (daily humor) and
                engagement_question (question of the day).

                Format is chosen per slot by DEFAULT_FORMAT_PLAN:
                  REELS    morning_motivation
                  CAROUSEL none (switched off)
                  IMAGE    everything else
                Override with IG_REEL_SLOTS / IG_CAROUSEL_SLOTS, or
                IG_MEDIA_TYPE_<SLOT> for a single slot, or IG_MEDIA_TYPE for
                everything at once.

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
    # funny_meme now carries the relatable bank and does run on Instagram.
    "engagement_question",
}

INSTAGRAM_EXCLUDED_CATEGORIES = {
    # meme_captions is retired; kept here so it can never reach Instagram
    # if a slot is ever pointed back at it by mistake.
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


# ── Format plan ───────────────────────────────────────────────────────────────
# A slot posts exactly one format. The default plan keeps carousels to two a
# day and gives reels the two bookend slots, where they earn the most reach.
#
#   REELS     morning + night — video is the discovery format
#   CAROUSEL  mid-morning + evening — carousels are the save format
#   IMAGE     everything else — the cheap, reliable default
#
# Override without touching code:
#   IG_REEL_SLOTS      comma separated slot names to render as reels
#   IG_CAROUSEL_SLOTS  comma separated slot names to render as carousels
#   IG_MEDIA_TYPE_<SLOT>  one slot, exact wins (e.g. IG_MEDIA_TYPE_BIBLE_...)
#   IG_MEDIA_TYPE      force one format everywhere, ignoring the plan

DEFAULT_FORMAT_PLAN = {
    # One reel a day, on the slot with the most reach.
    "REELS": {"morning_motivation"},
    # Carousels are switched off. The generator still exists — set
    # IG_CAROUSEL_SLOTS or IG_MEDIA_TYPE to bring them back.
    "CAROUSEL": set(),
}

VALID_FORMATS = {"IMAGE", "CAROUSEL", "REELS"}


def _clean(value):
    """Normalise a format name, or return None when it is not one."""

    if not value:
        return None

    candidate = value.strip().upper()
    return candidate if candidate in VALID_FORMATS else None


def _slot_list(variable):
    """Parse a comma separated slot list from the environment."""

    raw = os.environ.get(variable)

    if not raw:
        return None

    return {
        name.strip().lower()
        for name in raw.split(",")
        if name.strip()
    }


def _media_type_for(slot):
    """Decide this slot's format.

    Order of precedence:
        1. IG_MEDIA_TYPE_<SLOT>   one slot, exact
        2. IG_REEL_SLOTS / IG_CAROUSEL_SLOTS   a custom plan
        3. IG_MEDIA_TYPE          a global override
        4. DEFAULT_FORMAT_PLAN    what ships in the repo
    """

    name = str(slot or "").strip().lower()

    exact = _clean(os.environ.get(f"IG_MEDIA_TYPE_{name.upper()}"))

    if exact:
        return exact

    reels = _slot_list("IG_REEL_SLOTS")
    carousels = _slot_list("IG_CAROUSEL_SLOTS")

    if reels is not None or carousels is not None:
        if name in (carousels or set()):
            return "CAROUSEL"
        if name in (reels or set()):
            return "REELS"
        return "IMAGE"

    forced = _clean(os.environ.get("IG_MEDIA_TYPE"))

    if forced:
        return forced

    if name in DEFAULT_FORMAT_PLAN["CAROUSEL"]:
        return "CAROUSEL"

    if name in DEFAULT_FORMAT_PLAN["REELS"]:
        return "REELS"

    return "IMAGE"


def _publish_instagram(post):
    """Publish to Instagram using the configured media type."""

    media_type = _media_type_for(post.get("slot"))
    publisher = InstagramPublisher()

    if media_type == "REELS":
        try:
            # The animated reel draws its own frames, so it needs the post,
            # not a card. It still returns None if it cannot render.
            video = generate_reel(post)

            if not video:
                log.warning("Reel rendering unavailable; posting the card instead.")
                card = BlackCardGenerator().generate(post)
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
