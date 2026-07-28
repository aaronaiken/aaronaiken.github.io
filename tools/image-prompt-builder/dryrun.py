#!/usr/bin/env python3
"""Local dry-run: see exactly what the V2 builder would send, with NO deploy, NO image
generation, and NO touching the live Ani conversation.

Runs the REAL extractor (xAI/Grok) against your local XAI_API_KEY, then compiles — and
prints the SceneSpec + the positive/negative/params that would go to Venice. If no key is
set it falls back to the clothed default so you still see the pipeline shape.

Usage:
    python3 dryrun.py                                  # canned clothed conversation
    python3 dryrun.py "ani: curled on the couch in my grey hoodie, rainy out"
    echo "ani: ..." | python3 dryrun.py -              # read a line from stdin
"""

import json
import os
import sys

import requests

from image_prompt_builder import extract_scene, compile_scene, load_config

CFG = load_config()


def xai_llm_call(messages):
    """One xAI/Grok chat completion → text, or None (extractor then uses the clothed default)."""
    key = os.environ.get("XAI_API_KEY")
    if not key:
        print("[no XAI_API_KEY — extractor will fall back to the clothed default]\n")
        return None
    model = os.environ.get("ANI_NORMALIZE_MODEL", "grok-4.3")
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 500, "temperature": 0.3, "messages": messages},
            timeout=20)
        if r.status_code != 200:
            print(f"[xAI HTTP {r.status_code}: {r.text[:120]}]\n")
            return None
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[xAI error: {e}]\n")
        return None


def main():
    arg = " ".join(sys.argv[1:]).strip()
    if arg == "-":
        arg = sys.stdin.read().strip()
    if not arg:
        chat = ["aaron: send me a pic of you right now",
                "ani: mm okay — i'm curled on the couch in my grey oversized hoodie, rain on the window"]
    else:
        chat = arg.splitlines() if "\n" in arg else [arg if ":" in arg else f"ani: {arg}"]

    print("CHAT LINES:")
    for c in chat:
        print("  " + c)
    print()

    spec = extract_scene(chat, xai_llm_call)
    print("SCENE SPEC:")
    print("  fields :", {k: getattr(spec, k) for k in
                          ("hair", "outfit", "pose", "setting", "lighting", "camera", "expression")
                          if getattr(spec, k)})
    print("  flags  :", {k: getattr(spec, k) for k in
                         ("nude", "clothed", "rear", "legs_up", "partner", "writing", "pose_complex")
                         if getattr(spec, k)})
    print()

    req = compile_scene(spec, CFG, subject_identity="{SUBJECT_IDENTITY}")
    print("WOULD SEND TO VENICE:")
    print("  positive:", req.positive)
    print("  negative:", req.negative)
    print(f"  cfg={req.cfg} steps={req.steps} dims={req.width}x{req.height} "
          f"rear_qa={req.require_rear_qa} partner_qa={req.partner_qa}")
    print("  meta    :", json.dumps(req.meta))


if __name__ == "__main__":
    main()
