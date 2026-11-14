"""
Carousel Generator — Bright Side Daily

Builds a 3-slide Instagram carousel from a post:

    Slide 1  the quote card (the JG monogram card already used for feed posts)
    Slide 2  "Three ways to use this today" — three short actions
    Slide 3  a closing card with the JG signature and a save prompt

Every swipe is an engagement signal, which is why carousels reach further than
single images. All slides are 1080x1350 (4:5), the strongest carousel ratio.
"""

import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generators.black_card_generator import (
    BlackCardGenerator,
    CATEGORY_STYLES,
    FONT_STYLES,
    HEIGHT,
    MARGIN,
    RULE,
    SUBTLE,
    TEXT,
    WIDTH,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output" / "carousel"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BACKGROUND = (10, 10, 12)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("carousel")


# Three concrete actions per category. Written for this project so slide 2 is
# useful rather than filler.
ACTIONS = {
    "motivational_quotes": [
        "Pick the one task you keep postponing. Do ten minutes of it now.",
        "Say the goal out loud to one person who will ask you about it.",
        "Set one reminder for tonight — keep the promise you made this morning.",
    ],
    "positive_life_quotes": [
        "Name three ordinary things that went right today.",
        "Message someone who made your week easier.",
        "Take one slow walk with no headphones.",
    ],
    "self_improvement_quotes": [
        "Choose one habit small enough to do every day this week.",
        "Write down what you will stop doing to make room for it.",
        "Track it for seven days. No skipping, no negotiating.",
    ],
    "gratitude_quotes": [
        "Write one thing you would miss if it disappeared tomorrow.",
        "Thank someone who never gets thanked.",
        "Notice what your body did for you today.",
    ],
    "encouragement_quotes": [
        "Forget the whole mountain. Do the next small step.",
        "Tell one person you are having a hard day.",
        "Give yourself the same kindness you would offer a friend.",
    ],
    "bible_quotes": [
        "Read the verse again, slowly, out loud.",
        "Write it somewhere you will see it tomorrow.",
        "Pray it for someone else who needs it today.",
    ],
    "meme_captions": [
        "Send this to the person who is literally this.",
        "Tag someone who needs to be called out.",
        "Save it for the next time you do the exact same thing.",
    ],
    "engagement_questions": [
        "Answer in one honest sentence.",
        "Read the comments before you reply.",
        "Come back tomorrow for the next one.",
    ],
}

DEFAULT_ACTIONS = ACTIONS["motivational_quotes"]


def _font(style_name, size, bold=True):
    style = FONT_STYLES[style_name]
    candidates = style["bold"] if bold else style["regular"]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def _spaced(text, amount=3):
    return (" " * amount).join(list(text))


def _background(accent_dim=False):
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    glow = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(glow)

    steps = 24
    for i in range(steps, 0, -1):
        ratio = i / steps
        rx = int(WIDTH * 0.6 * ratio)
        ry = int(HEIGHT * 0.48 * ratio)
        value = int(8 * (1 - ratio) + 2)

        draw.ellipse(
            (
                WIDTH // 2 - rx,
                HEIGHT // 2 - ry,
                WIDTH // 2 + rx,
                HEIGHT // 2 + ry,
            ),
            fill=value,
        )

    return Image.composite(
        Image.new("RGB", (WIDTH, HEIGHT), (25, 25, 29)),
        image,
        glow,
    )


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


def _slide_actions(post, accent, style_name):
    """Slide 2 — three concrete actions."""

    image = _background()
    draw = ImageDraw.Draw(image)

    label_font = _font(style_name, 25, bold=True)
    label = _spaced("TRY THIS TODAY")

    label_w = draw.textbbox((0, 0), label, font=label_font)[2]
    draw.text(((WIDTH - label_w) // 2, 150), label, font=label_font, fill=accent)

    draw.line((WIDTH // 2 - 45, 208, WIDTH // 2 + 45, 208), fill=accent, width=3)

    actions = ACTIONS.get(post.get("category", ""), DEFAULT_ACTIONS)

    number_font = _font(style_name, 54, bold=True)
    body_font = _font(style_name, 34, bold=False)

    y = 320
    max_width = WIDTH - MARGIN * 2 - 90

    for index, action in enumerate(actions[:3], start=1):
        draw.text((MARGIN, y - 6), str(index), font=number_font, fill=accent)

        lines = _wrap(draw, action, body_font, max_width)

        line_y = y
        for line in lines:
            draw.text((MARGIN + 90, line_y), line, font=body_font, fill=TEXT)
            line_y += 46

        y = line_y + 62

    draw.line((MARGIN, HEIGHT - 232, WIDTH - MARGIN, HEIGHT - 232), fill=RULE, width=2)

    return image


def _slide_closing(style_name, accent):
    """Slide 3 — signature and save prompt."""

    image = _background()
    draw = ImageDraw.Draw(image)

    big_font = _font(style_name, 52, bold=True)
    small_font = _font(style_name, 30, bold=False)

    lines = ["Save this one.", "Come back when you need it."]

    y = 520
    for line in lines:
        wrapped = _wrap(draw, line, big_font, WIDTH - MARGIN * 2)

        for piece in wrapped:
            width = draw.textbbox((0, 0), piece, font=big_font)[2]
            draw.text(((WIDTH - width) // 2, y), piece, font=big_font, fill=TEXT)
            y += 68

    # Monogram
    centre_x = WIDTH // 2
    centre_y = HEIGHT - 300
    radius = 68

    draw.ellipse(
        (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius),
        outline=accent,
        width=2,
    )
    draw.line((centre_x - radius - 46, centre_y, centre_x - radius - 12, centre_y), fill=accent, width=2)
    draw.line((centre_x + radius + 12, centre_y, centre_x + radius + 46, centre_y), fill=accent, width=2)

    signature = (os.getenv("IG_SIGNATURE", "JG").strip().upper() or "JG")
    draw.text(
        (centre_x, centre_y - 2),
        _spaced(signature, 1),
        font=_font(style_name, 38, bold=True),
        fill=TEXT,
        anchor="mm",
    )

    hint = "New post every morning"
    hint_w = draw.textbbox((0, 0), hint, font=small_font)[2]
    draw.text(((WIDTH - hint_w) // 2, HEIGHT - 170), hint, font=small_font, fill=SUBTLE)

    return image


def generate(post, output_dir=None):
    """
    Build the three carousel slides.

    Returns a list of file paths in posting order.
    """

    style_name = CATEGORY_STYLES.get(post.get("category", ""), "modern")
    accent = FONT_STYLES[style_name]["accent"]

    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    slot = post.get("slot", "post")
    index = post.get("content_index", 0)

    paths = []

    # Slide 1 — the standard quote card
    slide_one = BlackCardGenerator().generate(
        post,
        output_path=out_dir / f"{slot}_{index}_1.jpg",
    )
    paths.append(slide_one)

    # Slide 2 — actions
    slide_two = _slide_actions(post, accent, style_name)
    slide_two_path = out_dir / f"{slot}_{index}_2.jpg"
    slide_two.save(slide_two_path, "JPEG", quality=92, optimize=True)
    paths.append(str(slide_two_path))

    # Slide 3 — closing
    slide_three = _slide_closing(style_name, accent)
    slide_three_path = out_dir / f"{slot}_{index}_3.jpg"
    slide_three.save(slide_three_path, "JPEG", quality=92, optimize=True)
    paths.append(str(slide_three_path))

    log.info("Carousel ready: %d slides for %s", len(paths), slot)

    return paths
