"""Profile loading + resolution helpers.

Profiles are the knowledge layer: each is a data row declaring, for a given scene-tag
combination, what to add to the prompt/negative and which engine dials to override.
Loading is the only I/O in the builder; the compiler itself stays pure.
"""

from __future__ import annotations

import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "profiles.json")


def _as_term_list(v):
    """Normalize a `negative` value to a list of terms. Accepts either a JSON array OR a
    single comma-separated string — so an operator can paste an `ani.py` constant (which is
    one comma-joined string) straight into a row without splitting it by hand."""
    if isinstance(v, str):
        return [t.strip() for t in v.split(",") if t.strip()]
    return list(v or [])


def load_config(path: str = _DEFAULT_PATH) -> dict:
    """Read and lightly validate the profile config. Raises on a malformed file — a
    broken knowledge base should fail loud at startup, not silently render garbage.
    Normalizes every `negative` (base + profiles) to a term list."""
    with open(path, "r") as f:
        cfg = json.load(f)
    for key in ("engine_defaults", "base", "profiles"):
        if key not in cfg:
            raise ValueError(f"profiles config missing required section: {key!r}")
    cfg["base"]["negative"] = _as_term_list(cfg["base"].get("negative"))
    for p in cfg["profiles"]:
        if "negative" in p:
            p["negative"] = _as_term_list(p["negative"])
    return cfg


def matching_profiles(spec, profiles: list) -> list:
    """Every profile whose `when` clause matches the spec, ordered by ascending priority
    so that higher-priority rows are applied LAST (last-wins for scalar overrides)."""
    hits = [p for p in profiles if spec.matches(p.get("when", {}))]
    return sorted(hits, key=lambda p: p.get("priority", 0))


def resolve_param(param: str, applied: list, defaults: dict, default_key: str):
    """Resolve one engine dial. The highest-priority applied profile that DECLARES the
    param wins; otherwise fall back to the named default. A declared value may be a
    number or a string naming an entry in engine_defaults (e.g. "cfg_clothed").

    Independent per-param resolution is deliberate: a clothed complex-pose takes its cfg
    from `clothed` (higher priority) but its steps from `complex_pose` (the only declarer),
    exactly mirroring the old code's split between the extra_neg cfg and the pose steps.
    """
    value = None
    for p in applied:               # ascending priority → last declarer wins
        if param in p:
            value = p[param]
    if value is None:
        value = defaults.get(default_key)
    if isinstance(value, str):      # indirection into engine_defaults
        value = defaults.get(value, value)
    return value
