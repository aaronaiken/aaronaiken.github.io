"""compile_scene() — SceneSpec + profiles -> RenderRequest.

This is the pure heart of the builder. No HTTP, no file I/O, no clock, no randomness:
same inputs -> byte-identical output. That's what makes it unit-testable with golden
strings, which is the whole point of pulling this logic out of the old 150-line,
API-coupled `ani_generate_image`.

The old function re-derived intent from a string with regexes, then did `re.sub` surgery
to remove clauses its own upstream normalizer kept emitting. Here, intent arrives as flags
on the SceneSpec and the positive prompt is BUILT from fields — so there's never a
conflicting clause to strip. The bug class disappears by construction.
"""

from __future__ import annotations

from .render_request import RenderRequest
from .scene_spec import SceneSpec, SCENE_FIELDS
from .profiles import matching_profiles, resolve_param


def _dedupe(seq):
    """Order-preserving dedupe for negative terms layered from multiple profiles."""
    seen = set()
    out = []
    for x in seq:
        x = (x or "").strip()
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out


def _scene_body(spec: SceneSpec) -> str:
    """The descriptive fields, in the fixed SCENE_FIELDS order, joined as one clause.
    Empty fields drop out. `hair` leads by design (earliest tokens weigh most)."""
    parts = [getattr(spec, f, "").strip() for f in SCENE_FIELDS]
    return ", ".join(p for p in parts if p)


def compile_scene(spec: SceneSpec, cfg: dict, *, subject_identity: str = "") -> RenderRequest:
    """Compile one scene into a fully-resolved RenderRequest.

    `subject_identity` is a caller-supplied slot (the character/identity anchor). The
    builder never hardcodes it — it's injected here so "who she is" stays separate from
    "what's happening" and "how to render", the three-way split the old code braided
    together in string concatenation.
    """
    base = cfg["base"]
    defaults = cfg["engine_defaults"]
    applied = matching_profiles(spec, cfg["profiles"])

    drop_solo = any(p.get("drop_solo") for p in applied)
    require_rear_qa = any(p.get("require_rear_qa") for p in applied)
    partner_qa = any(p.get("partner_qa") for p in applied)

    # --- positive prompt: prefix + anchors + framing + scene body + extras + identity + suffix ---
    anchors = []
    if not drop_solo:
        anchors.append(base["solo_anchor"])
    for p in applied:                       # profile anchors (e.g. partner/rear leads)
        if p.get("anchor"):
            anchors.append(p["anchor"])

    extras = [p["positive_extra"].strip() for p in applied if p.get("positive_extra")]

    pieces = [
        base["positive_prefix"],
        "".join(anchors),
        base["framing"],
        _scene_body(spec) + "." if _scene_body(spec) else "",
        " " + " ".join(extras) if extras else "",
        " " + subject_identity.strip() if subject_identity.strip() else "",
        base["positive_suffix"],
    ]
    positive = "".join(pieces)
    positive = " ".join(positive.split())   # collapse whitespace; deterministic

    # --- negative prompt: base + every applied profile's negatives, deduped, order-stable ---
    neg_terms = list(base["negative"])
    for p in applied:
        neg_terms.extend(p.get("negative", []))
    negative = ", ".join(_dedupe(neg_terms))

    # --- engine dials: per-param resolution (see resolve_param docstring) ---
    the_cfg = resolve_param("cfg", applied, defaults, "cfg")
    steps = int(resolve_param("steps", applied, defaults, "steps"))
    # Escalations set by the retry policy. `clean_limbs` is the one content-free knob the
    # compiler honors directly (more steps clean up extremities); rear_boost / feet_fix are
    # surfaced in meta for the operator's (payload) profile rows to key off.
    esc = spec.escalations or {}
    if esc.get("clean_limbs"):
        steps += 5 * int(esc["clean_limbs"])
    dims = defaults["dims_landscape"] if spec.orientation == "landscape" else defaults["dims_portrait"]
    width, height = dims

    return RenderRequest(
        positive=positive,
        negative=negative,
        cfg=float(the_cfg),
        steps=steps,
        width=int(width),
        height=int(height),
        require_rear_qa=require_rear_qa,
        partner_qa=partner_qa,
        meta={
            "applied_profiles": [p["id"] for p in applied],
            "drop_solo": drop_solo,
            "escalations": dict(spec.escalations or {}),
        },
    )
