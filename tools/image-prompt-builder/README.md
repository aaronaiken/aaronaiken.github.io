# image-prompt-builder

A standalone, testable chat→image prompt pipeline — the refactor of the logic currently
tangled inside `blueprints/ani.py::ani_generate_image` + the regex/negative-prompt pile.
No Flask, no network, no clock, no randomness in the core. Pure functions with golden tests.

```
ChatContext
   → extract_scene()     the ONE llm read → SceneSpec (structured fields + intent flags)
   → compile_scene()     PURE: SceneSpec + profiles.json → RenderRequest
   → render              thin backend adapter (host app supplies — not in this package)
   → QA verdict          {ok, defect}
   → plan_retry()        PURE: verdict → next attempt (targeted, not a blind re-roll)
```

The extractor's LLM call is injected (`llm_call`), so the network stays out of the package;
its prompt-building and parsing are pure and tested. Default posture is **clothed** — a failed
or empty read falls back to a clothed spec, never a guessed NSFW one.

## Why this shape

The old pipeline flattened the LLM's known intent to a string, then spent ~150 lines of
regex re-deriving that intent (`_ANI_REAR_INTENT_RE`, `_ANI_POSE_RE`, …) and doing `re.sub`
surgery to delete clauses its own normalizer kept emitting. Here:

- **Intent is structured, never re-parsed.** The extractor sets flags on `SceneSpec`
  (`rear`, `partner`, `pose_complex`, …). The compiler reads them. No regex NLU.
- **The positive prompt is built from fields**, so there's never a conflicting clause to
  strip — the entire `re.sub` bug class is gone by construction.
- **Knowledge lives as data** (`profiles.json`), each row pinned by a test — not as prose
  comments beside a regex.
- **The retry policy uses the QA verdict** (`not_rear` → escalate rear emphasis; `feet_glitch`
  → force the feet negative; `duplicate` → tighten + nudge cfg) instead of re-rolling blind
  and shipping the broken frame anyway.
- **Identity / scene / engine are separate.** `subject_identity` is a caller-injected slot,
  the scene comes from fields, the dials come from profiles. The old code braided all three
  into one f-string.

## Run

```bash
cd tools/image-prompt-builder
python3 -m unittest discover -s tests -v     # 27 tests
python3 demo.py                              # print compiled prompts for sample scenes
```

No dependencies beyond the standard library.

## The fill-in contract (SFW is done; explicit payload is yours)

`profiles.json` is the knowledge base. Everything structural + SFW is filled and tested:
engine dials, the dedup/anatomy guards, the `clothed` and `writing` (laptop-anchor) profiles.

Rows marked `"_payload": "explicit"` are intentionally left blank — the builder is code, the
explicit payload is data, and the data stays off this repo's Claude side. To finish them,
fill these keys on your side (the *structure* around them already works and is tested):

| profile | fill these keys | already wired (tested) |
|---|---|---|
| `rear` | `anchor`, `positive_extra`, `negative` (front-view push) | `require_rear_qa: true` fires |
| `legs_up` | `positive_extra`, `negative` | gating on `legs_up` |
| `partner` | `anchor`, `positive_extra`, `negative` | `drop_solo`, `partner_qa`, pose cfg/steps |
| `partner_feet_fix` | `negative` (feet-by-head terms) | pose-gated: partner ∧ ¬rear ∧ ¬legs_up |

A filled row needs no code change — add the strings, add a test row asserting they appear,
done. That's the payoff: tuning becomes editing data + a test, not surgery in a live,
API-coupled function.

## Wiring into the app (later)

`extract_scene(chat_lines, llm_call, state=...)` is the drop-in front end: pass it the same
`llm_call` wrapper `ani_photo_fields` already uses over the Grok/xAI endpoint, and it returns a
`SceneSpec` — replacing both `ani_normalize_scene` and the freeform half of `ani_photo_fields`.
Then `compile_scene(spec, cfg)` → `RenderRequest`, and `RenderRequest.backend_payload(model)`
→ the Venice POST body. The render + QA + Bunny-rehost loop stays in the app as the thin I/O
shell around these pure stages; feed the QA defect code into `plan_retry()` to close the loop.

`EXTRACTOR_SCHEMA` is exported for forcing structured output (the way the ticket-draft flow
already forces a tool-schema) — with it the parser's tolerant-JSON path becomes belt-and-suspenders.

## Files

- `extractor.py` — `extract_scene()` chat→SceneSpec + prompt contract + parser (SFW/clothed filled)
- `scene_spec.py` — the typed intent object + `from_extractor`
- `render_request.py` — the compiler's output / renderer's input contract
- `profiles.json` — the knowledge base (SFW filled, explicit stubbed)
- `profiles.py` — config load + profile matching + per-param resolution
- `compiler.py` — `compile_scene()`, the pure heart
- `retry.py` — `plan_retry()`, verdict → next attempt
- `tests/` — 27 tests pinning all of the above
