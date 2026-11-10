"""
Black Card Generator — Bright Side Daily (Instagram edition)

Creates elegant black-background quote cards for Instagram:
  - 1080 x 1350 (4:5 portrait, the best-performing Instagram ratio)
  - Pure near-black background with a soft radial glow
  - Category-specific typography (modern / elegant / playful)
  - A stylish "JG" monogram signature at the bottom of every card
    (no brand name is printed on the image)
  - Automatic text fitting so nothing ever overflows

Instagram has no text-only posts, so every slot still produces
a real, fully designed image — it is simply a designed card
instead of a stock photo.
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output" / "instagram"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1080
HEIGHT = 1350
MARGIN = 90

SIGNATURE_FONT = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]

BACKGROUND = (10, 10, 12)
TEXT = (255, 255, 255)
SUBTLE = (150, 150, 158)
RULE = (48, 48, 54)

# ── Typography ────────────────────────────────────────────────────────────────
FONT_STYLES = {
    "modern": {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "regular": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "accent": (88, 196, 255),
        "uppercase": False,
    },
    "elegant": {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ],
        "regular": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ],
        "accent": (214, 183, 111),
        "uppercase": False,
    },
    "playful": {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ],
        "regular": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "accent": (255, 214, 64),
        "uppercase": True,
    },
}

CATEGORY_STYLES = {
    "motivational_quotes": "modern",
    "self_improvement_quotes": "modern",
    "encouragement_quotes": "modern",
    "positive_life_quotes": "elegant",
    "gratitude_quotes": "elegant",
    "bible_quotes": "elegant",
    "meme_captions": "playful",
    "engagement_questions": "playful",
}

CATEGORY_LABELS = {
    "motivational_quotes": "DAILY MOTIVATION",
    "self_improvement_quotes": "SELF IMPROVEMENT",
    "encouragement_quotes": "ENCOURAGEMENT",
    "positive_life_quotes": "POSITIVE LIVING",
    "gratitude_quotes": "GRATITUDE",
    "bible_quotes": "VERSE OF THE DAY",
    "meme_captions": "TODAY'S MOOD",
    "engagement_questions": "QUESTION OF THE DAY",
}


class BlackCardGenerator:
    """Render a quote onto a black background card."""

    def __init__(self):
        # Only the initials appear on the image, never the full handle.
        self.signature = (
            os.getenv("IG_SIGNATURE", "JG").strip().upper() or "JG"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _style_name(self, post):
        return CATEGORY_STYLES.get(post.get("category", ""), "modern")

    @staticmethod
    def _font(style_name, size, bold=True):
        style = FONT_STYLES[style_name]
        candidates = style["bold"] if bold else style["regular"]

        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)

        return ImageFont.load_default()

    @staticmethod
    def _signature_font(size):
        for path in SIGNATURE_FONT:
            if Path(path).exists():
                return ImageFont.truetype(path, size)

        return ImageFont.load_default()

    def _draw_signature(self, draw, accent):
        """Draw a stylish circled monogram (e.g. JG) as the signature."""

        centre_x = WIDTH // 2
        centre_y = HEIGHT - 128
        radius = 68

        # Thin accent ring
        draw.ellipse(
            (
                centre_x - radius,
                centre_y - radius,
                centre_x + radius,
                centre_y + radius,
            ),
            outline=accent,
            width=2,
        )

        # Small accent ticks either side of the ring
        draw.line(
            (centre_x - radius - 46, centre_y, centre_x - radius - 12, centre_y),
            fill=accent,
            width=2,
        )
        draw.line(
            (centre_x + radius + 12, centre_y, centre_x + radius + 46, centre_y),
            fill=accent,
            width=2,
        )

        # Monogram initials
        draw.text(
            (centre_x, centre_y - 2),
            self._spaced(self.signature, 1),
            font=self._signature_font(38),
            fill=TEXT,
            anchor="mm",
        )

    def _background(self):
        """Near-black base with a very soft centre glow."""

        image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
        glow = Image.new("L", (WIDTH, HEIGHT), 0)
        glow_draw = ImageDraw.Draw(glow)

        steps = 26
        for i in range(steps, 0, -1):
            ratio = i / steps
            rx = int(WIDTH * 0.62 * ratio)
            ry = int(HEIGHT * 0.5 * ratio)
            value = int(9 * (1 - ratio) + 2)

            glow_draw.ellipse(
                (
                    WIDTH // 2 - rx,
                    HEIGHT // 2 - ry,
                    WIDTH // 2 + rx,
                    HEIGHT // 2 + ry,
                ),
                fill=value,
            )

        image = Image.composite(
            Image.new("RGB", (WIDTH, HEIGHT), (26, 26, 30)),
            image,
            glow,
        )

        return image

    # ── Text fitting ──────────────────────────────────────────────────────────

    def _wrap(self, draw, text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            trial = f"{current} {word}".strip()
            width = draw.textbbox((0, 0), trial, font=font)[2]

            if width <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def _fit(self, draw, text, style_name, max_width, max_height):
        """Find the largest font size where the wrapped text still fits."""

        for size in range(92, 34, -3):
            font = self._font(style_name, size, bold=True)
            lines = self._wrap(draw, text, font, max_width)

            line_height = int(size * 1.35)
            total_height = line_height * len(lines)

            widest = max(
                (draw.textbbox((0, 0), line, font=font)[2] for line in lines),
                default=0,
            )

            if total_height <= max_height and widest <= max_width:
                return font, lines, line_height

        font = self._font(style_name, 34, bold=True)
        return font, self._wrap(draw, text, font, max_width), 46

    # ── Render ────────────────────────────────────────────────────────────────

    def generate(self, post, output_path=None):
        """Build the black card and return its file path."""

        style_name = self._style_name(post)
        style = FONT_STYLES[style_name]

        content = (post.get("content") or "").strip()
        if not content:
            raise ValueError("Post has no content to render")

        # Bible posts read better with the reference separated from the verse.
        verse_reference = post.get("bible_reference", "")

        if verse_reference and content.startswith(verse_reference):
            content = content[len(verse_reference):].lstrip()

            for prefix in ("KJV", "-", "—", ":", "|"):
                if content.startswith(prefix):
                    content = content[len(prefix):].lstrip()

        # Drop the trailing pastoral note so the card stays clean.
        if verse_reference and "\n\n" in content:
            content = content.split("\n\n")[0].strip()

        if style["uppercase"]:
            content = content.upper()

        image = self._background()
        draw = ImageDraw.Draw(image)

        label = CATEGORY_LABELS.get(
            post.get("category", ""),
            "TODAY'S POST",
        )

        # ── Top label ─────────────────────────────────────────────────────────
        label_font = self._font(style_name, 26, bold=True)
        label_spacing = self._spaced(label)

        label_width = draw.textbbox((0, 0), label_spacing, font=label_font)[2]
        draw.text(
            ((WIDTH - label_width) // 2, 150),
            label_spacing,
            font=label_font,
            fill=style["accent"],
        )

        # ── Short accent rule ─────────────────────────────────────────────────
        rule_y = 210
        draw.line(
            (WIDTH // 2 - 45, rule_y, WIDTH // 2 + 45, rule_y),
            fill=style["accent"],
            width=3,
        )

        # ── Bible reference (accent line above the verse) ─────────────────────
        if verse_reference:
            reference_font = self._font(style_name, 40, bold=True)
            reference_text = verse_reference
            reference_width = draw.textbbox(
                (0, 0), reference_text, font=reference_font
            )[2]

            draw.text(
                ((WIDTH - reference_width) // 2, 262),
                reference_text,
                font=reference_font,
                fill=style["accent"],
            )

        # ── Main quote ────────────────────────────────────────────────────────
        max_width = WIDTH - (MARGIN * 2)
        font, lines, line_height = self._fit(
            draw,
            content,
            style_name,
            max_width,
            max_height=640 if verse_reference else 700,
        )

        total_height = line_height * len(lines)
        y = (HEIGHT - total_height) // 2 - (60 if verse_reference else 10)

        for line in lines:
            width = draw.textbbox((0, 0), line, font=font)[2]
            draw.text(
                ((WIDTH - width) // 2, y),
                line,
                font=font,
                fill=TEXT,
            )
            y += line_height

        # ── Divider above the signature ───────────────────────────────────────
        draw.line(
            (MARGIN, HEIGHT - 232, WIDTH - MARGIN, HEIGHT - 232),
            fill=RULE,
            width=2,
        )

        # ── JG monogram signature (the only branding on the card) ─────────────
        self._draw_signature(draw, style["accent"])

        # ── Save ──────────────────────────────────────────────────────────────
        if output_path is None:
            slot = post.get("slot", "post")
            index = post.get("content_index", 0)
            output_path = OUTPUT_DIR / f"{slot}_{index}.jpg"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        image.save(output_path, "JPEG", quality=92, optimize=True)
        return str(output_path)

    @staticmethod
    def _spaced(text, amount=3):
        """Letter-spaced text for the small caps labels."""

        return (" " * amount).join(list(text))
