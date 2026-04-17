#!/usr/bin/env python3
"""
publish_to_scribbles.py
Mirrors an aaronaiken.me blog post to cwa.omg.lol via the Scribbles Micropub API.

Usage:
    python3 publish_to_scribbles.py _posts/YYYY-MM-DD-your-post-slug.md

Options:
    --draft     Publish as draft (default: published)
    --dry-run   Print payload without posting to API
"""

import os
import sys
import re
import argparse
import requests

# --- Load .env manually (no external dependency) ---
def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

load_env()

# --- Configuration ---
SCRIBBLES_API_BASE = "https://scribbles.page/micropub"
SCRIBBLES_API_KEY  = os.environ.get("SCRIBBLES_API_KEY")
SITE_BASE_URL      = "https://aaronaiken.me"

# --- Front matter parser ---
def parse_front_matter(text):
    """
    Splits Jekyll front matter from body content.
    Returns (metadata dict, body string).
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body     = text[end + 3:].strip()

    metadata = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key   = key.strip()
        value = value.strip()

        # Strip inline YAML list brackets: [cwa, coffee] → ["cwa", "coffee"]
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            metadata[key] = items
        else:
            metadata[key] = value.strip('"').strip("'")

    return metadata, body

# --- Slug derivation from filename ---
def slug_from_filename(filepath):
    """
    Derives the post slug from the Jekyll filename.
    _posts/2026-04-14-my-post-title.md → my-post-title
    """
    basename = os.path.basename(filepath)
    basename = re.sub(r'\.(md|markdown)$', '', basename)
    slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', basename)
    return slug

# --- Kramdown attribute stripper ---
def strip_kramdown_attrs(text):
    """
    Removes Jekyll/Kramdown inline attribute syntax {:...} from body content.
    e.g. [link](url){:target="_blank" rel="noopener"} → [link](url)
    """
    return re.sub(r'\{:[^}]+\}', '', text)

# --- Canonical URL builder ---
def build_canonical_url(slug, metadata, filepath):
    """
    Builds the canonical aaronaiken.me URL using Jekyll's default permalink:
    /:categories/:year/:month/:day/:slug.html
    """
    categories = metadata.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    category = categories[0] if categories else "blog"

    # Try to parse date from front matter first, fall back to filename
    date_str   = metadata.get("date", "")
    date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(date_str))
    if date_match:
        year, month, day = date_match.groups()
    else:
        fn_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(filepath))
        if fn_match:
            year, month, day = fn_match.groups()
        else:
            year, month, day = "", "", ""

    return f"{SITE_BASE_URL}/{category}/{year}/{month}/{day}/{slug}.html"

# --- Attribution footer ---
def build_footer(slug, metadata, filepath):
    canonical_url = build_canonical_url(slug, metadata, filepath)
    return (
        f"\n\n---\n\n"
        f"*Originally published on [aaronaiken.me]({canonical_url}). "
        f"Coffee With Aaron is written by Aaron Aiken.*"
    )

# --- Post to Scribbles via Micropub ---
def post_to_scribbles(title, body, tags, published, dry_run):
    if not SCRIBBLES_API_KEY:
        print("!! SCRIBBLES_API_KEY not found. Check your .env file.")
        sys.exit(1)

    url     = SCRIBBLES_API_BASE
    headers = {
        "Authorization": f"Bearer {SCRIBBLES_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "type": ["h-entry"],
        "properties": {
            "name":        [title],
            "content":     [body],
            "category":    tags,
            "post-status": ["published" if published else "draft"]
        }
    }

    if dry_run:
        print("\n--- DRY RUN — payload that would be sent ---")
        print(f"URL:       {url}")
        print(f"Title:     {title}")
        print(f"Tags:      {tags}")
        print(f"Published: {published}")
        print(f"\n--- Body ---\n{body}")
        print("--- End dry run ---\n")
        return

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        # Micropub returns post URL in Location header
        post_url = response.headers.get("Location", "")
        print(f">> Successfully posted to Scribbles!")
        if post_url:
            print(f">> Scribbles URL: {post_url}")
        else:
            print(f">> Post created. No URL returned.")

    except requests.exceptions.HTTPError as e:
        print(f"!! Scribbles API error: {e}")
        print(f"!! Response: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"!! Unexpected error: {e}")
        sys.exit(1)

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Mirror a Jekyll post to Scribbles.")
    parser.add_argument("filepath", help="Path to the _posts/ markdown file")
    parser.add_argument("--draft",   action="store_true", help="Post as draft instead of published")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without posting")
    args = parser.parse_args()

    filepath = args.filepath

    if not os.path.exists(filepath):
        print(f"!! File not found: {filepath}")
        sys.exit(1)

    with open(filepath, "r") as f:
        raw = f.read()

    metadata, body = parse_front_matter(raw)

    title = metadata.get("title", "Untitled")
    tags  = metadata.get("categories", [])
    if isinstance(tags, str):
        tags = [tags]

    slug          = slug_from_filename(filepath)
    clean_body    = strip_kramdown_attrs(body)
    footer        = build_footer(slug, metadata, filepath)
    full_body     = clean_body + footer
    published     = not args.draft
    canonical_url = build_canonical_url(slug, metadata, filepath)

    print(f">> File:      {filepath}")
    print(f">> Title:     {title}")
    print(f">> Slug:      {slug}")
    print(f">> Tags:      {tags}")
    print(f">> Published: {published}")
    print(f">> Canonical: {canonical_url}")

    confirm = input("\nPost to Scribbles? [y/N] ").strip().lower()
    if confirm != "y":
        print(">> Aborted.")
        sys.exit(0)

    post_to_scribbles(title, full_body, tags, published, args.dry_run)

if __name__ == "__main__":
    main()