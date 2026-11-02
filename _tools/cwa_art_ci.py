#!/usr/bin/env python3
"""GitHub Action step: clean the art for every Coffee with Aaron post.

For each post in _posts/ with `cwa` in its categories, an `image:` URL, and `art`
not set to `photo` or `none`:
  - download the image (cargo.aaronaiken.me is public),
  - clean it with cwa_art.clean(),
  - write assets/cwa/art/<slug>.webp.

It never edits a post. assets/cwa/art/manifest.json remembers which image URL each
file was made from, so an unchanged post is skipped and a changed image is redone.
Writes a report to the run's summary page. Exits 1 if any image failed (after
trying them all), so the run shows red and GitHub emails Aaron.
"""
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from cwa_art import clean, paper_share  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
OUT = ROOT / "assets" / "cwa" / "art"
MANIFEST = OUT / "manifest.json"
SITE = "https://aaronaiken.me"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")  # the cleaned file is committed after this run


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def slug_of(path):
    # Jekyll's page.slug: the filename without the date prefix and extension.
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)


def categories(fm):
    c = fm.get("categories") or fm.get("category") or []
    if isinstance(c, str):
        c = c.split()
    return [str(x).lower() for x in c]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    rows, failed = [], 0

    for post in sorted(POSTS.glob("*.md")) + sorted(POSTS.glob("*.markdown")):
        fm = front_matter(post)
        if "cwa" not in categories(fm):
            continue
        image, art = fm.get("image"), str(fm.get("art", "sketch")).lower()
        if isinstance(image, dict):
            image = image.get("path")
        if not image or art in ("photo", "none"):
            continue
        slug = slug_of(post)
        dst = OUT / f"{slug}.webp"
        if manifest.get(slug) == image and dst.exists():
            rows.append((slug, "⏭ already clean", ""))
            continue
        try:
            url = image if image.startswith("http") else SITE + image
            req = urllib.request.Request(url, headers={"User-Agent": "cwa-art-action"})
            with urllib.request.urlopen(req, timeout=60) as r:
                src = Image.open(io.BytesIO(r.read()))
            out = clean(src)
            out.save(dst, quality=86)
            manifest[slug] = image
            share = paper_share(out)
            note = f"{out.width}×{out.height}, {share:.0%} paper"
            if share < 0.35:
                note += " — ⚠ little paper: is this a photo? set `art: photo`"
            rows.append((slug, "✅ cleaned", note))
        except Exception as e:  # keep going; report at the end
            failed += 1
            rows.append((slug, "❌ failed", f"{type(e).__name__}: {e}"))

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    lines = ["## Coffee with Aaron art", "", "| Post | Result | Notes |", "|---|---|---|"]
    lines += [f"| `{s}` | {r} | {n} |" for s, r, n in rows] or ["| — | nothing to do | |"]
    for s, r, _ in rows:
        if r.startswith("✅") and REPO:
            lines += ["", f"**{s}**", "",
                      f"![{s}](https://raw.githubusercontent.com/{REPO}/{BRANCH}/assets/cwa/art/{s}.webp)"]
    report = "\n".join(lines) + "\n"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(report)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
