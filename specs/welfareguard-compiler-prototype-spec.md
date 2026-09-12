# WelfareGuard Compiler Prototype — Build Spec

Component: compiler prototype for the WelfareGuard guardrail layer (Guardrails Engineer track).
Target consumer: Claude Code, with local read/write access to the `welfareguard` repo and an
editable install of `aisafepy` in the repo's `.venv`.

Predecessor: `welfareguard-scaffold-spec.md` (the interface-first scaffold, now built and merged
via PR). This spec builds the next layer: real compilation logic behind a new compile-time entry
point.

---

## 1. Masterplan (context + decisions)

**What this is.** The Week 2 compiler prototype. The scaffold proved the *interface shape*; this
proves the *compile path* — taking a `Cluster` of `FailureRecord`s and producing a deployable
guard artifact, against the digital minds scenario.

**What changed since the scaffold.** Three things, all verified against the built code rather than
assumed:

1. `check()` is confirmed runtime-facing only — `async def check(ctx: Context) -> GuardDecision`,
   returning `aisafepy.core.decisions.GuardDecision` exactly (not a subclass, not a wrapper).
   No compile-time types are imported into `guard.py`.
2. `guard.py` currently instantiates `_TIER1_GUARD = SycophancySelfHarmRegexGuard()` as a
   **module-level import side effect**, which really does invoke `Target.synthesize_regex(...)`
   at import time. This was deliberate (fail-fast on an incompatible aisafepy), but it means
   compilation is currently triggered implicitly by the runtime path.
3. ADR-001 has landed. Its scope is regex + classifier paired with `deliberative_case`, with the
   binding constraint that `deliberative_case` **must never ship alone**.

**Scope note.** Build for ADR-001's full original scope. One scenario only — the digital minds
sycophancy scenario — not two. (The Week 2 task list says "2 sample scenarios"; the digital minds
scenario was explicitly prioritized for this sprint.)

**Data provenance.** Richard is a pure *consumer* of `FailureRecord` clusters. Vidura supplies
them (absorbing the Evals role). Do **not** author synthetic scenario data as a substitute — the
existing scaffold fake-cluster pattern is the stand-in until Vidura's real cluster arrives.

**Locked decisions (do not relitigate — each was deliberately chosen in a design session):**

| Decision | Choice | Why |
|---|---|---|
| Compiler output shape | Paired `CompiledGuardSet { enforcement_artifact, deliberative_case }` | ADR-001's "never ship alone" constraint becomes structurally unrepresentable-if-violated, rather than relying on caller discipline |
| `deliberative_case` field | **Mandatory, never `None`** — holds a `SCAFFOLD STUB:` value for now | An optional field lets "ships alone" happen in practice, which is exactly what the pairing decision was meant to prevent |
| Compile input during build | The scaffold's existing fake-cluster pattern | Already honours real `min_precision`/`max_patterns` gating; swapping in Vidura's real cluster later is a data substitution, not a rewrite |
| Thresholds | Keep scaffold placeholder values; do **not** tune | Calibration is empirical and needs real failure data plus the `promote()` canary process. Guessing now would be a guess dressed as a decision |
| Below-threshold behaviour | Loud, never silent | A silent `None` return against a real cluster would make a "working prototype" demo misleading |
| `check()` | **Unchanged** in signature and return type | It is the runtime/inference entry point. Compilation is a different lifecycle with a different audience |
| New entry point | `compile()` — compile-time, returns `CompiledGuardSet` | Separate audience (operators/CI) from `check()`'s request path |
| `_TIER1_GUARD` eager compile | **Retained, demoted** to a lightweight sanity check only | Keeps the fail-fast-on-broken-aisafepy property, decoupled from producing the real artifact |
| Artifact lifecycle | Compiled **once**, cached, reused across all `check()` calls | Nothing changes between requests; `promote()`'s canary framing already implies deploy-and-reuse |
| Compile failure | **Fatal** — process does not come up serving traffic | Falling back to a stub artifact in production is the degraded-silently failure mode ADR-001's pairing constraint exists to prevent |
| Failure timing | Fatal at an explicit `initialize()`, **not at import** | Import-time fatal semantics break test collection, static analysis, IDEs, and `python -c "import x"` sanity checks for reasons unrelated to the guard |
| Cluster input | `initialize(cluster: Cluster)` takes it as a **parameter** | Vidura's handoff format is not yet known. Keeping loading outside the startup lifecycle means one small adapter function later, not a lifecycle change |

