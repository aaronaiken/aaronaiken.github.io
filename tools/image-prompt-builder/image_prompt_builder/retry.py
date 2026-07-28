"""Retry policy — turn a QA verdict into the NEXT attempt.

The old loop's biggest wasted lever: QA returned a defect code ('feet-glitch', 'not-rear',
...) and the loop re-rolled the *identical* prompt with a new seed, then shipped the last
frame even if still broken. Here the verdict drives a targeted adjustment — strengthen the
rear push, force the feet negative on, nudge cfg for a duplicate — and only after a real
escalation budget is spent do we withhold rather than ship-broken.

Pure functions. `plan_retry` decides; the caller applies (recompile if the spec changed,
else merge the ad-hoc negative/cfg deltas into the existing RenderRequest and re-render).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .scene_spec import SceneSpec


@dataclass
class RetryPlan:
    should_retry: bool
    recompile: bool = False                 # True -> spec changed, run compile_scene again
    spec: SceneSpec | None = None           # the mutated spec (when recompile)
    add_negative: list = field(default_factory=list)  # ad-hoc terms to merge if not recompiling
    cfg_delta: float = 0.0
    note: str = ""


# Defect codes the QA stage can emit. Kept as data so the QA prompt and this policy agree.
DEFECT_DUPLICATE = "duplicate"
DEFECT_MULTIPLE = "multiple_people"
DEFECT_BROKEN_LIMB = "broken_limb"
DEFECT_FEET_GLITCH = "feet_glitch"
DEFECT_NOT_REAR = "not_rear"
DEFECT_BACKWARDS_HEAD = "backwards_head"


def plan_retry(spec: SceneSpec, verdict: dict, *, attempt: int, max_attempts: int) -> RetryPlan:
    """Given the QA verdict for the just-rendered image, decide the next move.

    verdict: {"ok": bool, "defect": str}. A passing verdict, or an exhausted budget,
    returns should_retry=False (the caller then either ships the pass or withholds/marks
    the best-effort frame — a policy choice left to the caller, but it is TOLD which).
    """
    if verdict.get("ok"):
        return RetryPlan(should_retry=False, note="passed")
    if attempt >= max_attempts:
        return RetryPlan(should_retry=False, note="budget-exhausted")

    defect = (verdict.get("defect") or "").strip().lower()

    if defect == DEFECT_NOT_REAR:
        # Front-facing render on a rear scene: escalate the rear emphasis so the next
        # compile leans harder on the behind-camera anchor.
        return RetryPlan(True, recompile=True, spec=spec.with_escalation("rear_boost"),
                         note="escalate rear emphasis")

    if defect == DEFECT_FEET_GLITCH:
        # Force the pose-gated feet negative on regardless of how the pose was tagged.
        return RetryPlan(True, recompile=True, spec=spec.with_escalation("feet_fix"),
                         note="force feet negative")

    if defect in (DEFECT_DUPLICATE, DEFECT_MULTIPLE):
        # The two-of-her merge is latent-size driven; a small cfg bump + re-roll helps
        # without recompiling. (Dims already sit near 1MP by construction.)
        return RetryPlan(True, add_negative=["duplicate person", "second body"],
                         cfg_delta=0.3, note="tighten duplicate suppression")

    if defect == DEFECT_BROKEN_LIMB:
        return RetryPlan(True, recompile=True, spec=spec.with_escalation("clean_limbs"),
                         note="raise steps for extremities")

    if defect == DEFECT_BACKWARDS_HEAD:
        return RetryPlan(True, add_negative=["impossible neck rotation", "head turned backwards"],
                         note="suppress owl-neck")

    # Unknown / generic defect: a plain re-roll (fresh seed) is still worth one attempt.
    return RetryPlan(True, note="plain re-roll")
