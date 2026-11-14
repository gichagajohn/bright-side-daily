"""
Reel Generator — Bright Side Daily

Turns a quote card into a 15-second vertical Reel (1080x1920).

Treatment: the card sits centred on a black canvas and very slowly zooms in
(Ken Burns), which is what makes a static image feel like video. Optional
fade-in from black at the start and out at the end.

Requires ffmpeg. On GitHub Actions install it with:
    sudo apt-get install -y ffmpeg
Or leave imageio-ffmpeg in requirements.txt and the binary is resolved
automatically.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output" / "reels"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
DURATION = float(os.environ.get("REEL_DURATION", "15"))
FPS = 30
BACKGROUND = (10, 10, 12)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("reel_generator")


def _ffmpeg():
    """Find an ffmpeg binary, preferring the system one."""

    system = shutil.which("ffmpeg")

    if system:
        return system

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()

    except Exception:
        return None


def _vertical_canvas(card_path):
    """Place the square card on a 9:16 canvas with a soft border."""

    card = Image.open(card_path).convert("RGB")

    # Fit the card inside the frame with breathing room on all sides.
    target_w = int(WIDTH * 0.86)
    scale = target_w / card.width
    card = card.resize((target_w, int(card.height * scale)), Image.LANCZOS)

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)

    x = (WIDTH - card.width) // 2
    y = (HEIGHT - card.height) // 2
    canvas.paste(card, (x, y))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        (x - 1, y - 1, x + card.width, y + card.height),
        outline=(44, 44, 50),
        width=2,
    )

    still_path = OUTPUT_DIR / "_still.png"
    canvas.save(still_path, "PNG")

    return still_path


def generate(card_path, output_path=None, duration=None):
    """
    Build a vertical Reel from a card image.

    Returns the MP4 path, or None when ffmpeg is unavailable.
    """

    binary = _ffmpeg()

    if not binary:
        log.error(
            "ffmpeg not found. Install it (apt-get install -y ffmpeg) "
            "or add imageio-ffmpeg to requirements.txt."
        )
        return None

    still = _vertical_canvas(card_path)

    duration = float(duration or DURATION)
    frames = int(duration * FPS)

    if output_path is None:
        output_path = OUTPUT_DIR / f"{Path(card_path).stem}.mp4"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Slow zoom from 100% to 108%, then a fade in and out.
    zoom = (
        "zoompan=z='min(zoom+0.00035,1.08)'"
        ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )

    fade = "fade=t=in:st=0:d=0.8,fade=t=out:st={:.2f}:d=0.8".format(
        max(duration - 0.8, 0)
    )

    command = [
        binary,
        "-y",
        "-loop", "1",
        "-i", str(still),
        "-vf", f"{zoom},{fade},format=yuv420p",
        "-t", str(duration),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(output_path),
    ]

    log.info("Rendering reel: %s", output_path)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log.error("ffmpeg failed:\n%s", result.stderr[-1200:])
        return None

    try:
        still.unlink()
    except Exception:
        pass

    size_kb = output_path.stat().st_size / 1024
    log.info("Reel ready: %s (%.0f KB, %.0fs)", output_path, size_kb, duration)

    return str(output_path)