**Known spec deviation, deliberate:** the scaffold spec's locked table says *"Public API | Single
entry point: `check()`"*. This spec adds a second entry point (`compile()`). That row was written
about request-path callers before a compiler prototype was planned; a compile-time API serves a
different audience. Richard is flagging this to Vidura in chat. It does **not** need to route
through ADR-001, whose subject is which Target types are in v1 scope — not public API surface.

**Explicitly out of scope for this pass:** threshold tuning; `steering_vector`; the real
`deliberative_case` implementation (stub only); the cluster loader/parser (format unknown — see
Open Questions); registry/dispatch patterns; CI config; modifying `aisafepy` itself.

---

## 2. Interface contract

**Verification status — read this carefully, it differs from the scaffold spec.**

Section 2 of the scaffold spec was hedged: its types were inferred from aisafepy's README and
Claude Code was told to verify everything before coding. This time, the items under **Verified**
below were confirmed empirically against the built code and the installed package. Treat them as
fact. The items under **Unverified** carry the old rule: **the real source wins** — verify before
use, and update this contract rather than silently coding around a mismatch.

### Verified (confirmed empirically — do not re-derive)

```python
# src/welfareguard/guard.py:42
async def check(ctx: Context) -> GuardDecision: ...
#   ctx    -> aisafepy.stream.pipeline.Context
#   return -> aisafepy.core.decisions.GuardDecision   (base class exactly, NOT the
#             Tripwire(GuardDecision) subclass that also lives in core/decisions.py)
#   inspect.iscoroutinefunction(check) is True
#   `from __future__ import annotations` is active (line 27) — annotations are strings at
#   runtime; resolve via typing.get_type_hints() if you need the real objects.

# guard.py's complete import list — three lines, no compile-time types:
from aisafepy.core import GuardDecision                                 # 29
from aisafepy.stream import Context                                     # 30
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard  # 32

# guard.py:39 — runs at module import:
_TIER1_GUARD = SycophancySelfHarmRegexGuard()
#   Importing welfareguard.guard — with no check() call — really does invoke
#   Target.synthesize_regex(min_precision=0.99, max_patterns=20) exactly once.
#   guard._TIER1_GUARD.target   is a real _RegexTarget
#   guard._TIER1_GUARD.artifact is a real CompiledArtifact
#   All compile-time imports live one level down, at regex_guard.py:75.
```

### Unverified — confirm against real source before use

```python
# Cluster / FailureRecord: exact constructors, field names, and the shape a Cluster must have
#   to be accepted by _RegexTarget.compile_for_cluster. Locate in aisafepy and confirm.
# CompiledArtifact: full constructor signature and payload schema (the scaffold's
#   _fake_compile_for_cluster already constructs real ones — read that first, it is the
#   closest thing to a worked example in-repo).
# The real (non-faked) compile_for_cluster path: what it needs, what it raises, and what it
#   returns below the minimum-record threshold (the scaffold stub returns None under 4
#   violating records — confirm whether that mirrors the real target's behaviour).
# deliberative_case: whether aisafepy exposes a type for it at all, or whether WelfareGuard
#   must define the stub's shape locally. Report back before inventing one.
```

### New surface this spec introduces

```python
# Shape is illustrative, not prescriptive — confirm against real aisafepy types first.

class CompiledGuardSet:
    enforcement_artifact: CompiledArtifact   # regex (v1) or classifier
    deliberative_case: <type TBD>            # MANDATORY, never None; SCAFFOLD STUB for now

def compile(cluster: Cluster) -> CompiledGuardSet: ...
def initialize(cluster: Cluster) -> None: ...
    # calls compile() once, caches the result for check() to read.
    # Raises fatally on compile failure or below-threshold cluster. Never falls back to a stub.
```

---

## 3. Implementation strategy

**Build order — strictly incremental. Verify each step before the next. Do not one-shot.**

1. **Read before writing.** Confirm the Unverified block above against real source: `Cluster`,
   `FailureRecord`, `CompiledArtifact`'s real constructor, the real `compile_for_cluster` path,
   and whether aisafepy has any `deliberative_case` type. **Stop and report back** before writing
   code if anything materially differs from this contract — especially if `deliberative_case` has
   no aisafepy type, since that changes what the stub must be.

