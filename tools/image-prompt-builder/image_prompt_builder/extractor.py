"""Extractor — ChatContext -> SceneSpec. The ONE llm read of the pipeline.

This replaces both `ani_normalize_scene` (freeform prompt line) and the freeform half of
`ani_photo_fields`. Instead of emitting a string that the compiler has to re-parse, the
extractor emits STRUCTURED fields plus the boolean intent flags directly. That single
change is what lets every downstream regex go away.

The LLM call itself is I/O, so it stays injected (`llm_call`) and out of the pure core.
Everything here except the injected call is pure and unit-testable:

    build_extractor_messages()  pure  -> the system+user messages (the prompt contract)
    parse_extractor_json()      pure  -> LLM text/dict -> SceneSpec (or None)
    default_scene()             pure  -> the safe clothed fallback
    extract_scene(llm_call)     thin  -> build -> call -> parse -> fallback

Default posture is CLOTHED. Most photos are fully dressed; undress is only ever set when
the scene clearly shows it. The explicit flags (rear / legs_up / partner / nude) are
defined here as terse one-line CLASSIFIERS — category labels, not descriptor content.
"""

from __future__ import annotations

import json
import re

from .scene_spec import SceneSpec, SCENE_FIELDS, INTENT_FLAGS


# The full output contract, as a JSON schema — usable for forced structured output
# (the app already forces tool-schemas elsewhere, e.g. the ticket-draft flow).
EXTRACTOR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **{k: {"type": "string"} for k in SCENE_FIELDS},
        **{k: {"type": "boolean"} for k in INTENT_FLAGS},
    },
    "required": list(SCENE_FIELDS) + list(INTENT_FLAGS),
}


# --- the prompt contract ------------------------------------------------------------

_FIELD_GUIDE = (
    "Fields (a short plain phrase, or \"\" if the scene doesn't make it clear):\n"
    "- hair: her hair right now — style and state (e.g. 'loose caramel-blonde waves', "
    "'up in a soft messy bun').\n"
    "- outfit: exactly what she is wearing — be specific about garments, colors, and fabric "
    "(e.g. 'an oversized cream knit sweater and black leggings', 'a striped cotton sundress'). "
    "If the scene clearly shows her undressed, state that plainly instead of inventing clothes.\n"
    "- pose: how her body is positioned — standing / sitting / lying / kneeling, and what her "
    "arms, hands, and legs are doing.\n"
    "- setting: the room or place and the surroundings around her.\n"
    "- lighting: the light in the scene (e.g. 'soft afternoon light through the window', "
    "'warm lamplight').\n"
    "- camera: angle and framing (e.g. 'eye-level, three-quarter, full length', "
    "'close-up from the side').\n"
    "- expression: her face, gaze, and mood.\n"
)

_FLAG_GUIDE = (
    "Flags (booleans — set each from what the scene shows; do not infer beyond it):\n"
    "- clothed: she is wearing clothing. DEFAULT true — most photos are fully clothed.\n"
    "- nude: she is clearly undressed in the scene. Default false.\n"
    "- pose_complex: the pose is anything beyond standing or simple upright sitting — "
    "lying, reclining, on her side, kneeling, on-top, or bent over.\n"
    "- writing: she is writing, composing, journaling, or typing. (She always uses a "
    "laptop, never pen-and-paper — set this and the compiler anchors the laptop.)\n"
    "- rear: the camera is behind her (a from-behind view). Default false.\n"
    "- legs_up: she is on her back with her legs raised. Default false.\n"
    "- partner: the scene depicts a sexual act involving the viewer. Default false.\n"
)

_RULES = (
    "Rules:\n"
    "- Describe faithfully what the scene implies. Do not add clothing that isn't there, "
    "and do not invent undress that isn't there.\n"
    "- Use the MOST RECENT described scene; earlier chat is only background. Never carry a "
    "prior photo's outfit, pose, or location forward.\n"
    "- Short plain phrases inside values. No field labels inside values, no commentary.\n"
    "- Output ONLY the JSON object with exactly these keys — nothing else.\n"
)

