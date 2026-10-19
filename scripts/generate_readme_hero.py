#!/usr/bin/env python3
"""Generate a compact, animated README hero for MCP-Doctor.

This is reproducible source for the committed GIF. It intentionally draws the
graphic from vector-like primitives so the repository does not depend on
external image assets or image-generation services.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "readme" / "hero-animation.gif"
WIDTH, HEIGHT = 960, 360
CYAN = (57, 230, 191)
BLUE = (48, 133, 255)
PALE = (232, 243, 255)
MUTED = (144, 170, 200)


def font(kind: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    choices = {
        "bold": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ),
        "regular": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ),
        "mono": (
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        ),
    }
    for candidate in choices[kind]:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font("bold", 49)
F_SUBTITLE = font("bold", 17)
F_BODY = font("regular", 15)
F_SMALL = font("regular", 12)
F_CHIP = font("bold", 10)
F_FOOT = font("bold", 9)


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, ...],
    outline: tuple[int, ...] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)


def draw_static_scene() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        blend = y / HEIGHT
        draw.line(
            (0, y, WIDTH, y),
            fill=(5 + int(7 * blend), 13 + int(10 * blend), 26 + int(19 * blend)),
        )

    grid = ImageDraw.Draw(image, "RGBA")
    for x in range(24, WIDTH, 32):
        grid.line((x, 0, x, HEIGHT), fill=(38, 81, 122, 25), width=1)
    for y in range(20, HEIGHT, 32):
        grid.line((0, y, WIDTH, y), fill=(38, 81, 122, 21), width=1)

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((510, 22, 910, 338), fill=(18, 135, 210, 30))
    glow_draw.ellipse((610, 75, 820, 285), fill=(45, 225, 198, 21))
    glow = glow.filter(ImageFilter.GaussianBlur(64))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    draw = ImageDraw.Draw(image, "RGBA")

    draw.ellipse((42, 36, 51, 45), fill=(*CYAN, 255))
    draw.text((61, 32), "MCP INFRASTRUCTURE  /  DIAGNOSTIC SYSTEM", font=F_SMALL, fill=(*MUTED, 255))
    draw.text((40, 78), "MCP-DOCTOR", font=F_TITLE, fill=(*PALE, 255))
    draw.rounded_rectangle((43, 143, 258, 148), radius=2, fill=(*CYAN, 240))
    draw.text((43, 166), "FIND THE BREAK.", font=F_SUBTITLE, fill=(*CYAN, 255))
    draw.text((43, 194), "FIX THE HANDSHAKE.", font=F_SUBTITLE, fill=(*PALE, 245))
    draw.text((43, 235), "Explainable MCP server diagnostics.", font=F_BODY, fill=(*MUTED, 255))
    draw.text((43, 258), "Local-first  ·  bounded probes  ·  no tool execution", font=F_SMALL, fill=(133, 164, 195, 255))

    x = 43
    for label, chip_width in (("CONFIG", 75), ("PROTOCOL", 88), ("REPORT", 75)):
        rounded(draw, (x, 300, x + chip_width, 327), 9, (11, 28, 47, 220), outline=(45, 130, 150, 160))
        draw.ellipse((x + 9, 310, x + 15, 316), fill=(*CYAN, 255))
        draw.text((x + 22, 307), label, font=F_CHIP, fill=(207, 224, 241, 255))
        x += chip_width + 9

    rounded(draw, (526, 51, 918, 322), 20, (7, 21, 38, 236), outline=(65, 113, 160, 200), width=2)
    draw.rounded_rectangle((526, 51, 918, 88), radius=20, fill=(16, 38, 62, 245))
    draw.rectangle((526, 70, 918, 88), fill=(16, 38, 62, 245))
    for index, color in enumerate(((248, 113, 113, 255), (251, 191, 36, 255), (*CYAN, 255))):
        draw.ellipse((546 + index * 17, 65, 554 + index * 17, 73), fill=color)
    draw.text((610, 62), "mcp-doctor  /  live probe", font=F_SMALL, fill=(161, 190, 215, 255))

    for index, (y, label, color) in enumerate(
        ((123, "CFG", BLUE), (180, "RPC", CYAN), (237, "SCAN", BLUE))
    ):
        rounded(draw, (561, y, 633, y + 32), 8, (14, 39, 59, 240), outline=(*color, 180))
        draw.text((575, y + 8), label, font=F_CHIP, fill=(*color, 255))
        if index < 2:
            draw.line((597, y + 32, 597, y + 57), fill=(57, 230, 191, 180), width=2)

    for y in (139, 196, 253):
        draw.line((637, y, 760, y), fill=(60, 132, 197, 100), width=2)

    rounded(draw, (766, 110, 895, 170), 9, (11, 34, 51, 245), outline=(48, 133, 255, 150))
    draw.text((778, 120), "HANDSHAKE", font=F_CHIP, fill=(132, 170, 205, 255))
    draw.text((778, 139), "CONNECTED", font=font("bold", 13), fill=(*CYAN, 255))
    rounded(draw, (766, 180, 895, 240), 9, (11, 34, 51, 245), outline=(57, 230, 191, 155))
    draw.text((778, 190), "TOOL CATALOG", font=F_CHIP, fill=(132, 170, 205, 255))
    draw.text((778, 209), "READ-ONLY", font=font("bold", 13), fill=(*CYAN, 255))
    rounded(draw, (766, 250, 895, 294), 9, (11, 34, 51, 245), outline=(48, 133, 255, 150))
    draw.text((778, 258), "FINDINGS", font=F_CHIP, fill=(132, 170, 205, 255))
    draw.ellipse((778, 277, 785, 284), fill=(*CYAN, 255))
    draw.text((791, 273), "3 checks ready", font=F_SMALL, fill=(211, 228, 242, 255))
    draw.line((40, 344, 920, 344), fill=(41, 78, 111, 110), width=1)
    draw.text((42, 335), "MCP-DOCTOR  ·  ALPHA 0.2", font=F_FOOT, fill=(88, 121, 153, 255))
    return image


def make_frames() -> list[Image.Image]:
    base = draw_static_scene()
    frames: list[Image.Image] = []
    # Packet dots travel through the diagnostic pipeline while the underline
    # and the live status indicator subtly pulse.
    for frame_index in range(8):
        t = frame_index / 8
        frame = base.copy()
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        for dot_index in range(5):
            progress = (t + dot_index / 5) % 1
            px = 648 + int(102 * progress)
            py = 139 + int(9 * math_sin(progress * 6.283185307))
            alpha = 235 if dot_index == 0 else 118
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(*CYAN, alpha))
        pulse = int(170 + 85 * (0.5 + 0.5 * math_sin(t * 6.283185307)))
        draw.ellipse((878, 93, 884, 99), fill=(*CYAN, pulse))
        frame = Image.alpha_composite(frame, overlay)
        frames.append(frame.convert("RGB"))
    return frames


def math_sin(value: float) -> float:
    # Small wrapper keeps the only non-Pillow dependency in the Python stdlib.
    import math
    return math.sin(value)


def main() -> None:
    frames = make_frames()
    # Build one shared palette from sampled frames to keep the GIF small and
    # predictable instead of storing a separate palette for each frame.
    thumbnails = [frame.resize((192, 72), Image.Resampling.BILINEAR) for frame in frames]
    palette_sheet = Image.new("RGB", (768, 144), (0, 0, 0))
    for index, thumbnail in enumerate(thumbnails):
        palette_sheet.paste(thumbnail, ((index % 4) * 192, (index // 4) * 72))
    palette = palette_sheet.quantize(colors=56, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    quantized = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        OUTPUT,
        save_all=True,
        append_images=quantized[1:],
        duration=130,
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(f"Generated {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} bytes, {len(quantized)} frames)")


if __name__ == "__main__":
    main()
