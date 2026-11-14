"""
Reel Generator — Bright Side Daily

Turns a quote into a vertical (1080x1920) Instagram Reel.

Treatment
---------
The quote is no longer a flat picture in a video. Each word appears on its own,
rising into place a fraction before it is spoken, so the text and the voice land
together. The label fades in first, the monogram arrives after the last word,
and the whole thing fades out.

Audio
-----
Three things can be in the mix:

    voice   neural text-to-speech reading the quote aloud
    pad     a quiet generated ambient bed underneath
    track   any audio file you put in assets/audio/

The voice is timed with word-level boundaries from the TTS engine, which is why
the animation is in sync rather than guessed.

Environment
-----------
    IG_REEL_VOICE      voice name (default en-KE-ChilembaNeural)
    IG_REEL_RATE       speaking rate, e.g. -8%      (default -8%)
    IG_REEL_TTS        auto | off                   (default auto)
    IG_REEL_ANIM       words | none                 (default words)
    IG_REEL_PAD        on | off                     (default on)
    IG_REEL_VOLUME     voice volume 0.0 - 1.0       (default 1.0)
    IG_REEL_DURATION   length when there is no voice (default 15)

Every stage degrades safely: no TTS means a silent animated reel, no animation
means the old static-card reel, no ffmpeg means the caller posts the card.
"""

import asyncio
import logging
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from generators.black_card_generator import (
    CATEGORY_LABELS,
    CATEGORY_STYLES,
    FONT_STYLES,
    resolve_font,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "images" / "output" / "reels"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = ROOT / "assets" / "audio"
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac"}

WIDTH = 1080
HEIGHT = 1920
FPS = 30
BACKGROUND = (10, 10, 12)
TEXT = (255, 255, 255)
SUBTLE = (150, 150, 158)
RULE = (48, 48, 54)

DEFAULT_VOICE = os.environ.get("IG_REEL_VOICE", "en-KE-ChilembaNeural")
DEFAULT_RATE = os.environ.get("IG_REEL_RATE", "-8%")
TTS_MODE = (os.environ.get("IG_REEL_TTS") or "auto").strip().lower()
ANIM_MODE = (os.environ.get("IG_REEL_ANIM") or "words").strip().lower()
PAD_MODE = (os.environ.get("IG_REEL_PAD") or "on").strip().lower()
VOICE_VOLUME = float(os.environ.get("IG_REEL_VOLUME", "1.0"))
STATIC_DURATION = float(os.environ.get("IG_REEL_DURATION", "15"))

WORD_RISE_MS = 260          # how long a word takes to fade and rise in
LEAD_IN_MS = 700            # silence before the voice starts
TAIL_MS = 2400              # hold after the last word

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("reel_generator")


# ── ffmpeg discovery ──────────────────────────────────────────────────────────
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


def _run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


# ── Audio ─────────────────────────────────────────────────────────────────────
def _own_track():
    """A royalty-free track the user dropped into assets/audio/, if any."""

    if not AUDIO_DIR.is_dir():
        return None

    tracks = sorted(
        path
        for path in AUDIO_DIR.iterdir()
        if path.suffix.lower() in AUDIO_EXTENSIONS
    )

    return random.choice(tracks) if tracks else None


def _speak(text, voice=None, rate=None):
    """Read `text` aloud. Returns (mp3_path, [(seconds, word), ...]) or None.

    Tries edge-tts first because it reports word boundaries, which is what
    makes the text animation line up with the voice. Falls back to gTTS,
    which still reads the quote but gives no timing information.
    """

    if TTS_MODE == "off":
        return None

    target = Path(tempfile.mkdtemp(prefix="reel_tts_")) / "voice.mp3"

    try:
        import edge_tts

        async def _collect():
            communicate = edge_tts.Communicate(
                text,
                voice or DEFAULT_VOICE,
                rate=rate or DEFAULT_RATE,
                boundary="WordBoundary",
            )

            marks = []

            with open(target, "wb") as handle:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        handle.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        marks.append(
                            (round(chunk["offset"] / 10_000_000, 3), chunk["text"])
                        )

            return marks

        marks = asyncio.run(_collect())

        if target.exists() and target.stat().st_size > 1000:
            log.info("Voice-over: %s (%d words timed)", voice or DEFAULT_VOICE, len(marks))
            return target, marks

    except Exception as exc:
        log.warning("edge-tts unavailable (%s); trying gTTS.", exc)

    try:
        from gtts import gTTS

        gTTS(text=text, lang="en", slow=False).save(str(target))

        if target.exists() and target.stat().st_size > 1000:
            log.info("Voice-over: gTTS (no word timings available)")
            return target, []

    except Exception as exc:
        log.warning("gTTS unavailable (%s); the reel will be music only.", exc)

    return None


def _duration_of(binary, path):
    """Audio length in seconds, or 0.0 if it cannot be read."""

    ok, _ = _run([binary, "-i", str(path), "-f", "null", "-"])
    # ffmpeg exits non-zero for "-f null -" without an output; parse stderr
    result = subprocess.run(
        [binary, "-i", str(path)], capture_output=True, text=True
    )
    marker = "Duration: "

    if marker not in result.stderr:
        return 0.0

    stamp = result.stderr.split(marker, 1)[1].split(",", 1)[0]
    hours, minutes, seconds = stamp.split(":")

    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _render_pad(binary, duration, target):
    """Synthesise a warm, quiet ambient bed of exactly `duration` seconds.

    Plain generated tones, so there is nothing to license and nothing that can
    be claimed by anyone.
    """

    fade_out_d = min(3.0, max(duration / 4, 1.0))
    fade_out = max(duration - fade_out_d, 0)

    sources = []
    for freq in ("110.00", "164.81", "277.18", "440.00", "110.40", "220.60"):
        sources += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration + 1:.1f}"]

    graph = (
        "[0:a]volume=0.50[a0];[1:a]volume=0.30[a1];[2:a]volume=0.18[a2];"
        "[3:a]volume=0.08[a3];[4:a]volume=0.28[a4];[5:a]volume=0.12[a5];"
        "[a0][a1][a2][a3][a4][a5]amix=inputs=6:normalize=0[mix];"
        "[mix]tremolo=f=0.20:d=0.30,lowpass=f=1000,highpass=f=55,"
        "aecho=0.8:0.65:120:0.22,"
        f"afade=t=in:st=0:d={min(2.0, duration / 5):.2f},"
        f"afade=t=out:st={fade_out:.2f}:d={fade_out_d:.2f},"
        "volume=4.2[out]"
    )

    command = (
        [binary, "-y"]
        + sources
        + [
            "-filter_complex", graph,
            "-map", "[out]",
            "-t", f"{duration:.2f}",
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "aac",
            "-b:a", "128k",
            str(target),
        ]
    )

    ok, error = _run(command)

    if not ok:
        log.warning("Pad synthesis failed: %s", error[-300:])
        return None

    return target


