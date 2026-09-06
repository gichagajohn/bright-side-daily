"""Create photo memes from the free Pexels API."""
import os
import random
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_API = "https://api.pexels.com/v1/search"


class PexelsMemeGenerator:
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("PEXELS_API_KEY is not configured")

    def _font(self, size):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _find_photo(self, query):
        response = requests.get(
            PEXELS_API,
            headers={"Authorization": self.api_key},
            params={"query": query, "per_page": 15, "orientation": "square"},
            timeout=30,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        if not photos:
            raise RuntimeError(f"Pexels returned no photos for: {query}")
        return random.choice(photos)["src"]["large2x"]

    def generate(self, post, output_path=None):
        visual = post.get("visual_theme", {})
        query = visual.get("theme", "funny relatable person")
        image_url = self._find_photo(query)
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()

        temp_path = OUTPUT_DIR / "_pexels_download.jpg"
        temp_path.write_bytes(image_response.content)
        image = Image.open(temp_path).convert("RGB")

        # Crop to a square without stretching the source photo.
        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side)).resize((1080, 1080))
        image = ImageEnhance.Brightness(image).enhance(0.78)

        draw = ImageDraw.Draw(image, "RGBA")
        caption = post.get("content", "")
        font = self._font(58 if len(caption) < 105 else 46)
        lines = textwrap.wrap(caption, width=30 if len(caption) < 105 else 38)
        line_height = 70 if len(caption) < 105 else 58
        box_height = len(lines) * line_height + 70
        y = 50

        draw.rounded_rectangle((35, y, 1045, y + box_height), radius=22, fill=(0, 0, 0, 175))
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=2)
            x = (1080 - (bbox[2] - bbox[0])) // 2
            draw.text((x, y + 28), line, font=font, fill="white", stroke_width=2, stroke_fill="black")
            y += line_height

        branding = "Bright Side Daily"
        brand_font = self._font(25)
        bbox = draw.textbbox((0, 0), branding, font=brand_font)
        draw.text(((1080 - (bbox[2] - bbox[0])) // 2, 1015), branding,
                  font=brand_font, fill="white", stroke_width=2, stroke_fill="black")

        if not output_path:
            output_path = OUTPUT_DIR / f"{post.get('slot', 'meme')}_{post.get('content_index', 'photo')}.jpg"
        image.save(output_path, "JPEG", quality=92, optimize=True)
        temp_path.unlink(missing_ok=True)
        return str(output_path)
