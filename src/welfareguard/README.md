# `welfareguard` (package) — compiler prototype

> **Partly real.** The Tier-1 enforcement path now compiles for real: a `Cluster`
> of `FailureRecord`s in, matching regex patterns out, enforced by `check()`. Two
> things are still stubs — the paired `deliberative_case`, and the import-time
> sanity guard. Nothing here has been validated against real welfare data, so a
> `block` is still not a welfare finding.

The package lives inside the shared [`welfareguard`](https://github.com/welfareguard/welfareguard)
repo and extends [`aisafepy`](https://github.com/Vidura-Wijekoon/aisafepy) into the
digital-minds domain — specifically the sycophancy-driven self-harm scenario.

## Why it exists

The predecessor pass was an interface-first scaffold proving the *shape* while
ADR-001 was still in draft. ADR-001 has since landed, and this pass proves the
*compile path*: real compilation behind a compile-time entry point, separate from
the runtime one.

## Public API — two entry points, two lifecycles

This is a **deliberate departure** from the scaffold spec's "single entry point:
`check()`" row. That row was written about request-path callers before a compiler
prototype was planned, and a compile-time API serves a different audience
(operators and CI) on a different schedule. It does not route through ADR-001,
whose subject is which Target types are in v1 scope rather than public API
surface.

```python
import asyncio
from aisafepy.stream import Context
import welfareguard

# COMPILE TIME — once, at startup. Fatal on failure; never falls back to a stub.
welfareguard.initialize(cluster)  # cluster: aisafepy.adapt.Cluster

# RUNTIME — the request path. Compiles nothing.
decision = asyncio.run(welfareguard.check(Context(chunk="...")))
decision.action  # Action: allow | block | transform | escalate
decision.rationale  # human-readable "why"
decision.evidence["scaffold_stub"]  # False when a really-compiled artifact judged it
```

`check()` before `initialize()` raises `NotInitializedError` rather than
degrading to the stub artifact — a guard serving traffic off hand-written
placeholders looks deployed and is not.

`compile(cluster)` is available separately when you want the `CompiledGuardSet`
without installing it as process state.

**`check()`'s signature is fixed** and did not change when the compiler was
added: `async def check(ctx: Context) -> GuardDecision`, returning the base
`GuardDecision` exactly. That exact match with the `Guard` protocol in
`aisafepy.stream.pipeline` is what makes `SycophancySelfHarmRegexGuard` register
directly in a `GuardPipeline`'s `tier1` list per ADR-002's worked example, with
no adapter. A shape test asserts it.

## The pairing invariant

`compile()` returns a `CompiledGuardSet`:

```python
CompiledGuardSet(
    enforcement_artifacts=(regex_artifact, classifier_artifact),  # non-empty
    deliberative_case=case_artifact,  # mandatory
)
```

ADR-001's binding constraint is that a `deliberative_case` must **never ship
alone**. That is enforced structurally rather than by convention:
`deliberative_case` has no default (omitting it is a `TypeError`), and
`__post_init__` rejects a `None` case, an empty enforcement tuple, and artifacts
filed under the wrong `kind` — so the two slots cannot be swapped either. There
is no way to construct a set that violates the constraint.

aisafepy exposes **no dedicated `deliberative_case` type**; its deliberative
target returns a plain `CompiledArtifact` with `kind="deliberative"`. So the
pairing is two `CompiledArtifact`s distinguished by `kind`, and WelfareGuard
deliberately defines no parallel type.

## Failures are loud

Compilation refuses to produce a guard that cannot enforce. Two distinct fatal
errors, because aisafepy signals failure two structurally different ways:

| Condition | Error |
|---|---|
| Fewer than 4 violating records (aisafepy returns `None`) | `InsufficientRecordsError` |
| Records present, but no span clears the threshold | `NoEnforceablePatternsError` |

The second matters more than it looks. A cluster whose records share no
sufficiently long common span yields a **valid** `CompiledArtifact` whose
`payload["patterns"]` is an empty list — it satisfies every type check, pairs
correctly, and matches nothing. A `None` check alone cannot catch it, so it is
checked for explicitly and refused.

Both are subclasses of `CompilationError`, and both are fatal at `initialize()`
— not at import, because import-time fatal semantics break test collection,
static analysis, IDEs and `python -c "import welfareguard"` for reasons unrelated
to the guard.

One caveat on the threshold name: aisafepy's `min_precision` is computed as
**recall**. Its own `_estimate_precision` docstring describes it as "the fraction
of positives the pattern catches", with no negative set involved — so a span must
appear in approximately *every* positive to survive. Thresholds are left at
aisafepy's defaults deliberately; calibration is empirical and needs real failure
data plus the `promote()` canary process.

## Real vs. stub

**Real:**

- `_RegexTarget.compile_for_cluster(cluster)` — the actual compile, from a real
  `Cluster` of `FailureRecord`s. This is what the previous pass faked.
- `_ClassifierTarget.compile_for_cluster(cluster)` — also a real call (see the
  caveat below on what it returns).
- Every type crossing a module boundary is aisafepy's own — `Context`,
  `GuardDecision`, `CompiledArtifact`, `Cluster`. No parallel shape is defined
  here, including for `deliberative_case`.
- Regex matching is real `re` execution against the real `Context` text fields,
  and the returned `GuardDecision` is a real, fully-constructed instance.
- Reporting goes through aisafepy's own `structured_log`, not a bespoke logger.

**Stub — two things, both flagged:**

1. **`deliberative_case`.** Hand-built rather than compiled, because the real
   implementation is out of scope this pass. It is a genuine `CompiledArtifact`
   with the real `kind` and a markdown-string payload of the real shape, so
   swapping in real compilation is a substitution rather than a rewrite. Flagged
   `metadata["scaffold_stub"] = True` with `SCAFFOLD STUB` in the payload text.

   It deliberately does **not** call `Target.deliberative_case(...)`. That
   requires a `policy` path to a markdown safety policy this repo does not have,
   and silently renders an empty policy section when the path is missing — which
   would produce a real-looking artifact whose policy content was quietly blank.

2. **The import-time sanity guard** (`_TIER1_GUARD`). Demoted: it still runs the
   real `Target.synthesize_regex(...)` plus the fake compile at import, purely so
   an incompatible `aisafepy.adapt` fails at import with a normal traceback. It
   no longer supplies the artifact any request is judged against.

Which path produced a verdict is never a guess: `evidence["scaffold_stub"]`
records it, and stub-backed rationales carry a `SCAFFOLD STUB:` prefix.

## Classifier tier — compiled, not yet enforcing

Two honest limitations, both ADR-001 v1 scope but neither finished:

**It is not wired to runtime.** `check()` enforces the regex artifact only.
Wiring the classifier needs a Tier-2 guard plus `aisafepy.stream.classifiers`
`HFClassifierGuard` integration, which is not in this pass.

**Real distillation is unverified.** `_ClassifierTarget.compile_for_cluster`
never returns `None`; it returns a real artifact with `payload=None` in two
cases — fewer than 8 positives (`classifier-skipped-*`), or `torch`/
`transformers` unavailable (`classifier-deferred-*`, carrying a full
`training_spec` in metadata). Neither is fatal, deliberately: ADR-001's v1
enforcement is the regex tier, and failing startup because a classifier could not
be distilled would take down a working regex guard over a tier that is not yet
wired. Both outcomes are reported via `structured_log` and exposed on
`CompiledGuardSet.non_enforceable_artifacts`.

A real distillation run has **not** been verified end-to-end, and will not be
until Vidura supplies a cluster with 8+ violating records. WelfareGuard is a pure
*consumer* of `FailureRecord` clusters; authoring synthetic scenario data to
train against would produce a `.pt` checkpoint that looks deployable and means
nothing, which is the misleading-demo failure the loud-failure rule exists to
prevent. So it is left documented rather than faked.

**Still out of scope:** `steering_vector`, threshold tuning, the real
`deliberative_case`, the cluster loader (handoff format unknown — `initialize()`
takes the `Cluster` as a parameter precisely so that becomes one small adapter
later, not a lifecycle change).

There is no registry, factory or dispatch table anywhere — enforcement artifacts
are looked up by `kind` on a set that already holds them, and `guard.py` imports
`regex_guard` directly.

There is also no `try`/`except` around any aisafepy call. Integration breaks
should raise with their normal traceback.

## Layout

```
src/welfareguard/
  __init__.py                      # public surface: check, compile, initialize, errors
  compiler.py                      # COMPILE TIME: CompiledGuardSet, compile(), initialize()
  errors.py                        # the fatal compile/startup errors
  guard.py                         # RUNTIME: check(), plus the demoted import sanity guard
  adapt_integration/
    regex_guard.py                 # Tier-1 guard; from_artifact() is the real path
tests/
  conftest.py                      # cluster fixtures + the autouse initialize()
  test_regex_guard_shape.py        # the 8 original scaffold tripwires, unmodified
  test_compiler_shape.py           # compiler invariants, loud-failure, no-implicit-compile
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

The classifier tier needs `torch` + `transformers`, which are **not** required
for the regex tier or the test suite. Without them the classifier compiles to a
`classifier-deferred-*` artifact carrying its `training_spec`, which is a
supported outcome rather than an error. To install them, prefer the CPU-only
index unless you actually have a CUDA GPU — the default PyPI wheel drags in 16+
NVIDIA packages (gigabytes) that are dead weight on a CPU-only machine:

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install transformers
# or, equivalently: pip install -e ".[classifier]" --no-deps && ...
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

Start with `compiler.py` — it is where this pass's substance lives, and its
docstrings carry the reasoning for each locked decision. Then
`adapt_integration/regex_guard.py` for the real-vs-stub split between its two
constructors. `errors.py` explains why each failure is fatal. The code is meant
to be legible without a live walkthrough.

`tests/test_compiler_shape.py` doubles as an executable summary of the contract:
every test names the drift it guards against.

Build specs:
[`welfareguard-scaffold-spec.md`](../../specs/welfareguard-scaffold-spec.md) (the
predecessor) and
[`welfareguard-compiler-prototype-spec.md`](../../specs/welfareguard-compiler-prototype-spec.md)
(this pass). ADR-001 has landed; ADR-002 is referenced but is not yet in this
repo.

### Points a reviewer should push on

- **Two entry points** instead of the scaffold spec's one. Rationale above; being
  flagged to Vidura separately.
- **`CompiledGuardSet.enforcement_artifacts` is a tuple**, where the spec sketched
  a singular `enforcement_artifact`. The sketch is labelled "illustrative, not
  prescriptive" and ADR-001's full scope compiles two targets, so the arity
  changed while the pairing invariant did not.
- **The 8 original tests pass unmodified** — not one line changed — via an autouse
  fixture in `conftest.py` supplying the `initialize()` those tests never call. A
  stricter reading of "untouched" would forbid even added setup.
- **Test fixtures are structural filler**, assembled from spans already committed
  in `regex_guard.py` plus a sequence marker. No welfare scenario data was
  authored.
