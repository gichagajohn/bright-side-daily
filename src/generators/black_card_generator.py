"""
Black Card Generator — Bright Side Daily (Instagram edition)

Creates black-background quote cards for Instagram:
  - 1080 x 1350 (4:5 portrait, the best-performing Instagram ratio)
  - Pure near-black background with a soft radial glow
  - Category-specific typography (modern / elegant / playful)
  - Automatic text fitting so nothing ever overflows

Two layouts, chosen with IG_CARD_STYLE:

    tweet    (default) modelled on a social post: left aligned, regular
             weight, generous black space, no label, no monogram.
    plain    just the words, centred. No category label, no rule, no
             monogram. The quote is the whole card.
    branded  the earlier layout: small caps label, accent rule, divider
             and the JG monogram.

IG_MONOGRAM=on brings the monogram back on its own, in either layout.

Tweet layout tuning (all measure against a 1080px wide card):
    IG_CARD_FONT_SIZE    51    ~4.8% of the card width
    IG_CARD_LINE_HEIGHT  1.30
    IG_CARD_PADDING      72    left and right inset
    IG_CARD_HANDLE       ""    optional grey line under the quote
A Bible reference is always printed regardless of layout — a verse
without its citation is not publishable.

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

# Every style resolves through this list as a last resort. Without it, a
# missing font silently degrades to Pillow's 11px bitmap default, which puts a
# speck of text on a 1080px card and still reports success.
FONT_FALLBACK_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
]

FONT_FALLBACK_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
]


def resolve_font(candidates, size, bold):
    """Return the first font that exists, or raise RuntimeError.

    Raising is deliberate: a missing font must fail the run, not silently
    publish a card with an 11px speck on it.
    """

    chain = list(candidates) + (
        FONT_FALLBACK_BOLD if bold else FONT_FALLBACK_REGULAR
    )

    tried = []

    for path in chain:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception as exc:            # unreadable or corrupt file
                tried.append(f"{path} ({exc})")
                continue
        tried.append(path)

    raise RuntimeError(
        "No usable TrueType font found. Install fonts-dejavu-core "
        "(sudo apt-get install -y fonts-dejavu-core). Tried: "
        + ", ".join(tried[:4])
        + ("..." if len(tried) > 4 else "")
    )


CATEGORY_STYLES = {
    "motivational_quotes": "modern",
    "self_improvement_quotes": "modern",
    "encouragement_quotes": "modern",
    "positive_life_quotes": "elegant",
    "gratitude_quotes": "elegant",
    "bible_quotes": "elegant",
    "meme_captions": "playful",
    "engagement_questions": "playful",
    "relatable_quotes": "modern",
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
    "relatable_quotes": "RELATABLE",
}


class BlackCardGenerator:
    """Render a quote onto a black background card."""

    def __init__(self):
        # Only the initials appear on the image, never the full handle.
        self.signature = (
            os.getenv("IG_SIGNATURE", "JG").strip().upper() or "JG"
        )

        style = (os.getenv("IG_CARD_STYLE") or "tweet").strip().lower()
        self.style = style
        self.tweet = style == "tweet"
        self.plain = style in {"plain", "tweet"}

        # Tweet layout: left aligned, regular weight, lots of black.
        # Defaults are scaled from a measured reference (51px on a 1080 card,
        # 1.30 line height, left aligned) so the proportions match exactly.
        self.tweet_size = int(os.getenv("IG_CARD_FONT_SIZE", "51"))
        self.tweet_leading = float(os.getenv("IG_CARD_LINE_HEIGHT", "1.30"))
        self.tweet_pad = int(os.getenv("IG_CARD_PADDING", "72"))
        self.handle = (os.getenv("IG_CARD_HANDLE") or "").strip()

        # Monogram defaults off in plain layout, on in branded.
        monogram = os.getenv("IG_MONOGRAM")
        if monogram is None:
            self.monogram = not self.plain
        else:
            self.monogram = monogram.strip().lower() in {"1", "on", "true", "yes"}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _style_name(self, post):
        return CATEGORY_STYLES.get(post.get("category", ""), "modern")

    @staticmethod
    def _font(style_name, size, bold=True):
        style = FONT_STYLES.get(style_name, FONT_STYLES["modern"])
        candidates = style["bold"] if bold else style["regular"]

        return resolve_font(candidates, size, bold)

    @staticmethod
    def _signature_font(size):
        return resolve_font(SIGNATURE_FONT, size, bold=True)

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
        verse_reference = (
            post.get("bible_reference") or post.get("reference") or ""
        )

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

        if not self.plain:
            # ── Top label ─────────────────────────────────────────────────────
            label_font = self._font(style_name, 26, bold=True)
            label_spacing = self._spaced(label)

            label_width = draw.textbbox((0, 0), label_spacing, font=label_font)[2]
            draw.text(
                ((WIDTH - label_width) // 2, 150),
                label_spacing,
                font=label_font,
                fill=style["accent"],
            )

            # ── Short accent rule ─────────────────────────────────────────────
            rule_y = 210
            draw.line(
                (WIDTH // 2 - 45, rule_y, WIDTH // 2 + 45, rule_y),
                fill=style["accent"],
                width=3,
            )

        # ── Bible reference (accent line above the verse) ─────────────────────
        if verse_reference and not self.tweet:
            reference_font = self._font(style_name, 40, bold=True)
            reference_text = verse_reference
            reference_width = draw.textbbox(
                (0, 0), reference_text, font=reference_font
            )[2]

            reference_y = 400 if self.plain else 262
            draw.text(
                ((WIDTH - reference_width) // 2, reference_y),
                reference_text,
                font=reference_font,
                fill=style["accent"],
            )

        # ── Tweet layout: words only, left aligned ────────────────────────────
        if self.tweet:
            self._render_tweet(image, draw, content, style, verse_reference)

            if output_path is None:
                slot = post.get("slot", "post")
                index = post.get("content_index", 0)
                output_path = OUTPUT_DIR / f"{slot}_{index}.jpg"

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "JPEG", quality=92, optimize=True)
            return str(output_path)

        # ── Main quote ────────────────────────────────────────────────────────
        # Plain layout has the whole frame to itself, so it can run wider and
        # taller than the branded one.
        max_width = WIDTH - (MARGIN * (1 if self.plain else 2))
        max_height = 900 if self.plain else (640 if verse_reference else 700)

        font, lines, line_height = self._fit(
            draw,
            content,
            style_name,
            max_width,
            max_height=max_height,
        )

        total_height = line_height * len(lines)
        y = (HEIGHT - total_height) // 2 - (60 if verse_reference else 10)

        if self.plain and verse_reference:
            y -= 30

        for line in lines:
            width = draw.textbbox((0, 0), line, font=font)[2]
            draw.text(
                ((WIDTH - width) // 2, y),
                line,
                font=font,
                fill=TEXT,
            )
            y += line_height

        if self.monogram:
            # ── Divider above the signature ───────────────────────────────────
            draw.line(
                (MARGIN, HEIGHT - 232, WIDTH - MARGIN, HEIGHT - 232),
                fill=RULE,
                width=2,
            )

            # ── JG monogram (the only branding on the card) ───────────────────
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

    # ── Tweet-style layout ────────────────────────────────────────────────────

    def _tweet_lines(self, draw, content):
        """Wrap at the tweet font size, left aligned."""

        font = self._font("modern", self.tweet_size, bold=False)
        max_width = WIDTH - (self.tweet_pad * 2)

        words = content.split()
        lines, current = [], ""

        for word in words:
            trial = f"{current} {word}".strip()

            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

        return font, lines

    def _render_tweet(self, image, draw, content, style, reference=""):
        """Left-aligned, regular weight, generous black space.

        Deliberately has no label, rule or monogram: the words are the card.
        """

        font, lines = self._tweet_lines(draw, content)
        pitch = int(self.tweet_size * self.tweet_leading)

        block_height = pitch * len(lines)

        # Attribution line under the quote: the verse reference if there is
        # one, otherwise the optional IG_CARD_HANDLE. Left aligned, grey.
        attribution = reference or self.handle

        handle_font = self._font("modern", int(self.tweet_size * 0.82), bold=False)
        handle_gap = int(self.tweet_size * 1.9) if attribution else 0

        total = block_height + handle_gap

        y = (HEIGHT - total) // 2
        if y < self.tweet_pad * 2:
            y = self.tweet_pad * 2

        for line in lines:
            draw.text((self.tweet_pad, y), line, font=font, fill=TEXT)
            y += pitch

        if attribution:
            draw.text(
                (self.tweet_pad, y + int(self.tweet_size * 0.45)),
                attribution,
                font=handle_font,
                fill=SUBTLE,
            )

    @staticmethod
    def _spaced(text, amount=3):
        """Letter-spaced text for the small caps labels."""

        return (" " * amount).join(list(text))
