#!/usr/bin/env python3
"""
Generate assets/icon.icns and assets/menubar.png for IntenType.
Requires: pip install pillow
Run from repo root: python scripts/make_icon.py
"""
import os, shutil, subprocess, math
from PIL import Image, ImageDraw

SIZES   = [16, 32, 64, 128, 256, 512, 1024]
ICONSET = "assets/IntenType.iconset"
ICNS    = "assets/icon.icns"
MENUBAR = "assets/menubar.png"         # idle  — 44x44 @2x
MENUBAR_FRAMES = [                     # recording animation frames
    f"assets/menubar_rec_{i}.png" for i in range(4)
]

BG    = (10, 10, 11, 255)
RED   = (232, 49, 42, 255)
WHITE = (240, 240, 242, 255)

def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded rect background
    r = size * 0.22
    d.rounded_rectangle([0, 0, size, size], radius=r, fill=BG)

    # Waveform bars  (6 bars, sine-shaped heights)
    n_bars   = 6
    bar_w    = size * 0.065
    gap      = size * 0.028
    total_w  = n_bars * bar_w + (n_bars - 1) * gap
    x_start  = (size - total_w) / 2
    center_y = size * 0.56
    max_h    = size * 0.40

    for i in range(n_bars):
        h = max_h * (0.35 + 0.65 * abs(math.sin(i * math.pi / (n_bars - 1))))
        x0 = x_start + i * (bar_w + gap)
        y0 = center_y - h / 2
        x1 = x0 + bar_w
        y1 = center_y + h / 2
        br = bar_w / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=br, fill=WHITE)

    # Red dot (top-right of bars)
    dot_r = size * 0.065
    dot_x = size * 0.74
    dot_y = size * 0.28
    d.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=RED)

    return img


def make_menubar(size: int = 44) -> Image.Image:
    """Waveform bars + red dot, transparent background, for macOS menubar."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    n_bars  = 6
    bar_w   = size * 0.10
    gap     = size * 0.05
    total_w = n_bars * bar_w + (n_bars - 1) * gap
    x_start = (size - total_w) / 2
    center_y = size * 0.60
    max_h    = size * 0.52

    for i in range(n_bars):
        h = max_h * (0.30 + 0.70 * abs(math.sin(i * math.pi / (n_bars - 1))))
        x0 = x_start + i * (bar_w + gap)
        y0 = center_y - h / 2
        x1 = x0 + bar_w
        y1 = center_y + h / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=bar_w / 2, fill=WHITE)

    # Red dot top-right
    dot_r = size * 0.10
    dot_x = size * 0.86
    dot_y = size * 0.18
    d.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=RED)

    return img


def make_menubar_recording(size: int = 44, phase: float = 0.0) -> Image.Image:
    """Recording animation frame — same style, bars animated by phase (0..1)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    n_bars   = 6
    bar_w    = size * 0.10
    gap      = size * 0.05
    total_w  = n_bars * bar_w + (n_bars - 1) * gap
    x_start  = (size - total_w) / 2
    center_y = size * 0.60
    max_h    = size * 0.56

    for i in range(n_bars):
        wave = abs(math.sin((i / (n_bars - 1)) * math.pi + phase * 2 * math.pi))
        h = max_h * (0.25 + 0.75 * wave)
        x0 = x_start + i * (bar_w + gap)
        y0 = center_y - h / 2
        x1 = x0 + bar_w
        y1 = center_y + h / 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=bar_w / 2, fill=WHITE)

    # Red dot — slightly larger during recording
    dot_r = size * 0.12
    dot_x = size * 0.86
    dot_y = size * 0.17
    d.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=RED)

    return img


def main():
    os.makedirs(ICONSET, exist_ok=True)

    for sz in SIZES:
        img = make_frame(sz)
        img.save(f"{ICONSET}/icon_{sz}x{sz}.png")
        if sz > 16:
            img.save(f"{ICONSET}/icon_{sz//2}x{sz//2}@2x.png")

    make_frame(32).save(f"{ICONSET}/icon_16x16@2x.png")

    result = subprocess.run(
        ["iconutil", "-c", "icns", ICONSET, "-o", ICNS],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("iconutil error:", result.stderr)
        raise SystemExit(1)

    shutil.rmtree(ICONSET)
    print(f"Created {ICNS}")

    # Idle menubar icon
    make_menubar(44).save(MENUBAR)
    print(f"Created {MENUBAR}")

    # Recording animation frames (4 phases of the wave)
    for i, path in enumerate(MENUBAR_FRAMES):
        make_menubar_recording(44, phase=i / len(MENUBAR_FRAMES)).save(path)
    print(f"Created {len(MENUBAR_FRAMES)} recording frames")


if __name__ == "__main__":
    main()
