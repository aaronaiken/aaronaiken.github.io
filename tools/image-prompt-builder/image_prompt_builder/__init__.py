"""image_prompt_builder — a standalone, testable chat→image prompt pipeline.

    ChatContext
       -> SceneSpec           (structured intent, set by the extractor)
       -> compile_scene()     (pure: SceneSpec + profiles -> RenderRequest)
       -> render              (thin backend adapter — not in this package)
       -> QA verdict
       -> plan_retry()        (pure: verdict -> next attempt)

The two pure stages (compile + retry) live here and carry the whole design. Extraction
and rendering are I/O adapters the host app supplies. Knowledge lives in profiles.json.
"""

from .scene_spec import SceneSpec, SCENE_FIELDS, INTENT_FLAGS
from .render_request import RenderRequest
from .profiles import load_config, matching_profiles, resolve_param
from .compiler import compile_scene
from .retry import plan_retry, RetryPlan
from .extractor import (
    build_extractor_messages, parse_extractor_json, default_scene,
    extract_scene, EXTRACTOR_SCHEMA,
)

__all__ = [
    "SceneSpec", "SCENE_FIELDS", "INTENT_FLAGS",
    "RenderRequest",
    "load_config", "matching_profiles", "resolve_param",
    "compile_scene",
    "plan_retry", "RetryPlan",
    "build_extractor_messages", "parse_extractor_json", "default_scene",
    "extract_scene", "EXTRACTOR_SCHEMA",
]