2. **Define `CompiledGuardSet`.** Its only job is making "enforcement artifact without a
   deliberative case" unconstructable. Enforce the mandatory field at construction, not by
   convention or docstring. Confirm you cannot build an invalid one before moving on.

3. **Write the real `compile()`.** Takes a `Cluster`, runs the real (non-faked) compile path,
   returns a `CompiledGuardSet`. The `deliberative_case` slot gets a stub value carrying the
   `SCAFFOLD STUB:` prefix and `metadata["scaffold_stub"] = True`, matching the existing
   convention in `_fake_compile_for_cluster`. Below-threshold or failed compilation must surface
   loudly — raise, don't return `None`, and don't log-and-continue.

4. **Write `initialize(cluster)`.** Calls `compile()` once, caches the result. Fatal on failure.
   Import of any WelfareGuard module must **not** trigger it.

5. **Demote `_TIER1_GUARD`.** It keeps running at import as a lightweight sanity check that
   aisafepy is importable and the interface hasn't drifted — but it must no longer be the source
   of the artifact `check()` uses. Preserve the fail-fast-on-broken-aisafepy property; do not
   preserve the it-produces-the-real-artifact behaviour.

6. **Rewire `check()` to read the cached artifact** from `initialize()` instead of `_TIER1_GUARD`.
   **Its signature and return type must not change** — `async def check(ctx: Context) ->
   GuardDecision`, returning the base `GuardDecision` exactly. The existing 8 shape tests are the
   tripwire for this; they must still pass untouched.

7. **Tests.** Extend the existing shape-assertion style, don't replace it. At minimum:
   `CompiledGuardSet` cannot be constructed without a `deliberative_case`; `check()`'s signature
   is unchanged; importing any module triggers no real compilation; `initialize()` raises (not
   returns) on a below-threshold cluster.

8. **Docs last.** Update `src/welfareguard/README.md`: the compile-vs-runtime entry point split,
   the explicit `initialize()` startup requirement, and the deliberate spec deviation on "single
   entry point" with its rationale.

**Cross-cutting rules (carried forward from the scaffold spec, still in force):**

- No try/except around calls into real aisafepy. Let failures raise with their normal traceback.
- No registry/factory/dispatch. Direct imports only.
- Every stub documents what is fake and why, legibly to Vidura without live narration.
- Never modify `aisafepy` itself. WelfareGuard only ever imports it.
- **Use the repo `.venv`, never the system interpreter.** (See the README's install section —
  a system-wide install previously caused a `packaging` version conflict.) Note `pip install -e
  ".[dev]"` is wrong here: it refetches aisafepy from the git URL and silently shadows the local
  editable checkout. Use `--no-deps` plus explicit dev tools.

---

## 4. Setup prompt

> I'm building the compiler prototype for the WelfareGuard guardrail layer, in the shared
> `welfareguard` repo. The interface-first scaffold is already built and merged; this is the next
> layer — real compilation logic behind a new compile-time entry point, separate from the existing
> runtime `check()`.
>
> Follow the attached spec exactly, in the build order in Section 3. Do not generate all files at
> once.
>
> Start with step 1: Section 2 has a **Verified** block (confirmed empirically — treat as fact,
> don't re-derive) and an **Unverified** block (confirm against real aisafepy source first). Read
> and confirm the Unverified items, then report back what you find before writing any code.
> Flag especially whether aisafepy exposes a `deliberative_case` type at all, since that changes
> what the stub has to be.
>
> Work in the repo `.venv`, not the system interpreter.

---

## Open questions (not blocking this build)

- **Cluster handoff format from Vidura** — unknown. Deliberately kept outside the startup
  lifecycle: `initialize(cluster: Cluster)` takes the object, so whatever format arrives becomes
  one small adapter function later rather than a change to anything in this spec.
- **ADR-001 scope may narrow** at the next meeting, given the Evals role change. This spec builds
  for the full original scope; a narrowing would subtract work, not invalidate what's here.
- **Stale line in the scaffold spec**: its Section 1 table says Target-type selection logic lives
  *inside* `check()` once ADR-001 lands. Now that compilation is confirmed separate from the
  runtime path, that line is misleading. Worth correcting in the scaffold spec doc so the next
  reader isn't misled.
