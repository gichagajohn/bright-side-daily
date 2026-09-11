"""Post one daily world-news Bible encouragement photo."""

import io
import os
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "images" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from agents.world_bible_agent import build_bible_post
from agents.facebook_publisher import FacebookPublisher


def get_font(size: int, bold: bool = True):
    """Load an attractive Bible-style serif font."""
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def download_bible_photo():
    """Download a Bible-related image from Pexels."""
    api_key = os.getenv("PEXELS_API_KEY", "")

    if not api_key:
        raise RuntimeError("PEXELS_API_KEY is missing")

    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={
            "Authorization": api_key,
        },
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

    photo = photos[0]

    image_url = (
        photo["src"].get("large2x")
        or photo["src"].get("large")
        or photo["src"].get("original")
    )

    image_response = requests.get(image_url, timeout=60)
    image_response.raise_for_status()

    return Image.open(
        io.BytesIO(image_response.content)
    ).convert("RGB")


def create_bible_image(post: dict) -> Path:
    """Create a beautiful Bible quote image."""
    image = download_bible_photo()

    # Crop the photo into a square without stretching it.
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2

    image = image.crop(
        (
            left,
            top,
            left + side,
            top + side,
        )
    ).resize((1080, 1080))

    # Darken the image so the text is easy to read.
    image = ImageEnhance.Brightness(image).enhance(0.65)

    draw = ImageDraw.Draw(image, "RGBA")

    text = post.get("content", "").strip()

    lines = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()

        if paragraph:
            wrapped = textwrap.wrap(paragraph, width=30)
            lines.extend(wrapped or [paragraph])
        else:
            lines.append("")

    title_font = get_font(48, bold=True)
    body_font = get_font(38, bold=False)

    line_height = 58
    box_top = 50
    box_height = min(
        810,
        max(280, len(lines) * line_height + 90),
    )

    # Elegant dark translucent text panel.
    draw.rounded_rectangle(
        (
            35,
            box_top,
            1045,
            box_top + box_height,
        ),
        radius=25,
        fill=(20, 15, 25, 190),
    )

    y = box_top + 35

    for line in lines:
        if not line:
            y += 20
            continue

        # Bible references are displayed as headings.
        is_reference = (
            "KJV" in line
            or (
                ":" in line
                and len(line) < 40
            )
        )

        current_font = title_font if is_reference else body_font

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=current_font,
            stroke_width=2,
        )

        text_width = bbox[2] - bbox[0]
        x = (1080 - text_width) // 2

        draw.text(
            (x, y),
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
    brand_font = get_font(24, bold=False)

    brand_box = draw.textbbox(
        (0, 0),
        brand,
        font=brand_font,
    )

    brand_width = brand_box[2] - brand_box[0]

    draw.text(
        (
            (1080 - brand_width) // 2,
            1018,
        ),
        brand,
        font=brand_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black",
    )

    output_path = OUTPUT_DIR / "bible_world_encouragement.jpg"

    image.save(
        output_path,
        "JPEG",
        quality=92,
        optimize=True,
    )

    return output_path


def main():
    """
    Build the Bible post from current world headlines,
    create the photo, and publish it to Facebook.
    """

    base_post = {
        "slot": "bible_world_encouragement",
        "category": "bible_quotes",
        "content": "",
        "content_index": 0,
    }

    post = build_bible_post(base_post)

    image_path = create_bible_image(post)

    publisher = FacebookPublisher()

    result = publisher.publish(
        post,
        str(image_path),
    )

    print(result)

    if not result.get("success"):
        raise RuntimeError(
            f"Bible post failed: {result}"
        )


if __name__ == "__main__":
    main()
