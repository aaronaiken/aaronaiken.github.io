"""RenderRequest — the compiler's output contract and the renderer's input.

A plain, fully-resolved description of one generation: the positive prompt, the negative
prompt, and the engine dials. No scene semantics survive to this layer — by the time you
hold a RenderRequest, every decision has been made. The renderer is a dumb adapter that
POSTs these fields to a backend.

`meta` is diagnostic only (which profiles fired, escalation state). It never reaches the
backend, but it's what you log so you can later answer "pass-rate by scene tag" instead of
doing comment-archaeology.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RenderRequest:
    positive: str
    negative: str
    cfg: float
    steps: int
    width: int
    height: int

    # Diagnostics: applied profile ids, escalation counters, etc. For logging only.
    meta: dict = field(default_factory=dict)

    def backend_payload(self, model: str, *, safe_mode: bool = False) -> dict:
        """The subset a Venice-style backend actually needs. Kept here so the renderer
        stays a one-liner and the field mapping lives with the contract."""
        return {
            "model": model,
            "prompt": self.positive[:7500],
            "negative_prompt": self.negative,
            "cfg_scale": self.cfg,
            "steps": self.steps,
            "width": self.width,
            "height": self.height,
            "safe_mode": safe_mode,
            "format": "jpeg",
            "return_binary": True,
        }