def _build_audio(binary, voice_path, duration, workdir):
    """Mix voice + bed into one track. Returns a path or None."""

    workdir = Path(workdir)
    parts = []

    if voice_path:
        parts.append(("voice", voice_path))

    want_pad = PAD_MODE != "off"

    if not voice_path and want_pad:
        track = _own_track()

        if track:
            bed = workdir / "bed.m4a"
            ok, _ = _run([
                binary, "-y", "-stream_loop", "-1", "-i", str(track),
                "-t", f"{duration:.2f}",
                "-af", (
                    "volume=0.6,afade=t=in:st=0:d=1.0,"
                    f"afade=t=out:st={max(duration - 2.0, 0):.2f}:d=2.0"
                ),
                "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "160k",
                str(bed),
            ])
            if ok:
                parts.append(("bed", bed))
                log.info("Reel audio: %s", track.name)
        else:
            pad = _render_pad(binary, duration, workdir / "pad.m4a")
            if pad:
                parts.append(("bed", pad))

    if voice_path and want_pad:
        # A quiet bed under the voice keeps the reel from feeling clinical.
        pad = _render_pad(binary, duration, workdir / "pad.m4a")
        if pad:
            parts.append(("pad", pad))

    if not parts:
        return None

    if len(parts) == 1 and parts[0][0] == "bed":
        return parts[0][1]

    mixed = workdir / "mix.m4a"
    inputs = []
    filters = []
    labels = []

    for index, (kind, path) in enumerate(parts):
        inputs += ["-i", str(path)]

        if kind == "voice":
            filters.append(
                f"[{index}:a]volume={VOICE_VOLUME},"
                f"adelay={LEAD_IN_MS}|{LEAD_IN_MS}[v{index}]"
            )
        else:
            filters.append(f"[{index}:a]volume=0.22[bed{index}]")

        labels.append(f"[{'v' if kind == 'voice' else 'bed'}{index}]")

    graph = (
        ";".join(filters)
        + ";"
        + "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0[out]"
    )

    ok, error = _run([
        binary, "-y",
        *inputs,
        "-filter_complex", graph,
        "-map", "[out]",
        "-t", f"{duration:.2f}",
        "-ar", "44100", "-ac", "2",
        "-c:a", "aac", "-b:a", "160k",
        str(mixed),
    ])

    if not ok:
        log.warning("Audio mix failed: %s", error[-300:])
        return voice_path

    return mixed


