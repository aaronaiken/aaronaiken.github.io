#!/usr/bin/env python3
"""Prepare a Midjourney sketch for a Coffee with Aaron post.

Flattens the uneven 'paper' of the render to pure white, so the image melts into
the page (multiply in daylight, inverted + screen before sunup), and resizes it.

    python3 _tools/cwa_art.py in.png out.webp [--width 1920]

The GitHub Action (_tools/cwa_art_ci.py) imports clean() from here; you only need
the command line to try an image by hand. Needs Pillow and numpy.
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter


def clean(im, width=1920):
    """Return a copy of `im` with the paper flattened to pure white, at most `width` wide."""
    im = im.convert("RGB")
    if im.width > width:
        im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
    px = np.asarray(im).astype(float)
    # Flat-field: estimate the paper colour everywhere (large max filter + blur), divide it out.
    paper = np.asarray(im.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(60))).astype(float)
    n = np.clip(px / np.maximum(paper, 1), 0, 1)
    # Anything close to paper becomes pure white (smoothstep 0.86 -> 0.95), so no rectangle shows.
    lum = n.mean(axis=2, keepdims=True)
    t = np.clip((lum - 0.86) / (0.95 - 0.86), 0, 1)
    t = t * t * (3 - 2 * t)
    out = n * (1 - t) + t
    return Image.fromarray((out * 255).round().astype("uint8"))


def paper_share(im):
    """Fraction of pixels that are pure white: a quick health check (a good sketch is mostly paper)."""
    a = np.asarray(im.convert("L"))
    return float((a >= 254).mean())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--width", type=int, default=1920)
    a = p.parse_args()
    out = clean(Image.open(a.src), a.width)
    out.save(a.dst, quality=86)
    print(f"{a.dst}: {out.width}x{out.height}, {paper_share(out):.0%} paper")
