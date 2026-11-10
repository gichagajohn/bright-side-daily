"""Post one daily world-news Bible encouragement photo."""
import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUTPUT_DIR = ROOT / "images" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from agents.world_bible_agent import build_bible_post
from agents.social_publisher import SocialPublisher


def font(size, bold=True):
    paths = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
        if bold
        else ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
    )
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def download_photo():
    key = os.getenv("PEXELS_API_KEY", "")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is missing")

    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": key},
        params={
            "query": "open Bible sunlight window",
            "per_page": 15,
            "orientation": "square",
        },
        timeout=30,
    )
    response.raise_for_status()
    photos = response.json().get("photos", [])
    if not photos:
        raise RuntimeError("Pexels returned no Bible photos")

    url = photos[0]["src"].get("large2x") or photos[0]["src"]["large"]
    image_response = requests.get(url, timeout=60)
    image_response.raise_for_status()
    return Image.open(io.BytesIO(image_response.content)).convert("RGB")


def create_image(post):
    image = download_photo()
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((1080, 1080))
    image = ImageEnhance.Brightness(image).enhance(0.65)

    draw = ImageDraw.Draw(image, "RGBA")
    text = post["content"]
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.extend(__import__("textwrap").wrap(paragraph, width=30) or [paragraph])
        else:
            lines.append("")

    title_font = font(48, True)
    body_font = font(38, False)
    y = 55
    line_height = 58
    box_height = min(810, max(260, len(lines) * line_height + 80))

    draw.rounded_rectangle(
        (35, y, 1045, y + box_height),
        radius=25,
        fill=(20, 15, 25, 185),
    )

    for line in lines:
        current_font = title_font if "KJV" in line or ":" in line and len(line) < 32 else body_font
        if line:
            bbox = draw.textbbox((0, 0), line, font=current_font, stroke_width=2)
            x = (1080 - (bbox[2] - bbox[0])) // 2
            draw.text(
                (x, y + 28),
                line,
                font=current_font,
                fill=(255, 250, 235),
                stroke_width=2,
                stroke_fill=(35, 20, 25),
            )
        y += line_height
        if y > 900:
            break

    brand = "Bright Side Daily"
    brand_font = font(24, False)
    bbox = draw.textbbox((0, 0), brand, font=brand_font)
    draw.text(
        ((1080 - (bbox[2] - bbox[0])) // 2, 1018),
        brand,
        font=brand_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black",
    )

    path = OUTPUT_DIR / "bible_world_encouragement.jpg"
    image.save(path, "JPEG", quality=92, optimize=True)
    return path


def main():
    base_post = {
        "slot": "bible_world_encouragement",
        "category": "bible_quotes",
        "content": "",
        "content_index": 0,
    }
    post = build_bible_post(base_post)
    image_path = create_image(post)

    publisher = SocialPublisher(platforms=os.getenv("PLATFORMS"))
    result = publisher.publish(post, str(image_path))
    print(json.dumps(result, indent=2, default=str))

    if not result.get("success"):
        raise RuntimeError(f"Bible post failed: {result}")


if __name__ == "__main__":
    main()
