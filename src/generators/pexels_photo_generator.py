"""Generate photo posts with category-specific typography."""
import io
import os
import random
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PEXELS_API = "https://api.pexels.com/v1/search"

CATEGORY_QUERIES = {
    "motivational_quotes": ["person reaching mountain summit sunrise", "runner celebrating finish line", "open road sunrise"],
    "positive_life_quotes": ["friends laughing outdoors", "happy family in sunny park", "colorful flowers sunlight"],
    "self_improvement_quotes": ["person journaling by window", "books coffee study desk", "person meditating sunrise"],
    "gratitude_quotes": ["coffee by rainy window", "hands holding flower", "peaceful sunset over water"],
    "encouragement_quotes": ["sunlight through storm clouds", "sprout growing through concrete", "hiker walking toward light"],
    "meme_captions": ["funny confused dog", "funny cat expression", "tired office worker", "person making funny face"],
    "engagement_questions": ["friends talking coffee table", "colorful speech bubbles", "people having conversation"],
}

# Each category has its own visual identity.
FONT_STYLES = {
    "modern": {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
        "fill": "white",
        "stroke": "black",
        "box": (0, 0, 0, 180),
    },
    "elegant": {
        "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
        "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
        "fill": (255, 250, 235),
        "stroke": (35, 20, 25),
        "box": (20, 15, 25, 155),
    },
    "playful": {
        "bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ],
        "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
        "fill": (255, 235, 80),
        "stroke": "black",
        "box": (0, 0, 0, 195),
    },
}

CATEGORY_STYLES = {
    "motivational_quotes": "modern",
    "positive_life_quotes": "elegant",
    "self_improvement_quotes": "modern",
    "gratitude_quotes": "elegant",
    "encouragement_quotes": "modern",
    "meme_captions": "playful",
    "engagement_questions": "playful",
}


class PexelsPhotoGenerator:
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("PEXELS_API_KEY is not configured")

    def _style(self, post):
        return CATEGORY_STYLES.get(post.get("category", ""), "modern")

    def _font(self, style_name, size, bold=True):
        style = FONT_STYLES[style_name]
        candidates = style["bold"] if bold else style["regular"]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _query(self, post):
        choices = CATEGORY_QUERIES.get(
            post.get("category", ""),
            ["beautiful positive lifestyle"],
        )
        return random.choice(choices)

    def _download_url(self, query):
        response = requests.get(
            PEXELS_API,
            headers={"Authorization": self.api_key},
            params={
                "query": query,
                "per_page": 15,
                "orientation": "square",
            },
            timeout=30,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        if not photos:
            raise RuntimeError(f"Pexels returned no photos for: {query}")
        photo = random.choice(photos)
        return photo["src"].get("large2x") or photo["src"]["large"]

    def _draw_centered(self, draw, text, y, font, fill, stroke):
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
        x = (1080 - (bbox[2] - bbox[0])) // 2
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            stroke_width=2,
            stroke_fill=stroke,
        )

    def generate(self, post, output_path=None):
        style_name = self._style(post)
        style = FONT_STYLES[style_name]
        query = self._query(post)

        image_response = requests.get(self._download_url(query), timeout=60)
        image_response.raise_for_status()

        image = Image.open(io.BytesIO(image_response.content)).convert("RGB")
        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side)).resize((1080, 1080))
        image = ImageEnhance.Brightness(image).enhance(0.72)

        draw = ImageDraw.Draw(image, "RGBA")
        caption = post.get("content", "").strip()
        category = post.get("category", "")

        if style_name == "playful":
            caption = caption.upper()
            width = 28 if len(caption) < 110 else 36
            font_size = 58 if len(caption) < 100 else 45
        elif style_name == "elegant":
            width = 27 if len(caption) < 110 else 35
            font_size = 54 if len(caption) < 100 else 43
        else:
            width = 32 if len(caption) < 110 else 42
            font_size = 58 if len(caption) < 100 else 46

        font = self._font(style_name, font_size, bold=True)
        lines = textwrap.wrap(caption, width=width) or [caption]
        line_height = font_size + 12
        box_height = len(lines) * line_height + 80
        y = 45

        draw.rounded_rectangle(
            (35, y, 1045, y + box_height),
            radius=24,
            fill=style["box"],
        )

        for line in lines:
            self._draw_centered(
                draw,
                line,
                y + 30,
                font,
                style["fill"],
                style["stroke"],
            )
            y += line_height

        # Category label gives every type a clear visual identity.
        labels = {
            "motivational_quotes": "DAILY MOTIVATION",
            "positive_life_quotes": "POSITIVE VIBES",
            "self_improvement_quotes": "GROW EVERY DAY",
            "gratitude_quotes": "GRATITUDE MOMENT",
            "encouragement_quotes": "KEEP GOING",
            "meme_captions": "DAILY HUMOR",
            "engagement_questions": "QUESTION OF THE DAY",
        }
        label = labels.get(category, "BRIGHT SIDE DAILY")
        label_font = self._font(style_name, 25, bold=True)
        self._draw_centered(draw, label, 950, label_font, style["fill"], style["stroke"])

        brand = "Bright Side Daily"
        brand_font = self._font(style_name, 23, bold=False)
        bbox = draw.textbbox((0, 0), brand, font=brand_font)
        draw.text(
            ((1080 - (bbox[2] - bbox[0])) // 2, 1015),
            brand,
            font=brand_font,
            fill="white",
            stroke_width=2,
            stroke_fill="black",
        )

        if output_path is None:
            output_path = OUTPUT_DIR / (
                f"{post.get('slot', 'post')}_"
                f"{post.get('content_index', 'photo')}.jpg"
            )

        image.save(output_path, "JPEG", quality=92, optimize=True)
        return str(output_path)
