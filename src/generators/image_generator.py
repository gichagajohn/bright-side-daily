"""
Image Generation System — Bright Side Daily
Creates professional, Facebook-optimized quote poster images using Pillow.
No external API required — all rendering is local.
"""
import json
import math
import os
import random
import textwrap
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️  Pillow not installed. Run: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "images" / "output"
FONTS_DIR = ROOT / "images" / "fonts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Facebook-optimized dimensions (1:1 square, also fits 4:5 feed)
IMG_WIDTH = 1080
IMG_HEIGHT = 1080

# ── Palette themes ─────────────────────────────────────────────────────────────

THEMES = {
    "sunrise_gold": {
        "bg_colors": [(255, 198, 93), (255, 139, 58), (255, 82, 82)],
        "text_color": (255, 255, 255),
        "shadow_color": (120, 60, 0),
        "accent": (255, 230, 150),
        "overlay": (200, 80, 20, 80),
    },
    "ocean_calm": {
        "bg_colors": [(20, 136, 204), (0, 83, 155), (0, 184, 212)],
        "text_color": (255, 255, 255),
        "shadow_color": (0, 40, 80),
        "accent": (180, 235, 255),
        "overlay": (0, 50, 120, 90),
    },
    "forest_green": {
        "bg_colors": [(67, 160, 71), (27, 94, 32), (100, 181, 246)],
        "text_color": (255, 255, 255),
        "shadow_color": (10, 50, 10),
        "accent": (200, 255, 200),
        "overlay": (20, 80, 20, 80),
    },
    "lavender_dream": {
        "bg_colors": [(126, 87, 194), (81, 45, 168), (206, 147, 216)],
        "text_color": (255, 255, 255),
        "shadow_color": (40, 10, 80),
        "accent": (240, 220, 255),
        "overlay": (80, 20, 150, 70),
    },
    "warm_rose": {
        "bg_colors": [(233, 30, 99), (194, 24, 91), (255, 138, 101)],
        "text_color": (255, 255, 255),
        "shadow_color": (100, 0, 40),
        "accent": (255, 200, 220),
        "overlay": (180, 10, 70, 80),
    },
    "midnight_blue": {
        "bg_colors": [(13, 27, 62), (25, 55, 109), (0, 100, 148)],
        "text_color": (255, 255, 255),
        "shadow_color": (0, 0, 30),
        "accent": (150, 200, 255),
        "overlay": (5, 10, 50, 100),
    },
    "warm_cream": {
        "bg_colors": [(255, 248, 225), (255, 236, 179), (255, 213, 79)],
        "text_color": (60, 40, 10),
        "shadow_color": (200, 160, 60),
        "accent": (150, 100, 20),
        "overlay": (220, 170, 50, 40),
    },
    "minimalist_white": {
        "bg_colors": [(255, 255, 255), (245, 245, 245), (250, 250, 250)],
        "text_color": (30, 30, 30),
        "shadow_color": (180, 180, 180),
        "accent": (100, 100, 100),
        "overlay": (220, 220, 220, 20),
    },
}

CATEGORY_THEME_MAP = {
    "motivational_quotes": ["sunrise_gold", "midnight_blue", "ocean_calm"],
    "positive_life_quotes": ["warm_rose", "forest_green", "lavender_dream"],
    "self_improvement_quotes": ["ocean_calm", "midnight_blue", "forest_green"],
    "gratitude_quotes": ["warm_cream", "sunrise_gold", "lavender_dream"],
    "encouragement_quotes": ["sunrise_gold", "warm_rose", "ocean_calm"],
    "meme_captions": ["warm_cream", "lavender_dream", "minimalist_white"],
    "engagement_questions": ["ocean_calm", "forest_green", "warm_rose"],
}


