#!/usr/bin/env python3
"""Show what the builder compiles for a few SFW scenes. `python3 demo.py`."""

import json

from image_prompt_builder import (
    SceneSpec, compile_scene, load_config, plan_retry, extract_scene,
)

CFG = load_config()
IDENTITY = "{SUBJECT_IDENTITY}"   # the caller injects the real character anchor here


def show(title, spec):
    req = compile_scene(spec, CFG, subject_identity=IDENTITY)
    print(f"\n=== {title} ===")
    print("POSITIVE:", req.positive)
    print("NEGATIVE:", req.negative)
    print(f"cfg={req.cfg} steps={req.steps} dims={req.width}x{req.height} "
          f"rear_qa={req.require_rear_qa} partner_qa={req.partner_qa}")
    print("meta:", json.dumps(req.meta))


if __name__ == "__main__":
    show("Clothed, at home", SceneSpec(
        hair="caramel-blonde waves", outfit="an oversized cream sweater and jeans",
        setting="curled on the sofa by the window", lighting="soft afternoon light",
        camera="eye-level, full length", clothed=True))

    show("Writing (laptop-anchored)", SceneSpec(
        hair="loose waves", outfit="a soft robe", setting="at her desk",
        writing=True, camera="three-quarter from the side"))

    show("Complex pose, clothed", SceneSpec(
        hair="waves", outfit="a slip dress", pose="reclining across the chaise",
        clothed=True, pose_complex=True))

    # Explicit-payload profiles compile structurally even while their content rows are blank.
    show("Rear (payload blank — structure only)", SceneSpec(
        hair="waves", setting="the bedroom", rear=True, nude=True))

    # Full front-end: chat -> SceneSpec -> RenderRequest. `llm_call` is faked here; in the
    # app it wraps the Grok/xAI chat endpoint. The failed-read path falls back to clothed.
    fake_json = (
        '{"hair": "loose caramel-blonde waves", "outfit": "a grey oversized cardigan over a '
        'white tee", "pose": "leaning on the kitchen counter", "setting": "the kitchen, morning", '
        '"lighting": "bright morning light", "camera": "eye-level, waist up", '
        '"expression": "laughing, looking off-camera", "clothed": true}'
    )
    spec = extract_scene(["aaron: send me one from this morning", "ani: haha okay, one sec"],
                         llm_call=lambda m: fake_json, state={"where": "the kitchen"})
    show("chat -> extract -> compile", spec)

    # Retry demo: a not-rear verdict escalates and recompiles.
    spec = SceneSpec(hair="waves", setting="the bedroom", rear=True, nude=True)
    plan = plan_retry(spec, {"ok": False, "defect": "not_rear"}, attempt=1, max_attempts=4)
    print(f"\n=== retry(not_rear) -> retry={plan.should_retry} recompile={plan.recompile} "
          f"escalations={plan.spec.escalations if plan.spec else None} note={plan.note!r} ===")
