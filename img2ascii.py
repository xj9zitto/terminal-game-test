#!/usr/bin/env python3
"""
img2ascii.py

Convert an image into an ASCII texture file.

Usage:
    python img2ascii.py -i input.png -o textures/#.txt [--color] [--invert] [--size 32]

Options:
    -i, --input    Input image path
    -o, --output   Output text file path
    --color        Emit ANSI 24-bit color around each char (truecolor)
    --invert       Invert brightness mapping (dark->light)
    --size         Texture size (NxN). Default 32

Output:
    A text file where each line corresponds to a row of the ASCII texture.
    If --color is used the file will contain ANSI escape sequences around each character.
"""

import argparse
from PIL import Image

# The brightness ramp you requested (dark -> bright)
ASCII_RAMP = ".:-=+*#%@"

ESC = "\x1b"
RESET = ESC + "[0m"

def rgb_to_ansi_fg(r, g, b):
    """Return SGR foreground ANSI 24-bit sequence for color."""
    return f"{ESC}[38;2;{r};{g};{b}m"

def image_to_ascii_lines(path, size=32, invert=False, use_color=False):
    """
    Returns list[str] of 'size' strings, each representing a row of ASCII texture.
    If use_color is True the visible characters are wrapped in ANSI color sequences.
    """
    img = Image.open(path).convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    px = img.load()
    w, h = img.size

    ramp = ASCII_RAMP
    ramp_len = len(ramp)

    out_lines = []
    for y in range(h):
        row_chars = []
        for x in range(w):
            r, g, b = px[x, y]
            # compute luminance (0..255)
            lum = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            if invert:
                lum = 255 - lum
            idx = int((lum / 255.0) * (ramp_len - 1))
            idx = max(0, min(ramp_len - 1, idx))
            ch = ramp[idx]

            if use_color:
                ansi = rgb_to_ansi_fg(r, g, b)
                row_chars.append(f"{ansi}{ch}{RESET}")
            else:
                row_chars.append(ch)
        out_lines.append("".join(row_chars))
    return out_lines

def main():
    p = argparse.ArgumentParser(description="Convert image -> ASCII texture")
    p.add_argument("-i", "--input", required=True, help="Input image path")
    p.add_argument("-o", "--output", required=True, help="Output text file")
    p.add_argument("--color", action="store_true", help="Wrap chars in ANSI truecolor (24-bit) sequences")
    p.add_argument("--invert", action="store_true", help="Invert brightness mapping (dark<->light)")
    p.add_argument("--size", type=int, default=32, help="Output texture size (NxN). Default 32")
    args = p.parse_args()

    lines = image_to_ascii_lines(args.input, size=args.size, invert=args.invert, use_color=args.color)

    with open(args.output, "w", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")

    print(f"[img2ascii] Wrote {args.output}  (size={args.size}, color={args.color}, invert={args.invert})")

if __name__ == "__main__":
    main()