# ── Layout ────────────────────────────────────────────────────────────────────
def _font(style_name, size, bold=True):
    style = FONT_STYLES.get(style_name, FONT_STYLES["modern"])
    candidates = style["bold"] if bold else style["regular"]

    return resolve_font(candidates, size, bold)


def _spaced(text, tracking=1):
    """Letter-spaced small caps that keeps the gaps between words."""

    if not tracking:
        return text

    separator = " " * tracking
    return ("   ").join(separator.join(word) for word in text.split())


def _wrap(draw, words, font, max_width):
    """Greedy wrap returning a list of lines, each a list of words."""

    lines, current = [], []

    for word in words:
        trial = " ".join(current + [word])
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width or not current:
            current.append(word)
        else:
            lines.append(current)
            current = [word]

    if current:
        lines.append(current)

    return lines


def _layout_words(draw, words, style_name, accent):
    """Pick the largest font size that fits, then place every word.

    Returns (font, [(word, x, y, colour), ...], line_height).
    """

    max_width = WIDTH - 300
    area_top, area_bottom = 470, 1430

    for size in range(96, 33, -4):
        font = _font(style_name, size, bold=True)
        lines = _wrap(draw, words, font, max_width)
        line_height = int(size * 1.34)
        block_height = line_height * len(lines)

        widest = max(
            draw.textbbox((0, 0), " ".join(line), font=font)[2] for line in lines
        )

        if block_height <= (area_bottom - area_top) and widest <= max_width:
            placed = []
            y = area_top + ((area_bottom - area_top) - block_height) // 2

            for line_index, line in enumerate(lines):
                text = " ".join(line)
                line_width = draw.textbbox((0, 0), text, font=font)[2]
                x = (WIDTH - line_width) // 2
                cursor = x

                for position, word in enumerate(line):
                    colour = TEXT
                    is_last = (
                        line_index == len(lines) - 1
                        and position == len(line) - 1
                    )
                    if is_last:
                        colour = accent

                    placed.append((word, cursor, y, colour))
                    cursor += draw.textbbox((0, 0), word + " ", font=font)[2]

                y += line_height

            return font, placed, line_height

    font = _font(style_name, 34, bold=True)
    lines = _wrap(draw, words, font, max_width)
    placed, y, line_height = [], area_top, 46

    for line_index, line in enumerate(lines):
        text = " ".join(line)
        line_width = draw.textbbox((0, 0), text, font=font)[2]
        cursor = (WIDTH - line_width) // 2

        for position, word in enumerate(line):
            colour = accent if (
                line_index == len(lines) - 1 and position == len(line) - 1
            ) else TEXT
            placed.append((word, cursor, y, colour))
            cursor += draw.textbbox((0, 0), word + " ", font=font)[2]

        y += line_height

    return font, placed, line_height


