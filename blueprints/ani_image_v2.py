"""A/B shim — run the tools/image-prompt-builder pipeline against the live endpoints.

Isolates ONE variable — prompt construction — so the structured builder
(extractor → SceneSpec → compile_scene → profiles.json) can be compared head-to-head
against the legacy `ani_normalize_scene` + regex path, while reusing the SAME Venice
render + vision-QA + Bunny loop (`_ani_render_venice`) for both. That's the clean A/B:
only the prompt changes, the render/QA/rehost stays identical.

Flip per request (`{"pipeline": "v2"}` in the /ani/photo POST body) or globally via
`ANI_IMAGE_PIPELINE=v2`. Venice-backend only for now. Lane: clothed + tasteful art nudes —
the sexual-act rows this builder once carried (rear/legs_up/partner) were removed, so the
clothed and tasteful-nude paths are all there is.

This module contains no scene content: it is control flow + endpoint wiring. All prompt
text comes from the builder package + profiles.json.
"""

import os
import sys

import requests

# The builder package lives beside the app in tools/. Resolve relative to this file so it
# works both locally and on PA regardless of REPO_ROOT.
_BUILDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "image-prompt-builder")
if _BUILDER not in sys.path:
    sys.path.insert(0, _BUILDER)

from image_prompt_builder import extract_scene, compile_scene, load_config  # noqa: E402

# Global default; a per-request 'pipeline' field overrides it.
ANI_IMAGE_PIPELINE = os.environ.get("ANI_IMAGE_PIPELINE", "v1").strip().lower()

_CFG = None


def _cfg():
    """Lazy-load + cache the profile config (fail-loud on a malformed file)."""
    global _CFG
    if _CFG is None:
        _CFG = load_config()
    return _CFG


def _xai_llm_call(messages):
    """The extractor's injected llm_call: one xAI/Grok chat completion → text. Mirrors the
    call `ani_photo_fields` already makes. Returns None on any failure (extractor then
    falls back to a clothed default)."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("ANI_NORMALIZE_MODEL", "grok-4.3")
    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 500, "temperature": 0.3, "messages": messages},
            timeout=20)
        if resp.status_code != 200:
            print(f"Ani v2 extractor HTTP {resp.status_code}: {resp.text[:120]}")
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Ani v2 extractor error: {e}")
        return None


def _chat_lines(messages):
    """Recent conversation as 'role: text' lines, stripped of image markers / briefings /
    system lines — the same filtering the normalizer does. Last 8 turns."""
    out = []
    for m in messages:
        c = (m.get("content") or "").strip()
        if not c or c == "📷" or m.get("image"):
            continue
        if c.startswith("[daily briefing") or c.startswith("[system:"):
            continue
        out.append(f"{m.get('role', '?')}: {c}")
    return out[-8:]


def generate_photo_v2(messages, orientation="portrait"):
    """Full builder pipeline against live endpoints.

    Returns (image_url, compiled_prompt). compiled_prompt is stored on the message exactly
    like the v1 `scene` (so retry + display keep working). Returns (None, None) when the
    backend isn't venice or extraction can't run."""
    # Imported lazily to avoid any import-order coupling with blueprints.ani.
    from blueprints.ani import (
        ani_get_bible, ani_load_state, _ani_bible_identity, _ani_bust_lead,
        _ani_render_venice, ANI_IMAGE_BACKEND)

    if ANI_IMAGE_BACKEND != "venice":
        print("Ani v2: builder is venice-only; backend is", ANI_IMAGE_BACKEND)
        return None, None

    spec = extract_scene(_chat_lines(messages), _xai_llm_call, state=ani_load_state() or {})
    spec.orientation = "landscape" if str(orientation or "").lower().startswith("land") else "portrait"

    _bible = ani_get_bible() or ""
    bible_id = _ani_bible_identity(_bible).strip()
    _bust = _ani_bust_lead(_bible)   # carry the v1 figure/bust anchor into v2 (identity strips the figure line otherwise)
    if _bust:
        bible_id = (bible_id + " " + _bust + ".").strip()
    req = compile_scene(spec, _cfg(), subject_identity=bible_id)
    applied = req.meta.get("applied_profiles", [])
    print(f"Ani PIC v2 profiles={applied} cfg{req.cfg} {req.width}x{req.height} steps{req.steps}")

    # Flags the extractor set — so the LOG shows *why* a scene rendered as it did (e.g. clothed=true
    # keeping her covered), not just the final prompt. INTENT_FLAGS live on the SceneSpec.
    from image_prompt_builder.scene_spec import INTENT_FLAGS
    flags = {k: getattr(spec, k) for k in INTENT_FLAGS if getattr(spec, k)}
    info = {
        "pipeline": "v2",
        "profiles": applied,
        "flags": flags or {"(none set)": True},
        "fields": {k: getattr(spec, k) for k in
                   ("hair", "outfit", "pose", "setting", "lighting", "camera", "expression")
                   if getattr(spec, k)},
    }
    url = _ani_render_venice(
        req.positive, req.negative, req.cfg, req.width, req.height, req.steps,
        scene=req.positive, pose=("complex_pose" in applied),
        clothed=("clothed" in applied), info=info)
    return url, req.positive
