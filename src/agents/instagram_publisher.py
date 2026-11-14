"""
Instagram Publisher — Bright Side Daily

Publishes single-image feed posts to an Instagram Business / Creator account.

Two login modes are supported, chosen with IG_LOGIN_MODE:

  facebook  (default)
      Instagram Graph API via a linked Facebook Page.
      Host: graph.facebook.com
      Needs: IG_USER_ID + IG_ACCESS_TOKEN (Page token)
      Scopes: instagram_basic, instagram_content_publish

  instagram
      Instagram API with Instagram Login. NO Facebook Page required.
      Host: graph.instagram.com
      Needs: IG_ACCESS_TOKEN only (the token identifies the account)
      Scopes: instagram_business_basic, instagram_business_content_publish

Both modes use the same two-step publish flow:
    1. Create a media container from a public image URL.
    2. Publish the container.

Other environment variables:
    IG_API_VERSION        Graph API version, default v23.0
    IG_MEDIA_TYPE         IMAGE | CAROUSEL | REELS   (default IMAGE)
    IG_REEL_DURATION      seconds for generated reels (default 15)
    IG_COLLABORATORS      comma-separated usernames for Collab posts
    SUPABASE_*            used to host the media publicly
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


def _clean(value):
    """Strip whitespace and stray line breaks from a secret value."""

    if not value:
        return ""

    return (
        value.strip()
        .strip("\u00a0")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )

FACEBOOK_HOST = "https://graph.facebook.com"
INSTAGRAM_HOST = "https://graph.instagram.com"

MAX_RETRIES = 3
RETRY_DELAY = 20
CONTAINER_POLL_INTERVAL = 5
CONTAINER_POLL_ATTEMPTS = 12


# ── Hashtag strategy ─────────────────────────────────────────────────────────
# Repeating one identical hashtag block on every post suppresses reach, so each
# category rotates through several sets. Every set mixes broad discovery tags
# with niche ones the account can realistically rank for.

HASHTAG_SETS = {
    "motivational_quotes": [
        ["#motivation", "#dailyMotivation", "#mindset", "#selfBelief",
         "#growthMindset", "#discipline", "#successMindset", "#morningMotivation",
         "#keepGoing", "#innerStrength"],
        ["#motivationalQuotes", "#dailyInspiration", "#lifeGoals", "#levelUp",
         "#dreambig", "#hardWork", "#neverGiveUp", "#stayFocused",
         "#positiveMindset", "#progress"],
        ["#beInspired", "#dailyHustle", "#selfGrowth", "#ambition",
         "#winTheDay", "#smallSteps", "#keepShowing",
         "#mindsetshift", "#motivateYourself", "#dailyQuotes"],
    ],
    "positive_life_quotes": [
        ["#positiveVibes", "#goodVibes", "#happyLife", "#joyfulliving",
         "#simpleJoys", "#gratitudeDaily", "#brightSide", "#positiveEnergy",
         "#sunnydays", "#mindfulLiving"],
        ["#chooseJoy", "#everydayMagic", "#littleThings", "#slowliving",
         "#goodEnergy", "#lifeIsBeautiful", "#smileMore", "#kindnessMatters",
         "#hopeful", "#peacefulMind"],
        ["#positiveThinking", "#lifelately", "#dailyHappiness", "#beautifulLife",
         "#joyInTheJourney", "#presentMoment", "#softLife", "#innerPeace",
         "#goodDaysAhead", "#contentment"],
    ],
    "self_improvement_quotes": [
        ["#selfImprovement", "#growthMindset", "#personalDevelopment", "#habits",
         "#discipline", "#betterEveryDay", "#selfDiscipline", "#goalSetting",
         "#productivity", "#learnEveryDay"],
        ["#selfGrowth", "#improvement", "#dailyHabits", "#focusAndDiscipline",
         "#levelUpYourself", "#mindsetshift", "#personalGrowth", "#selfMastery",
         "#consistency", "#becomeBetter"],
        ["#selfDevelopment", "#habitBuilding", "#motivatedMindset", "#deepWork",
         "#selfAwareness", "#buildYourself", "#dailyProgress", "#growthJourney",
         "#learnAndGrow", "#futureYou"],
    ],
    "gratitude_quotes": [
        ["#gratitude", "#thankful", "#gratefulHeart", "#blessed",
         "#countYourBlessings", "#gratitudeDaily", "#thankfulHeart", "#appreciation",
         "#gratefulLiving", "#joyfulHeart"],
        ["#gratitudePractice", "#dailyGratitude", "#thankYouGod", "#blessedLife",
         "#gratefulFor", "#simpleBlessings", "#thankfulness", "#heartFullOfThanks",
         "#noticeTheGood", "#gratitudeAttitude"],
        ["#thankfulEveryday",
         "#gratefulMoments", "#blessingsOnBlessings", "#gratitudeJournal",
         "#appreciateLife", "#goodnessOfGod", "#smallBlessings", "#thankfulLiving",
         "#gratefulSoul", "#alreadyEnough"],
    ],
    "encouragement_quotes": [
        ["#encouragement", "#youGotThis", "#keepGoing", "#stayStrong",
         "#neverGiveUp", "#dontGiveUp", "#keepTheFaith", "#strengthAndCourage",
         "#youAreEnough", "#brightSideDaily"],
        ["#encouragingWords", "#dailyEncouragement", "#holdOn", "#keepPushing",
         "#youMatter", "#strongerThanYouThink", "#oneDayAtATime", "#hopeDealer",
         "#beKindToYourself", "#keepBelieving"],
        ["#wordsOfEncouragement", "#youCanDoIt", "#stayHopeful", "#littleByLittle",
         "#progressNotPerfection", "#beGentleWithYourself", "#youAreLoved",
         "#faithOverFear", "#keepShowingUp", "#courage"],
    ],
    "relatable_quotes": [
        ["#relatable", "#relatableQuotes", "#thatIsSoMe", "#dailyLaughs",
         "#sameHere", "#lifeHumor", "#funnyQuotes", "#honestlyMe",
         "#adultingBeLike", "#relatableContent"],
        ["#justForLaughs", "#sarcasm", "#everydayStruggles", "#meIRL",
         "#textPost", "#laughingOutLoud", "#humourDaily", "#realLife",
         "#tiredButHappy", "#notJustMe"],
        ["#relatableMemes", "#adulting", "#smallThings", "#dailyStruggle",
         "#thisIsFine", "#mood", "#honestPost", "#overthinking",
         "#grownUpStuff", "#sameEnergy"],
    ],
    "meme_captions": [
        ["#relatable", "#funnyMemes", "#dailyLaughs", "#memeLife",
         "#thatisSoMe", "#humour", "#lol", "#relatableMemes",
         "#lifeHumor", "#funnyPost"],
        ["#memeOfTheDay", "#relatableContent", "#adultingMemes",
         "#justForLaughs", "#comedyPost", "#sarcasm", "#sameHere",
         "#mondayMood", "#workLifeMemes", "#genZHumour"],
        ["#funnyQuotes", "#relatableQuotes", "#humourDaily", "#laughingOutLoud",
         "#tiredButHappy", "#busyLife", "#everydayStruggles", "#reallifeMemes",
         "#funnyLife", "#memesDaily"],
    ],
    "engagement_questions": [
        ["#questionOfTheDay", "#communityPost", "#shareYourThoughts", "#letsTalk",
         "#commentBelow", "#dailyQuestion", "#talkToMe", "#yourOpinion",
         "#engagement", "#joinTheConversation"],
        ["#askTheCommunity", "#whatDoYouThink", "#conversationStarter", "#yourAnswer",
         "#communityLove", "#brightSideFamily", "#tellMe", "#discussion",
         "#dailychat", "#friendlyDebate"],
        ["#questionTime", "#communityQuestion",
         "#shareYourStory", "#yourTake", "#openQuestion", "#talkToUs",
         "#weekendChat", "#goodConversation", "#thoughts", "#replyBelow"],
    ],
    "bible_quotes": [
        ["#bibleVerse", "#KJV", "#dailyVerse", "#faith", "#hope",
         "#scripture", "#bibleQuotes", "#wordOfGod", "#christianInspiration",
         "#verseOfTheDay"],
        ["#kjvBible", "#bibleDaily", "#faithJourney", "#prayerWarrior", "#blessed",
         "#godIsGood", "#walkByFaith", "#scriptureOfTheDay", "#trustGod",
         "#dailyScripture"],
        ["#bibleTruth", "#christianLiving", "#faithOverFear", "#prayersUp",
         "#wordForToday", "#bibleEncouragement", "#hopeInGod", "#stillStanding",
         "#verseForToday", "#faithfulGod"],
    ],
}

# Extra tags attached only to Bible posts, chosen from the detected news theme.
THEME_TAGS = {
    "conflict": ["#prayForPeace", "#worldPeace"],
    "disaster": ["#prayForTheWorld", "#hopeInHardTimes"],
    "grief": ["#comfortInGrief", "#prayerForComfort"],
    "injustice": ["#justiceAndMercy", "#prayForJustice"],
    "leadership": ["#prayForLeaders", "#wisdomForLeaders"],
    "hope": ["#hopeRestored", "#dailyHope"],
    "fear": ["#fearNot", "#courageInFaith"],
    "general": ["#dailyFaith", "#beEncouraged"],
}

# A short human line between the quote and the call to action. Kept specific
# per category so a meme never gets a motivational closer.
CONTEXT_LINE = {
    "motivational_quotes": "You do not need more time. You need one honest hour. 💛",
    "positive_life_quotes": "A small reminder for an ordinary day ☀️",
    "self_improvement_quotes": "One change, repeated daily, becomes a different life. 📈",
    "gratitude_quotes": "Take a second to notice what is already good 🌿",
    "encouragement_quotes": "For whoever needed to read this today 💛",
    "relatable_quotes": "",
    "meme_captions": "",
    "engagement_questions": "",
    "bible_quotes": "",
}

# One clear ask per category. Saves and shares are the strongest ranking
# signals Instagram uses for quote accounts.
SAVE_CTA = {
    "motivational_quotes": "Save this for the day you need a push 📌",
    "positive_life_quotes": "Save this for a slow morning ☀️",
    "self_improvement_quotes": "Save this and try it this week 📌",
    "gratitude_quotes": "Save this and come back to it tonight 🌙",
    "encouragement_quotes": "Save this for someone who needs it 💛",
    "relatable_quotes": "Send this to the person it describes exactly 😂",
    "meme_captions": "Tag someone who will relate 😂",
    "engagement_questions": "Answer in the comments 👇",
    "bible_quotes": "Save this verse and share it with someone who needs it 🙏",
}


def _rotate(items, salt):
    """Deterministic daily rotation so the same set never repeats twice running."""

    from datetime import date

    index = (date.today().toordinal() + abs(hash(salt)) % 97) % len(items)

    return items[index]


class InstagramPublisher:
    def __init__(self):
        self.mode = (os.environ.get("IG_LOGIN_MODE") or "facebook").strip().lower()
        self.version = os.environ.get("IG_API_VERSION", "v23.0").strip() or "v23.0"
        self.token = _clean(os.environ.get("IG_ACCESS_TOKEN", ""))
        self.dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

        self.user_id = _clean(os.environ.get("IG_USER_ID", ""))

        if self.mode == "instagram":
            # Instagram Login tokens identify the account, so /me is enough.
            self.base_url = f"{INSTAGRAM_HOST}/{self.version}/me"
        else:
            self.mode = "facebook"
            self.base_url = (
                f"{FACEBOOK_HOST}/{self.version}/{self.user_id}"
            )

        if not self.dry_run:
            if not self.token:
                raise EnvironmentError(
                    "Missing IG_ACCESS_TOKEN environment variable."
                )

            if self.mode == "facebook" and not self.user_id:
                raise EnvironmentError(
                    "Missing IG_USER_ID environment variable "
                    "(required for IG_LOGIN_MODE=facebook)."
                )

    # ── Caption ───────────────────────────────────────────────────────────────

    def build_caption(self, post):
        """
        Build a caption optimised for discovery.

        Structure:
          1. The quote itself on the first line (Instagram indexes this text
             for search, and it is what shows before "more").
          2. A short human line of context.
          3. One clear call to action (save or comment).
          4. Rotating hashtag sets, capped well under the 30 limit.
        """

        content = post.get("content", "").strip()
        category = post.get("category", "")
        theme = post.get("world_theme", "")

        parts = [content]

        if category == "bible_quotes":
            pass  # the world agent already adds a respectful, theme-aware line
        elif category == "engagement_questions":
            pass  # the question is already the call to action
        elif CONTEXT_LINE.get(category):
            parts.append(CONTEXT_LINE[category])

        cta = SAVE_CTA.get(category)

        if cta:
            parts.append(cta)

        tags = list(_rotate(HASHTAG_SETS.get(category, HASHTAG_SETS["motivational_quotes"]), category))

        if category == "bible_quotes" and theme:
            tags = THEME_TAGS.get(theme, []) + tags

        # Always keep the community tag last so the set reads consistently.
        tags.append("#BrightSideDaily")

        # Instagram allows 30; staying near 15 protects reach.
        parts.append(" ".join(tag.lower() for tag in tags[:16]))

        return "\n\n".join(parts)

    # ── API calls ─────────────────────────────────────────────────────────────

    def _create_container(self, image_url, caption):
        payload_data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.token,
        }

        # Instagram Collab posts reach both accounts' followers. Opt in by
        # setting IG_COLLABORATORS to a comma-separated list of usernames.
        collaborators = [
            name.strip().lstrip("@")
            for name in (os.environ.get("IG_COLLABORATORS") or "").split(",")
            if name.strip()
        ]

        if collaborators:
            payload_data["collaborators"] = json.dumps(collaborators)

        response = requests.post(
            f"{self.base_url}/media",
            data=payload_data,
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
                f"{FACEBOOK_HOST}/{self.version}/{container_id}",
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
            f"{self.base_url}/media_publish",
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

    # ── Reels and carousels ───────────────────────────────────────────────────

    def _create_reel_container(self, video_url, caption):
        payload_data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.token,
        }

        collaborators = [
            name.strip().lstrip("@")
            for name in (os.environ.get("IG_COLLABORATORS") or "").split(",")
            if name.strip()
        ]

        if collaborators:
            payload_data["collaborators"] = json.dumps(collaborators)

        response = requests.post(
            f"{self.base_url}/media",
            data=payload_data,
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

    def _create_carousel_container(self, image_urls, caption):
        children = []

        for url in image_urls:
            response = requests.post(
                f"{self.base_url}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
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

            children.append(payload["id"])

        payload_data = {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": self.token,
        }

        collaborators = [
            name.strip().lstrip("@")
            for name in (os.environ.get("IG_COLLABORATORS") or "").split(",")
            if name.strip()
        ]

        if collaborators:
            payload_data["collaborators"] = json.dumps(collaborators)

        response = requests.post(
            f"{self.base_url}/media",
            data=payload_data,
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

    def _publish_media(self, post, caption, build_container, storage):
        """Shared publish loop for image, reel and carousel containers."""

        for attempt in range(1, MAX_RETRIES + 1):
            container = build_container()

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

                return {"success": False, "platform": "instagram", **container}

            container_id = container["container_id"]

            if not self._wait_for_container(container_id):
                return {
                    "success": False,
                    "platform": "instagram",
                    "error": "Container did not finish processing.",
                }

            result = self._publish_container(container_id)

            if result["success"]:
                log.info("Instagram post published [%s]", post.get("slot"))
                self._log_success(post, caption, result.get("data", {}))
                return {"success": True, "platform": "instagram", **result}

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

    def publish_reel(self, post, video_path):
        """Publish a vertical MP4 as a Reel."""

        slot = post.get("slot", "unknown")
        caption = self.build_caption(post)

        log.info("Instagram reel [%s] | video: %s", slot, video_path)

        if self.dry_run:
            log.info("[DRY RUN] Reel caption:\n%s", caption)
            return {
                "success": True,
                "dry_run": True,
                "platform": "instagram",
                "media_type": "REELS",
                "slot": slot,
            }

        if not video_path or not Path(video_path).exists():
            return {
                "success": False,
                "platform": "instagram",
                "error": "Reel video not found.",
            }

        storage = SupabaseStorage()
        public_url = storage.upload(video_path)

        try:
            return self._publish_media(
                post,
                caption,
                lambda: self._create_reel_container(public_url, caption),
                storage,
            )
        finally:
            storage.delete(public_url)

    def publish_carousel(self, post, image_paths):
        """Publish 2-10 images as a carousel."""

        slot = post.get("slot", "unknown")
        caption = self.build_caption(post)

        log.info(
            "Instagram carousel [%s] | %d slides",
            slot,
            len(image_paths or []),
        )

        if self.dry_run:
            log.info("[DRY RUN] Carousel caption:\n%s", caption)
            return {
                "success": True,
                "dry_run": True,
                "platform": "instagram",
                "media_type": "CAROUSEL",
                "slides": len(image_paths or []),
                "slot": slot,
            }

        if not image_paths or len(image_paths) < 2:
            return {
                "success": False,
                "platform": "instagram",
                "error": "A carousel needs at least two images.",
            }

        storage = SupabaseStorage()
        urls = [storage.upload(path) for path in image_paths]

        try:
            return self._publish_media(
                post,
                caption,
                lambda: self._create_carousel_container(urls, caption),
                storage,
            )
        finally:
            for url in urls:
                storage.delete(url)

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

    # ── Token maintenance ─────────────────────────────────────────────────────

    @staticmethod
    def refresh_long_lived_token(token=None, version=None):
        """
        Exchange an Instagram Login token for a fresh 60-day token.

        Only valid for IG_LOGIN_MODE=instagram.
        Returns {"access_token": ..., "expires_in": seconds}.
        """

        token = token or os.environ.get("IG_ACCESS_TOKEN", "")
        version = version or os.environ.get("IG_API_VERSION", "v23.0")

        if not token:
            raise EnvironmentError("IG_ACCESS_TOKEN is not set")

        response = requests.get(
            f"{INSTAGRAM_HOST}/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": token,
            },
            timeout=30,
        )

        payload = response.json()

        if response.status_code != 200 or "access_token" not in payload:
            raise RuntimeError(
                f"Token refresh failed ({response.status_code}): "
                f"{response.text[:300]}"
            )

        return payload

    # ── Stories, insights, comments ───────────────────────────────────────────

    def publish_story(self, story_path):
        """Publish a 9:16 image as a Story."""

        if self.dry_run:
            log.info("[DRY RUN] Story would publish: %s", story_path)
            return {"success": True, "dry_run": True, "platform": "instagram"}

        if not story_path or not Path(story_path).exists():
            return {
                "success": False,
                "platform": "instagram",
                "error": "Story image not found.",
            }

        storage = SupabaseStorage()
        public_url = storage.upload(story_path, folder="stories")

        try:
            response = requests.post(
                f"{self.base_url}/media",
                data={
                    "media_type": "STORIES",
                    "image_url": public_url,
                    "access_token": self.token,
                },
                timeout=60,
            )

            payload = response.json()

            if response.status_code != 200 or "id" not in payload:
                return {
                    "success": False,
                    "platform": "instagram",
                    "error": payload.get("error", payload),
                }

            container_id = payload["id"]

            if not self._wait_for_container(container_id):
                return {
                    "success": False,
                    "platform": "instagram",
                    "error": "Story container did not finish processing.",
                }

            result = self._publish_container(container_id)
            result["platform"] = "instagram"
            result["media_type"] = "STORIES"

            if result["success"]:
                log.info("Instagram story published")

            return result

        finally:
            storage.delete(public_url)

    def fetch_media_insights(self, media_id, media_product_type="FEED"):
        """
        Pull saves, shares, reach and engagement for one published post.

        Some metrics are only valid for certain media products, so failures are
        tolerated per metric rather than failing the whole call.
        """

        if media_product_type == "REELS":
            metrics = "reach,likes,comments,shares,saved"
        else:
            metrics = "reach,likes,comments,shares,saved"

        response = requests.get(
            f"{FACEBOOK_HOST}/{self.version}/{media_id}/insights",
            params={
                "metric": metrics,
                "access_token": self.token,
            },
            timeout=30,
        )

        payload = response.json()

        if response.status_code != 200:
            # Retry with the baseline metric set some tokens are limited to.
            response = requests.get(
                f"{FACEBOOK_HOST}/{self.version}/{media_id}/insights",
                params={
                    "metric": "reach,likes,comments,shares",
                    "access_token": self.token,
                },
                timeout=30,
            )
            payload = response.json()

        if response.status_code != 200:
            return {
                "success": False,
                "error": payload.get("error", payload),
            }

        values = {}

        for item in payload.get("data", []):
            values[item.get("name")] = item.get("values", [{}])[0].get("value")

        return {"success": True, "metrics": values}

    def fetch_comments(self, media_id, limit=50):
        """Return recent comments on a published post."""

        response = requests.get(
            f"{FACEBOOK_HOST}/{self.version}/{media_id}/comments",
            params={
                "fields": "id,text,username,timestamp,replies{id,username}",
                "limit": limit,
                "access_token": self.token,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return []

        return response.json().get("data", [])

    def reply_to_comment(self, comment_id, message):
        """Post a reply to a comment."""

        if self.dry_run:
            log.info("[DRY RUN] reply to %s: %s", comment_id, message)
            return {"success": True, "dry_run": True}

        response = requests.post(
            f"{FACEBOOK_HOST}/{self.version}/{comment_id}/replies",
            data={
                "message": message,
                "access_token": self.token,
            },
            timeout=30,
        )

        payload = response.json()

        if response.status_code == 200 and "id" in payload:
            return {"success": True, "id": payload["id"]}

        return {"success": False, "error": payload.get("error", payload)}

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
