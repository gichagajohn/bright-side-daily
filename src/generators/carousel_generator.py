"""
Carousel Generator — Bright Side Daily

Builds a 2-slide Instagram carousel from a post:

    Slide 1  the quote card (the JG monogram card already used for feed posts)
    Slide 2  "Try this today" — three short actions for the quote's category

Every swipe is an engagement signal, which is why carousels reach further than
single images. Both slides are 1080x1350 (4:5), the strongest carousel ratio.

A third "save this one" slide was removed on request — the monogram already
appears on slide 1, so nothing was lost by cutting it.
"""

import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generators.black_card_generator import (
    resolve_font,
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


# Slide 2 copy. Each category holds several three-action variants and the
# carousel rotates through them by content_index, so consecutive quotes never
# ship the same advice twice in a row. Add a variant by appending a triple.
ACTIONS = {
    "motivational_quotes": [
        ["Pick the one task you keep postponing. Do ten minutes of it now.",
         "Say the goal out loud to one person who will ask you about it.",
         "Set one reminder for tonight — keep the promise you made this morning."],
        ["Choose the smallest version of the thing you are avoiding.",
         "Start before you feel ready. Feelings follow action, not the reverse.",
         "Stop at ten minutes even if it is going well, so tomorrow you want to return."],
        ["Write the goal on paper and put it where you look first in the morning.",
         "Tell one person the deadline, not the dream.",
         "Do the hard part before you open your phone."],
        ["Name the excuse you used this week. Just name it, out loud.",
         "Replace \u201cI do not have time\u201d with what you actually chose instead.",
         "Take one action today that your future self would thank you for."],
        ["Pick one thing to finish today, not start.",
         "Close every other tab, literally and mentally.",
         "Do not move on until it is done and you have looked at it once."],
        ["Look at what worked last week and copy one part of it deliberately.",
         "Cut one thing from today's list instead of adding another.",
         "Tell someone what you are working on so you cannot quietly quit."],
    ],
    "positive_life_quotes": [
        ["Name three ordinary things that went right today.",
         "Message someone who made your week easier.",
         "Take one slow walk with no headphones."],
        ["Notice one thing you usually walk past. Look at it properly.",
         "Say thank you out loud to someone today.",
         "Keep the phone face-down for the first ten minutes of your morning."],
        ["Find one small thing that is working. Write it down.",
         "Do one thing today for no reason other than you enjoy it.",
         "Spend ten minutes somewhere green, or next to an open window."],
        ["Send someone a photo of something that reminded you of them.",
         "Eat one meal today without a screen in front of you.",
         "Sit for two minutes doing absolutely nothing. Time it."],
        ["Count what you have that money cannot replace.",
         "Say no to one thing that drains you this week.",
         "Do something that would make a child in your life smile."],
        ["Go to a place you love this week, even for fifteen minutes.",
         "Play a song you loved years ago, all the way through.",
         "Tell someone a memory of them that they have forgotten."],
    ],
    "self_improvement_quotes": [
        ["Choose one habit small enough to do every day this week.",
         "Write down what you will stop doing to make room for it.",
         "Track it for seven days. No skipping, no negotiating."],
        ["Pick a habit you can complete in under five minutes.",
         "Attach it to something you already do — after coffee, before bed.",
         "Mark it on a calendar. Seeing the unbroken chain is the reward."],
        ["Choose one area of your life and write the honest version of where you are.",
         "Name the one behaviour that keeps you there.",
         "Change only that behaviour for two weeks. Nothing else."],
        ["Identify the time of day you have the most energy.",
         "Move your hardest task into that exact window.",
         "Protect that window from meetings and messages."],
        ["Write down the thing you keep saying you will do \u201csomeday\u201d.",
         "Decide whether you want it or just like the idea of it.",
         "If you want it, give it a date this month."],
        ["Spend ten minutes reviewing the last week — what worked, what did not.",
         "Keep one thing. Drop one thing.",
         "Do the same review next Sunday, at the same time."],
    ],
    "gratitude_quotes": [
        ["Write one thing you would miss if it disappeared tomorrow.",
         "Thank someone who never gets thanked.",
         "Notice what your body did for you today."],
        ["Name the person who made today easier.",
         "Tell them, specifically, what they did.",
         "Recall one hard day that turned out better than you feared."],
        ["Write down three things from the last twenty-four hours. Small counts.",
         "Put one of them somewhere you will see it tomorrow.",
         "Send one message of thanks before you sleep."],
        ["Look around the room and name one thing you rely on daily.",
         "Notice who keeps it working.",
         "Say thank you where it is usually assumed."],
        ["Think of a meal you ate today and trace it back to who made it possible.",
         "Thank one person in that chain.",
         "Eat one meal slowly this week with nothing else going on."],
        ["Write down something difficult you got through this year.",
         "Name what actually got you through it.",
         "Thank the version of you who kept going."],
    ],
    "encouragement_quotes": [
        ["Forget the whole mountain. Do the next small step.",
         "Tell one person you are having a hard day.",
         "Give yourself the same kindness you would offer a friend."],
        ["Lower today's expectation until it is something you can actually do.",
         "Do that one thing.",
         "Count it as a win, out loud, where someone can hear you."],
        ["Write down what is actually wrong, in one sentence.",
         "Separate what you can change today from what you cannot.",
         "Act only on the first list. Leave the second alone."],
        ["Drink water. Eat something. Sit down.",
         "Then look at the problem again.",
         "Most of it looks smaller than it did an hour ago."],
        ["Ask for one specific thing from one specific person today.",
         "Say what you need in plain words, not hints.",
         "Do not apologise for needing it."],
        ["Stop trying to fix everything at once.",
         "Pick the single most urgent thing.",
         "Let the rest stay unfinished today. It will keep."],
    ],
    "bible_quotes": [
        ["Read the verse again, slowly, out loud.",
         "Write it somewhere you will see it tomorrow.",
         "Pray it for someone else who needs it today."],
        ["Copy the verse into your notes by hand.",
         "Underline the one word that stops you.",
         "Ask why that word, today, of all days."],
        ["Read the verse in the morning and again before you sleep.",
         "Notice what changed in between.",
         "Write one sentence about it."],
        ["Say the verse out loud before you decide anything today.",
         "Let it set the tone, not the task list.",
         "Return to it when the day gets loud."],
        ["Send the verse to one person who needs it more than you do.",
         "Do not explain it. Just send it.",
         "Pray for them by name."],
        ["Sit with the verse for two quiet minutes.",
         "Do not analyse it or look anything up.",
         "Just let it land."],
    ],
    "meme_captions": [
        ["Send this to the person who is literally this.",
         "Tag someone who needs to be called out.",
         "Save it for the next time you do the exact same thing."],
        ["Send it to the group chat without context.",
         "Tag the friend who invented this behaviour.",
         "Screenshot it for your own records."],
        ["Send to the one person who will reply in capital letters.",
         "Tag someone who does this and denies it.",
         "Save it for Monday morning."],
    ],
    "engagement_questions": [
        ["Answer in one honest sentence.",
         "Read the comments before you reply to anyone.",
         "Come back tomorrow for the next one."],
        ["Answer with the first thing that comes to mind.",
         "Reply to one other person's answer.",
         "Share it with someone who would answer differently."],
        ["Answer honestly, not cleverly.",
         "Read three answers before you write yours.",
         "Come back at the end of the day and see what changed."],
    ],
}

DEFAULT_ACTIONS = ACTIONS["motivational_quotes"][0]


def _actions_for(post):
    """Pick this post's three actions, rotating by content_index."""

    variants = ACTIONS.get(post.get("category", ""), ACTIONS["motivational_quotes"])
    index = int(post.get("content_index") or 0)

    return variants[index % len(variants)]


def _font(style_name, size, bold=True):
    """Resolve a font for the category's style, falling back safely."""

    style = FONT_STYLES.get(style_name, FONT_STYLES["modern"])
    candidates = style["bold"] if bold else style["regular"]

    return resolve_font(candidates, size, bold)


def _spaced(text, tracking=1):
    """Letter-spaced small caps that keeps the gaps between words."""

    if not tracking:
        return text

    separator = " " * tracking
    return ("   ").join(separator.join(word) for word in text.split())


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

    actions = _actions_for(post)

    number_font = _font(style_name, 54, bold=True)
    body_font = _font(style_name, 34, bold=False)

    y = 320
    max_width = WIDTH - MARGIN * 2 - 120

    for index, action in enumerate(actions[:3], start=1):
        draw.text((MARGIN, y - 6), str(index), font=number_font, fill=accent)

        lines = _wrap(draw, action, body_font, max_width)

        line_y = y
        for line in lines:
            draw.text((MARGIN + 90, line_y), line, font=body_font, fill=TEXT)
            line_y += 46

        y = line_y + 62

    return image


def generate(post, output_dir=None):
    """
    Build the two carousel slides.

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

    log.info("Carousel ready: %d slides for %s", len(paths), slot)

    return paths