_EXAMPLE = (
    "Example output for a clothed scene:\n"
    "{\"hair\": \"loose caramel-blonde waves\", \"outfit\": \"an oversized cream knit sweater "
    "and black leggings\", \"pose\": \"curled sideways into the sofa cushions, knees up, mug in "
    "both hands\", \"setting\": \"the living room by the window\", \"lighting\": \"soft grey "
    "afternoon light\", \"camera\": \"eye-level, three-quarter, full length\", \"expression\": "
    "\"a small warm smile, looking at the camera\", \"clothed\": true, \"nude\": false, "
    "\"pose_complex\": false, \"writing\": false, \"rear\": false, \"legs_up\": false, "
    "\"partner\": false}"
)


def build_extractor_messages(chat_lines, state=None, now_hint=None):
    """Pure. Build the (system, user) messages for the extractor LLM call.

    chat_lines: list of "role: text" strings (already trimmed of image markers / system lines).
    state:      optional dict {where, wearing, doing} — her live status, used ONLY to fill an
                unstated setting/outfit (the described scene always wins).
    now_hint:   optional string (e.g. 'Tuesday afternoon') for seasonal/time grounding.
    """
    keys = list(SCENE_FIELDS) + list(INTENT_FLAGS)
    system = (
        "You convert a chat between Aaron and his companion Ani into a STRUCTURED description "
        "of the single photo she would send RIGHT NOW.\n"
        f"Return ONLY a JSON object with EXACTLY these keys: {', '.join(keys)}.\n\n"
        + _FIELD_GUIDE + "\n" + _FLAG_GUIDE + "\n" + _RULES + "\n" + _EXAMPLE
    )

    convo = "\n".join(chat_lines) if chat_lines else "(no chat yet)"
    parts = [f"Conversation so far (most recent last):\n{convo}"]
    if state:
        st = "; ".join(f"{k}={state.get(k, '')}" for k in ("where", "wearing", "doing") if state.get(k))
        if st:
            parts.append(
                "Her live status (use ONLY to fill an unstated setting or baseline outfit — "
                f"the described scene always wins):\n{st}")
    if now_hint:
        parts.append(f"Right now: {now_hint}")
    parts.append("Return the JSON object for the photo she would send right now. JSON only.")
    user = "\n\n".join(parts)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# --- parsing + fallback -------------------------------------------------------------

def parse_extractor_json(text_or_dict):
    """Pure. Turn the extractor's response into a SceneSpec, or None if unparseable.

    Accepts a dict (already-parsed / forced-schema output) or raw text that may wrap the
    JSON in prose or ```code fences``` — the first balanced {...} block is taken."""
    if isinstance(text_or_dict, dict):
        return SceneSpec.from_extractor(text_or_dict)
    if not text_or_dict:
        return None
    m = re.search(r"\{.*\}", str(text_or_dict), re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return SceneSpec.from_extractor(data)


def default_scene(state=None):
    """Pure. The safe fallback when extraction fails: a clothed spec, seeded from live
    status if available. Never returns undress — a failed read must not guess NSFW."""
    state = state or {}
    return SceneSpec(
        outfit=(state.get("wearing") or "").strip(),
        setting=(state.get("where") or "").strip(),
        clothed=True,
    )


def extract_scene(chat_lines, llm_call, *, state=None, now_hint=None):
    """Thin adapter: build -> call -> parse -> fallback. `llm_call` is a callable that
    takes the messages list and returns the model's text (or a dict). Injecting it keeps
    this testable with a fake and keeps the network out of the package.

    In the app, `llm_call` wraps the xAI/Grok chat endpoint (the same client
    `ani_photo_fields` already uses). A failed or empty read falls back to a clothed
    default rather than raising — a photo request should never hard-error."""
    messages = build_extractor_messages(chat_lines, state=state, now_hint=now_hint)
    try:
        raw = llm_call(messages)
    except Exception:
        raw = None
    spec = parse_extractor_json(raw)
    return spec if spec is not None else default_scene(state)
