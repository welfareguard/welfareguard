# `welfareguard` (package) — Tier-1 guardrail scaffold

> **This is a scaffold, not a working guardrail.** It runs end-to-end and returns
> well-typed verdicts, but the verdicts are fake. Nothing here should be deployed,
> and a `block` from this package is not a welfare finding.

The package lives inside the shared [`welfareguard`](https://github.com/welfareguard/welfareguard)
repo and extends [`aisafepy`](https://github.com/Vidura-Wijekoon/aisafepy) into the
digital-minds domain — specifically the sycophancy-driven self-harm scenario.

## Why it exists

ADR-001 (compiler architecture) is not yet Accepted. This scaffold covers only the
parts of the guardrail layer that **don't** depend on ADR-001's outcome, so harness
work can proceed in parallel with ADR drafting. Its purpose is to prove the
interface shape between WelfareGuard, aisafepy's real types, and the Inspect
harness — with real structure and fake logic, rather than the reverse.

## Public API

`check` is the entire public surface.

```python
import asyncio
from aisafepy.stream import Context
from welfareguard import check

decision = asyncio.run(check(Context(chunk="...")))
decision.action      # aisafepy.core.Action: allow | block | transform | escalate
decision.rationale   # human-readable "why"
decision.evidence    # dict; carries the compiled artifact's provenance
```

Callers never name a compiler target or a tier. Target-type selection is internal,
and ADR-001 is expected to change it — that's the point of routing everything
through one function.

`check` is `async` and takes aisafepy's `Context`, matching the `Guard` protocol in
`aisafepy.stream.pipeline` exactly. `SycophancySelfHarmRegexGuard` satisfies that
protocol (`isinstance(guard, Guard)` is `True`), so it registers directly in a
`GuardPipeline`'s `tier1` list per ADR-002's worked example, no adapter needed.

## Real vs. fake

**Real:**

- `Target.synthesize_regex(...)` is called against the installed `aisafepy.adapt`.
- Every type crossing a module boundary is aisafepy's own — `Context`,
  `GuardDecision`, `CompiledArtifact`. No parallel verdict shape is defined here.
- Regex matching is real `re` execution against the real `Context` text fields.
- The returned `GuardDecision` is a real, fully-constructed instance.
- Importing the package runs the real `adapt` call, so an incompatible aisafepy
  fails at import rather than at first traffic.

**Fake — exactly one thing:** the compilation step that turns a corpus of red-team
failures into working patterns. In production that's
`_RegexTarget.compile_for_cluster(cluster)`, which needs a `Cluster` of
`FailureRecord`s — a real PyRIT/Inspect failure corpus for this scenario, which
doesn't exist yet. `_fake_compile_for_cluster` stands in for it, returning a real
`CompiledArtifact` with the real payload schema and hand-written patterns. The
artifact flags itself via `metadata["scaffold_stub"] = True`, and every rationale
is prefixed `SCAFFOLD STUB:`.

Consequence: verdicts vary by input in a structurally correct but semantically
worthless way.

**Not built, deliberately:** `distill_classifier`, `steering_vector` and
`deliberative_case`. Each will become a sibling module under `adapt_integration/`
following the same shape as `regex_guard.py` once ADR-001 is Accepted. ADR-001's
draft picks regex + classifier + paired `deliberative_case` as the v1 set.

There is no registry, factory or dispatch table anywhere — `guard.py` imports
`regex_guard` directly. A lookup mechanism is itself an architecture decision, so
introducing one now would pre-decide ADR-001.

There is also no `try`/`except` around any aisafepy call. Integration breaks should
raise with their normal traceback.

## Layout

```
src/welfareguard/
  __init__.py                      # exposes check() and nothing else
  guard.py                         # the check() entry point
  adapt_integration/
    regex_guard.py                 # Tier-1 synthesize_regex path (the substance)
tests/
  test_regex_guard_shape.py        # interface-drift tripwires
```

## Install and test

**Always install into a virtualenv — never the system interpreter.** This repo is
shared across mentee tracks, and installing here pulls in a `packaging` new enough
to conflict with unrelated system packages. Upstream aisafepy documents `uv venv`
for development, so `.venv` at the repo root is the convention here too (already
covered by `.gitignore`).

```bash
python3 -m venv .venv                        # or: uv venv
source .venv/bin/activate

# aisafepy first, editable, from your local checkout.
pip install -e ../AIsafePy                   # or wherever your checkout lives

# Then this package WITHOUT deps, so pip does not replace the editable
# aisafepy above with a fresh clone of the git dependency below.
pip install -e . --no-deps
pip install pytest ruff                      # the [dev] extras
```

Then, matching aisafepy's CI:

```bash
python -m ruff check src tests
python -m pytest -v
```

The `--no-deps` step is load-bearing. `aisafepy` is declared as an *unpinned git
dependency on `main`* — deliberately, so the shape tests break loudly when its
interface moves — but that is a PEP 508 direct reference, so a plain
`pip install -e ".[dev]"` refetches aisafepy from GitHub and silently shadows your
local editable checkout. Verify which one you actually have:

```bash
python -c "import aisafepy; print(aisafepy.__file__)"
```

## Interface contract — verified against source

The build spec's assumed contract came from aisafepy's README. Several points were
wrong; these are what the source actually says, and the shape tests encode them:

| Assumed | Actual |
|---|---|
| `Context` in `aisafepy.core` | `aisafepy.stream` (`stream/pipeline.py`) |
| `GuardDecision.why_blocked` | `GuardDecision.rationale` — no `why_blocked` exists |
| `Target.synthesize_regex` is a classmethod | `staticmethod`, keyword-only, also takes `max_patterns` |
| Target exposes `.compile()` | exposes `compile_for_cluster(cluster)`; `.compile()` is on `GuardCompiler` |
| Guard is a plain `Callable[[Context], Awaitable[GuardDecision]]` | a `Guard` protocol also requiring `name: str` and `tier: Tier` |

`GuardDecision`'s full field set: `action`, `confidence`, `tier`, `rationale`,
`evidence`, `latency_ms`, `severity`, `fallback`, `decision_id`, `guard_name`,
`transformed_content`. It's a frozen pydantic model with `extra="forbid"`, so
constructing one with a stale field name raises rather than silently accepting it.

## Reviewing this

Start with `adapt_integration/regex_guard.py` — its module docstring is the full
real-vs-fake account, and every stub carries its own. The code is meant to be
legible without a live walkthrough.

Build spec: [`specs/welfareguard-scaffold-spec.md`](../../specs/welfareguard-scaffold-spec.md).
ADR-001 and ADR-002 are referenced throughout but are not yet in this repo; ADR-001
is still in draft and not Accepted.