class ImageGenerator:
    def __init__(self):
        if not PILLOW_AVAILABLE:
            raise RuntimeError("Pillow is required. Run: pip install Pillow")

    # ── Core rendering ─────────────────────────────────────────────────────────

    def _pick_theme(self, category: str, style: str) -> dict:
        if style == "minimalist":
            return THEMES["minimalist_white"]
        candidates = CATEGORY_THEME_MAP.get(category, list(THEMES.keys()))
        name = random.choice(candidates)
        return THEMES[name]

    def _make_gradient_background(self, theme: dict) -> Image.Image:
        img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
        draw = ImageDraw.Draw(img)
        colors = theme["bg_colors"]

        for y in range(IMG_HEIGHT):
            t = y / IMG_HEIGHT
            if len(colors) >= 3:
                if t < 0.5:
                    r = self._lerp(colors[0][0], colors[1][0], t * 2)
                    g = self._lerp(colors[0][1], colors[1][1], t * 2)
                    b = self._lerp(colors[0][2], colors[1][2], t * 2)
                else:
                    r = self._lerp(colors[1][0], colors[2][0], (t - 0.5) * 2)
                    g = self._lerp(colors[1][1], colors[2][1], (t - 0.5) * 2)
                    b = self._lerp(colors[1][2], colors[2][2], (t - 0.5) * 2)
            else:
                r = self._lerp(colors[0][0], colors[1][0], t)
                g = self._lerp(colors[0][1], colors[1][1], t)
                b = self._lerp(colors[0][2], colors[1][2], t)
            draw.line([(0, y), (IMG_WIDTH, y)], fill=(int(r), int(g), int(b)))
        return img

    def _add_geometric_decoration(self, img: Image.Image, theme: dict) -> Image.Image:
        draw = ImageDraw.Draw(img, "RGBA")
        accent = theme["accent"]

        style = random.choice(["circles", "lines", "dots", "arcs"])

        if style == "circles":
            for _ in range(6):
                r = random.randint(40, 160)
                x = random.randint(-r, IMG_WIDTH + r)
                y = random.randint(-r, IMG_HEIGHT + r)
                opacity = random.randint(15, 40)
                draw.ellipse([x - r, y - r, x + r, y + r],
                              outline=(*accent, opacity), width=2)

        elif style == "lines":
            for i in range(0, IMG_HEIGHT, 80):
                draw.line([(0, i), (IMG_WIDTH, i + 40)],
                          fill=(*accent, 20), width=1)

        elif style == "dots":
            for _ in range(40):
                x = random.randint(0, IMG_WIDTH)
                y = random.randint(0, IMG_HEIGHT)
                r = random.randint(3, 12)
                opacity = random.randint(20, 60)
                draw.ellipse([x - r, y - r, x + r, y + r],
                              fill=(*accent, opacity))

        elif style == "arcs":
            for i in range(3):
                x = random.randint(200, 800)
                y = random.randint(200, 800)
                r = random.randint(200, 500)
                draw.arc([x - r, y - r, x + r, y + r],
                         start=random.randint(0, 180),
                         end=random.randint(181, 360),
                         fill=(*accent, 30), width=3)

        return img

    def _add_vignette(self, img: Image.Image) -> Image.Image:
        vignette = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        cx, cy = IMG_WIDTH // 2, IMG_HEIGHT // 2
        max_r = math.sqrt(cx ** 2 + cy ** 2)
        for step in range(60, 0, -1):
            r = int(max_r * step / 60)
            alpha = int((1 - step / 60) * 100)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=(0, 0, 0, alpha))
        result = Image.alpha_composite(img.convert("RGBA"), vignette)
        return result.convert("RGB")

    def _add_decorative_border(self, img: Image.Image, theme: dict) -> Image.Image:
        draw = ImageDraw.Draw(img)
        margin = 28
        line_color = theme["accent"]
        draw.rectangle(
            [margin, margin, IMG_WIDTH - margin, IMG_HEIGHT - margin],
            outline=(*line_color, 80) if len(line_color) == 3 else line_color,
            width=2,
        )
        # Corner accents
        corner = 60
        for x, y in [(margin, margin), (IMG_WIDTH - margin - corner, margin),
                     (margin, IMG_HEIGHT - margin - corner),
                     (IMG_WIDTH - margin - corner, IMG_HEIGHT - margin - corner)]:
            draw.rectangle([x, y, x + corner, y + corner],
                           outline=line_color, width=3)
        return img

    # ── Typography ─────────────────────────────────────────────────────────────

    def _get_font(self, size: int):
        """Try to load a system font, fall back to default."""
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _get_font_regular(self, size: int):
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for path in font_candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _auto_font_size(self, text: str, max_width: int, min_size=40, max_size=80) -> int:
        """Auto-scale font to fit text width."""
        chars = len(text)
        if chars < 60:
            return max_size
        elif chars < 100:
            return 65
        elif chars < 160:
            return 55
        else:
            return min_size

    def _draw_text_with_shadow(self, draw, text: str, position, font,
                                text_color, shadow_color, shadow_offset=4):
        x, y = position
        # Shadow
        draw.text((x + shadow_offset, y + shadow_offset), text,
                  font=font, fill=(*shadow_color, 150))
        # Main text
        draw.text((x, y), text, font=font, fill=text_color)

    def _wrap_and_center_text(self, draw, text: str, y_center: int,
                               font, text_color, shadow_color,
                               max_width: int, line_spacing: int = 10):
        """Word-wrap text and render it centered."""
        chars_per_line = max(20, max_width // (font.size // 2 + 2))
        lines = textwrap.wrap(text, width=chars_per_line)
        # Guard empty
        if not lines:
            lines = [text]

        try:
            bbox = draw._image.size  # not used directly
            line_height = font.getbbox("A")[3] + line_spacing
        except Exception:
            line_height = font.size + line_spacing

        total_height = len(lines) * line_height
        y = y_center - total_height // 2

        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
            except Exception:
                w = len(line) * (font.size // 2)
            x = (IMG_WIDTH - w) // 2
            self._draw_text_with_shadow(draw, line, (x, y), font, text_color, shadow_color)
            y += line_height

    # ── Branding ───────────────────────────────────────────────────────────────

    def _add_branding(self, img: Image.Image, theme: dict):
        draw = ImageDraw.Draw(img)
        brand_font = self._get_font_regular(28)
        brand_text = "✨ Bright Side Daily ✨"
        text_color = theme["accent"]

        try:
            bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(brand_text) * 14

        x = (IMG_WIDTH - w) // 2
        y = IMG_HEIGHT - 75

        # Brand background pill
        padding = 20
        draw.rounded_rectangle(
            [x - padding, y - 8, x + w + padding, y + 42],
            radius=20,
            fill=(0, 0, 0, 80),
        )
        draw.text((x, y), brand_text, font=brand_font, fill=text_color)

    def _add_quote_marks(self, img: Image.Image, theme: dict):
        draw = ImageDraw.Draw(img)
        quote_font = self._get_font(120)
        color = (*theme["accent"], 60)
        draw.text((50, 80), "\u201C", font=quote_font, fill=color)
        draw.text((IMG_WIDTH - 110, IMG_HEIGHT - 160), "\u201D", font=quote_font, fill=color)

    # ── Main generation ────────────────────────────────────────────────────────

    def generate(self, post: dict, output_path: str = None) -> str:
        category = post.get("category", "motivational_quotes")
        content = post.get("content", "")
        visual = post.get("visual_theme", {})
        style = visual.get("style", "photography")
        slot = post.get("slot", "morning_motivation")

        theme = self._pick_theme(category, style)

        # 1. Background
        img = self._make_gradient_background(theme)

        # 2. Decorative layer
        img = self._add_geometric_decoration(img, theme)

        # 3. Vignette (except minimalist)
        if style != "minimalist":
            img = self._add_vignette(img)

        draw = ImageDraw.Draw(img)

        # 4. Divider lines
        draw.line([(100, 200), (IMG_WIDTH - 100, 200)], fill=(*theme["accent"], 100), width=2)
        draw.line([(100, IMG_HEIGHT - 210), (IMG_WIDTH - 100, IMG_HEIGHT - 210)],
                  fill=(*theme["accent"], 100), width=2)

        # 5. Slot label (top)
        label_map = {
            "morning_motivation": "☀️  MORNING MOTIVATION",
            "positive_quote": "🌟  POSITIVE VIBES",
            "funny_meme": "😄  DAILY HUMOR",
            "self_improvement": "📈  GROW DAILY",
            "midday_encouragement": "💪  KEEP GOING",
            "evening_reflection": "🌙  EVENING REFLECTION",
            "engagement_question": "💬  QUESTION OF THE DAY",
        }
        label = label_map.get(slot, "✨  BRIGHT SIDE DAILY")
        label_font = self._get_font_regular(30)
        try:
            lbbox = draw.textbbox((0, 0), label, font=label_font)
            lw = lbbox[2] - lbbox[0]
        except Exception:
            lw = len(label) * 15
        lx = (IMG_WIDTH - lw) // 2
        draw.text((lx, 120), label, font=label_font, fill=theme["accent"])

        # 6. Quote / meme text
        font_size = self._auto_font_size(content, IMG_WIDTH - 180)
        quote_font = self._get_font(font_size)

        if category == "meme_captions":
            # Split at newline for meme two-liner
            parts = content.split("\n", 1)
            if len(parts) == 2:
                setup_font = self._get_font(52)
                punchline_font = self._get_font(58)
                self._wrap_and_center_text(draw, parts[0], 440, setup_font,
                                           theme["text_color"], theme["shadow_color"], 800)
                self._wrap_and_center_text(draw, parts[1], 620, punchline_font,
                                           theme["accent"], theme["shadow_color"], 800)
            else:
                self._wrap_and_center_text(draw, content, 540, quote_font,
                                           theme["text_color"], theme["shadow_color"], 860)
        else:
            # Add decorative quote marks
            self._add_quote_marks(img, theme)
            draw = ImageDraw.Draw(img)
            self._wrap_and_center_text(draw, content, 520, quote_font,
                                       theme["text_color"], theme["shadow_color"], 860)

        # 7. Border
        self._add_decorative_border(img, theme)

        # 8. Branding
        self._add_branding(img, theme)

        # 9. Save
        if not output_path:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{slot}_{ts}.png"
            output_path = str(OUTPUT_DIR / filename)

        img.save(output_path, "PNG", quality=95)
        print(f"  🖼️  Image saved: {output_path}")
        return output_path

    @staticmethod
    def _lerp(a, b, t):
        return a + (b - a) * t


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gen = ImageGenerator()
    test_post = {
        "slot": "morning_motivation",
        "category": "motivational_quotes",
        "content": "Success begins when excuses end. The time to start is now.",
        "visual_theme": {"style": "photography", "theme": "mountain climber reaching summit"},
    }
    path = gen.generate(test_post)
    print(f"Generated: {path}")
