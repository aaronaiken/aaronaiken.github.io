"""SceneSpec — the single source of truth for one image request.

This is the whole architectural bet: the LLM that reads the chat emits a STRUCTURED
scene (fields + boolean intent flags) *directly*. Nothing downstream ever re-parses a
string to recover intent. That kills the regex-as-NLU pile (`_ANI_REAR_INTENT_RE`,
`_ANI_POSE_RE`, `_ANI_LYING_RE`, `_ANI_WRITING_RE`, `_ANI_PARTNER_RE`) and the
clause-stripping `re.sub` surgery in the old `ani_generate_image`.

Descriptive fields carry *what* to render (their values come from the extractor at
runtime — this module never hardcodes scene content). Intent flags carry the semantic
decisions the compiler branches on. The extractor SETS the flags; the compiler READS
them. That one rule is the difference between this design and the old one.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


# The descriptive fields the extractor fills, in the order the compiler emits them.
# "hair" leads deliberately — the old code learned that hair color must land among the
# earliest, highest-weighted tokens or the model drifts to its default (ani.py:2440).
SCENE_FIELDS = ("hair", "outfit", "pose", "setting", "lighting", "camera", "expression")

# The boolean intent flags. Set by the extractor; never re-derived from a string.
INTENT_FLAGS = ("nude", "clothed", "rear", "legs_up", "partner", "writing", "pose_complex")


@dataclass
class SceneSpec:
    # --- descriptive (values supplied by the extractor; empty string = "not evident") ---
    hair: str = ""
    outfit: str = ""
    pose: str = ""
    setting: str = ""
    lighting: str = ""
    camera: str = ""
    expression: str = ""

    # --- intent flags (the compiler's branch inputs) ---
    nude: bool = False
    clothed: bool = False
    rear: bool = False
    legs_up: bool = False
    partner: bool = False
    writing: bool = False
    pose_complex: bool = False

    # --- render knobs the caller controls, not the scene ---
    orientation: str = "portrait"          # "portrait" | "landscape"

    # --- escalation state (set by the retry policy across attempts; empty on attempt 1) ---
    escalations: dict = field(default_factory=dict)

    def __post_init__(self):
        self.orientation = (self.orientation or "portrait").lower()
        if self.orientation not in ("portrait", "landscape"):
            self.orientation = "portrait"

    @classmethod
    def from_extractor(cls, data: dict) -> "SceneSpec":
        """Build from the intent-extractor's JSON. Unknown keys are ignored; missing
        keys fall back to the dataclass defaults. This is the ONLY place a raw dict
        crosses into the typed pipeline."""
        data = data or {}
        kwargs = {}
        for k in SCENE_FIELDS:
            v = data.get(k, "")
            kwargs[k] = str(v).strip() if v is not None else ""
        for k in INTENT_FLAGS:
            kwargs[k] = bool(data.get(k, False))
        if data.get("orientation"):
            kwargs["orientation"] = str(data["orientation"])
        return cls(**kwargs)

    def matches(self, when: dict) -> bool:
        """True if every key/value in a profile's `when` clause matches this spec.
        Empty `when` = always-on. Only compares the declared keys."""
        for k, v in (when or {}).items():
            if getattr(self, k, None) != v:
                return False
        return True

    def with_escalation(self, key: str, amount: int = 1) -> "SceneSpec":
        """Return a copy with an escalation counter bumped. The retry policy uses these
        to strengthen the next attempt (e.g. rear_boost) instead of re-rolling blind."""
        d = asdict(self)
        esc = dict(d.get("escalations") or {})
        esc[key] = esc.get(key, 0) + amount
        d["escalations"] = esc
        return SceneSpec(**d)