# ── Animation ─────────────────────────────────────────────────────────────────
def _base_frame(style_name, accent, label_text):
    """Background, label and rule — everything that never changes."""

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # Soft centre glow so the black does not look flat on a phone screen.
    glow = Image.new("L", (WIDTH, HEIGHT), 0)
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (WIDTH // 2 - 520, HEIGHT // 2 - 620, WIDTH // 2 + 520, HEIGHT // 2 + 620),
        fill=42,
    )
    glow = glow.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(220))
    image = Image.composite(
        Image.new("RGB", (WIDTH, HEIGHT), (20, 20, 25)), image, glow
    )
    draw = ImageDraw.Draw(image)

    label_font = _font(style_name, 25, bold=True)
    label = _spaced(label_text)
    label_width = draw.textbbox((0, 0), label, font=label_font)[2]
    draw.text(
        ((WIDTH - label_width) // 2, 300), label, font=label_font, fill=accent
    )
    draw.line((WIDTH // 2 - 45, 358, WIDTH // 2 + 45, 358), fill=accent, width=3)

    return image


def _monogram_layer(style_name, accent, signature, reference=None):
    """The JG ring, plus the verse reference when there is one."""

    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    centre_x, centre_y, radius = WIDTH // 2, 1660, 62

    if reference:
        # A Bible verse must carry its citation — it is the whole point.
        draw.text(
            (centre_x, centre_y - 130),
            str(reference).strip(),
            font=_font(style_name, 32, bold=False),
            fill=SUBTLE,
            anchor="mm",
        )

    draw.ellipse(
        (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius),
        outline=accent, width=2,
    )
    draw.line((centre_x - radius - 44, centre_y, centre_x - radius - 12, centre_y), fill=accent, width=2)
    draw.line((centre_x + radius + 12, centre_y, centre_x + radius + 44, centre_y), fill=accent, width=2)
    draw.text(
        (centre_x, centre_y - 1),
        _spaced(signature, 1),
        font=_font(style_name, 34, bold=True),
        fill=TEXT, anchor="mm",
    )

    return layer


def _timings(mark_count, marks, duration):
    """When each word should appear, in seconds."""

    if marks:
        return [LEAD_IN_MS / 1000 + offset for offset, _ in marks][:mark_count]

    start = LEAD_IN_MS / 1000
    finish = max(duration - TAIL_MS / 1000, start + 1.0)
    span = finish - start

    if mark_count <= 1:
        return [start]

    step = span / mark_count
    return [start + index * step for index in range(mark_count)]


def _render_frames(post, words, style_name, accent, duration, marks, framedir):
    """Write the PNG sequence. Returns the number of frames."""

    sample = ImageDraw.Draw(Image.new("RGB", (WIDTH, HEIGHT)))
    font, placed, line_height = _layout_words(sample, words, style_name, accent)

    label_text = CATEGORY_LABELS.get(post.get("category", ""), "BRIGHT SIDE DAILY")
    base = _base_frame(style_name, accent, label_text)
    monogram = _monogram_layer(
        style_name,
        accent,
        (os.getenv("IG_SIGNATURE", "JG").strip().upper() or "JG"),
        post.get("reference"),
    )

    signature_alpha_start = None
    appear = _timings(len(words), marks, duration)

    if appear:
        signature_alpha_start = appear[-1] + 0.9

    total_frames = int(duration * FPS)
    rise = WORD_RISE_MS / 1000.0

    for frame in range(total_frames):
        now = frame / FPS
        canvas = base.copy()

        # Words already finished go straight onto the canvas.
        active = []

        for index, (word, x, y, colour) in enumerate(placed):
            start = appear[index] if index < len(appear) else 1e9
            progress = (now - start) / rise

            if progress >= 1:
                ImageDraw.Draw(canvas).text((x, y), word, font=font, fill=colour)
            elif progress > 0:
                active.append((word, x, y, colour, progress))

        if active:
            layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)

            for word, x, y, colour, progress in active:
                eased = 1 - (1 - progress) ** 2
                offset = int((1 - eased) * 26)
                draw.text(
                    (x, y + offset),
                    word,
                    font=font,
                    fill=colour + (int(255 * eased),),
                )

            canvas = Image.alpha_composite(canvas.convert("RGBA"), layer).convert("RGB")

        if signature_alpha_start is not None and now >= signature_alpha_start:
            eased = min((now - signature_alpha_start) / 0.8, 1.0)
            faded = monogram.copy()
            alpha = faded.split()[3].point(lambda value: int(value * eased))
            faded.putalpha(alpha)
            canvas = Image.alpha_composite(canvas.convert("RGBA"), faded).convert("RGB")

        canvas.save(Path(framedir) / f"f{frame:05d}.png")

    return total_frames


# ── Public API ────────────────────────────────────────────────────────────────
def generate(card_path, output_path=None, duration=None, post=None):
    """
    Build a vertical Reel.

    `card_path` may be a card image (the original interface) or the post dict.
    Returns the MP4 path, or None when ffmpeg is unavailable or rendering
    fails, in which case the caller should fall back to the plain card.
    """

    binary = _ffmpeg()

    if not binary:
        log.error(
            "ffmpeg not found. Install it (apt-get install -y ffmpeg) "
            "or keep imageio-ffmpeg in requirements.txt."
        )
        return None

    if isinstance(card_path, dict):
        post = card_path
        card_path = None

    post = post or {}
    words = str(post.get("content", "")).split()

    if not words or ANIM_MODE == "none" or card_path:
        if not card_path:
            from generators.black_card_generator import BlackCardGenerator

            card_path = BlackCardGenerator().generate(post)

        return _static_reel(binary, card_path, output_path, duration)

    style_name = CATEGORY_STYLES.get(post.get("category", ""), "modern")
    accent = FONT_STYLES[style_name]["accent"]

    workdir = Path(tempfile.mkdtemp(prefix="reel_build_"))
    spoken = _speak(" ".join(words))

    voice_path, marks = (spoken if spoken else (None, []))

    if duration:
        total = float(duration)
    elif voice_path:
        speech = _duration_of(binary, voice_path)
        total = max(speech + LEAD_IN_MS / 1000 + TAIL_MS / 1000, 8.0)
    else:
        total = STATIC_DURATION

    log.info("Rendering reel: %.1fs, %d words", total, len(words))

    try:
        frames = _render_frames(
            post, words, style_name, accent, total, marks, workdir
        )

        audio = _build_audio(binary, voice_path, total, workdir)

        if output_path is None:
            slug = post.get("slot", "reel")
            index = post.get("content_index", 0)
            output_path = OUTPUT_DIR / f"{slug}_{index}.mp4"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fade_out = max(total - 0.7, 0)

        command = [
            binary, "-y",
            "-framerate", str(FPS),
            "-i", str(workdir / "f%05d.png"),
        ]

        if audio:
            command += ["-i", str(audio)]

        command += [
            "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out:.2f}:d=0.7,format=yuv420p",
            "-t", f"{total:.2f}",
            "-r", str(FPS),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

        if audio:
            command += ["-map", "0:v:0", "-map", "1:a:0",
                        "-c:a", "aac", "-b:a", "160k", "-shortest"]
        else:
            command += ["-an"]

        command.append(str(output_path))

        ok, error = _run(command)

        if not ok:
            log.error("ffmpeg failed:\n%s", error[-1200:])
            return None

        size_kb = output_path.stat().st_size / 1024
        log.info(
            "Reel ready: %s (%.0f KB, %.1fs, %d frames)",
            output_path, size_kb, total, frames,
        )

        return str(output_path)

    except Exception as exc:
        log.error("Animated reel failed (%s); falling back to a still card.", exc)
        return _static_reel(binary, card_path, output_path, duration)

    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        if voice_path:
            shutil.rmtree(Path(voice_path).parent, ignore_errors=True)


def _static_reel(binary, card_path, output_path, duration=None):
    """The original treatment: a card, a slow zoom, a gentle fade."""

    from PIL import Image

    card = Image.open(card_path).convert("RGB")
    target_w = int(WIDTH * 0.86)
    card = card.resize(
        (target_w, int(card.height * target_w / card.width)), Image.LANCZOS
    )

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    x = (WIDTH - card.width) // 2
    y = (HEIGHT - card.height) // 2
    canvas.paste(card, (x, y))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        (x - 1, y - 1, x + card.width, y + card.height), outline=(44, 44, 50), width=2
    )

    workdir = Path(tempfile.mkdtemp(prefix="reel_static_"))
    still = workdir / "_still.png"
    canvas.save(still, "PNG")

    total = float(duration or STATIC_DURATION)
    frames = int(total * FPS)

    audio = _build_audio(binary, None, total, workdir)

    if output_path is None:
        output_path = OUTPUT_DIR / f"{Path(card_path).stem}.mp4"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    zoom = (
        "zoompan=z='min(zoom+0.00035,1.08)'"
        ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )
    fade = f"fade=t=in:st=0:d=0.8,fade=t=out:st={max(total - 0.8, 0):.2f}:d=0.8"

    command = [binary, "-y", "-loop", "1", "-i", str(still)]

    if audio:
        command += ["-i", str(audio)]

    command += [
        "-vf", f"{zoom},{fade},format=yuv420p",
        "-t", str(total),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]

    if audio:
        command += ["-map", "0:v:0", "-map", "1:a:0",
                    "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        command += ["-an"]

    command.append(str(output_path))

    ok, error = _run(command)

    if not ok:
        log.error("Static reel failed:\n%s", error[-800:])
        return None

    shutil.rmtree(workdir, ignore_errors=True)

    log.info("Reel ready (static): %s (%.0f KB)", output_path, output_path.stat().st_size / 1024)

    return str(output_path)
