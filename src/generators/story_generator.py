"""
Story Generator — Bright Side Daily

Builds 1080x1920 Instagram Story images from a quote card.

Stories keep existing followers engaged, which feeds future post reach.
Two variants are produced:

    poll   — a two-option poll holder at the bottom
    plain  — card plus a "reply" prompt

Instagram does not let the API publish native sticker elements, so the poll is
drawn into the artwork. Viewers reply to it like any normal story sticker frame.
"""

import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generators.black_card_generator import (
    CATEGORY_STYLES,
    FONT_STYLES,
    SUBTLE,
    TEXT,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output" / "stories"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
BACKGROUND = (10, 10, 12)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("story_generator")


# Two-option polls per category. One tap is the cheapest possible engagement.
POLLS = {
    "motivational_quotes": ("Needed this today", "Sending it to a friend"),
    "positive_life_quotes": ("Made me smile", "Made me think"),
    "self_improvement_quotes": ("Trying this", "Already doing this"),
    "gratitude_quotes": ("Feeling grateful", "Could use the reminder"),
    "encouragement_quotes": ("I needed this", "Know someone who does"),
    "bible_quotes": ("Amen 🙏", "Praying for someone"),
    "meme_captions": ("This is me", "This is my friend"),
    "engagement_questions": ("Answering below", "Reading the answers"),
}


def _font(style_name, size, bold=True):
    style = FONT_STYLES[style_name]
    candidates = style["bold"] if bold else style["regular"]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def _spaced(text, amount=3):
    return (" " * amount).join(list(text))


def _rounded(draw, box, radius, fill=None, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()

        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def generate(post, output_path=None, variant="poll"):
    """
    Build a vertical Story image.

    variant: "poll" or "plain"
    """

    style_name = CATEGORY_STYLES.get(post.get("category", ""), "modern")
    accent = FONT_STYLES[style_name]["accent"]

    card_path = post.get("_card_path")
    content = (post.get("content") or "").strip()

    if not content:
        raise ValueError("Story needs post content")

    # Bible posts lead with the reference; keep the verse only on the story.
    reference = post.get("bible_reference", "")
    if reference and content.startswith(reference):
        content = content[len(reference):].lstrip()

        for prefix in ("KJV", "-", "—", ":", "|"):
            if content.startswith(prefix):
                content = content[len(prefix):].lstrip()

    if reference and "\n\n" in content:
        content = content.split("\n\n")[0].strip()

    if post.get("category") in ("meme_captions", "engagement_questions"):
        content = content.upper()

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image, "RGBA")

    # ── Header ───────────────────────────────────────────────────────────────
    label_font = _font(style_name, 26, bold=True)
    label = _spaced((os.getenv("IG_SIGNATURE", "JG") or "JG").upper() + "  ·  BRIGHT SIDE")

    label_w = draw.textbbox((0, 0), label, font=label_font)[2]
    draw.text(((WIDTH - label_w) // 2, 150), label, font=label_font, fill=accent)

    # ── Quote, auto-fitted ───────────────────────────────────────────────────
    max_width = WIDTH - 180
    max_height = 900

    font = None
    lines = []

    for size in range(84, 34, -3):
        trial_font = _font(style_name, size, bold=True)
        trial_lines = _wrap(draw, content, trial_font, max_width)
        line_height = int(size * 1.35)

        widest = max(
            (draw.textbbox((0, 0), line, font=trial_font)[2] for line in trial_lines),
            default=0,
        )

        if line_height * len(trial_lines) <= max_height and widest <= max_width:
            font = trial_font
            lines = trial_lines
            break

    if font is None:
        font = _font(style_name, 34, bold=True)
        lines = _wrap(draw, content, font, max_width)

    line_height = int(font.size * 1.35)
    total = line_height * len(lines)
    y = (HEIGHT - total) // 2 - 60

    if reference:
        ref_font = _font(style_name, 36, bold=True)
        ref_w = draw.textbbox((0, 0), reference, font=ref_font)[2]
        draw.text(((WIDTH - ref_w) // 2, y - 90), reference, font=ref_font, fill=accent)

    for line in lines:
        width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((WIDTH - width) // 2, y), line, font=font, fill=TEXT)
        y += line_height

    # ── Footer block ─────────────────────────────────────────────────────────
    if variant == "poll":
        option_a, option_b = POLLS.get(
            post.get("category", ""),
            ("Yes", "Not yet"),
        )

        box_top = HEIGHT - 520
        _rounded(
            draw,
            (90, box_top, WIDTH - 90, box_top + 250),
            radius=32,
            outline=accent,
            width=3,
        )

        prompt_font = _font(style_name, 34, bold=True)
        prompt = "Tap to answer"
        prompt_w = draw.textbbox((0, 0), prompt, font=prompt_font)[2]
        draw.text(
            ((WIDTH - prompt_w) // 2, box_top + 32),
            prompt,
            font=prompt_font,
            fill=SUBTLE,
        )

        option_font = _font(style_name, 36, bold=True)

        for index, option in enumerate((option_a, option_b)):
            top = box_top + 100 + index * 72
            _rounded(
                draw,
                (130, top, WIDTH - 130, top + 58),
                radius=29,
                outline=(70, 70, 78),
                width=2,
            )

            width = draw.textbbox((0, 0), option, font=option_font)[2]
            draw.text(
                ((WIDTH - width) // 2, top + 10),
                option,
                font=option_font,
                fill=TEXT,
            )
    else:
        prompt_font = _font(style_name, 32, bold=False)
        prompt = "Reply with the line you needed today"
        prompt_w = draw.textbbox((0, 0), prompt, font=prompt_font)[2]
        draw.text(
            ((WIDTH - prompt_w) // 2, HEIGHT - 380),
            prompt,
            font=prompt_font,
            fill=SUBTLE,
        )

    # ── Monogram ─────────────────────────────────────────────────────────────
    centre_x = WIDTH // 2
    centre_y = HEIGHT - 190
    radius = 58

    draw.ellipse(
        (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius),
        outline=accent,
        width=2,
    )

    signature = (os.getenv("IG_SIGNATURE", "JG").strip().upper() or "JG")
    draw.text(
        (centre_x, centre_y - 2),
        _spaced(signature, 1),
        font=_font(style_name, 34, bold=True),
        fill=TEXT,
        anchor="mm",
    )

    if output_path is None:
        slot = post.get("slot", "post")
        index = post.get("content_index", 0)
        output_path = OUTPUT_DIR / f"{slot}_{index}_{variant}.jpg"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "JPEG", quality=92, optimize=True)

    log.info("Story ready: %s", output_path)

    return str(output_path)
