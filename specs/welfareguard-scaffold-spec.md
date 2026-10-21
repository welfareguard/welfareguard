# WelfareGuard Guardrail Scaffold — Build Spec

Component: interface-first scaffold for the WelfareGuard guardrail layer (Guardrails Engineer track).
Target consumer: Claude Code, with local read access to the `aisafepy` repo and an editable install of it.

---

## 1. Masterplan (context + decisions)

**What this is.** A *scaffold*, not a working guardrail. It proves the interface shape between the
WelfareGuard package, aisafepy's real types, and the Inspect harness — before [ADR-001](../docs/adr/ADR-001-compiler-targets.md) (compiler
architecture) is Accepted. It should run end-to-end with fake verdict logic, not fake structure.

**Why it exists now, before [ADR-001](../docs/adr/ADR-001-compiler-targets.md) lands.** WelfareGuard's Week 1 pattern is to run ADR drafting and
harness work in parallel, deferring only genuinely architecture-sensitive decisions. This scaffold is
scoped to the parts that don't depend on [ADR-001](../docs/adr/ADR-001-compiler-targets.md)'s outcome.

**Repo context — do not create a new repo.** WelfareGuard is one shared repo (`welfareguard`), owned by
Vidura Wijekoon, that all three mentees (Evals, Guardrails, Research & Comms) contribute to via PRs into
`main`. This scaffold is built as a package *inside* that repo, not as its own standalone GitHub repo.
**Before starting**, confirm with the user whether the `welfareguard` repo already exists, or if this
scaffold should be prepared to be added once it does — do not assume and do not create one speculatively.

**Locked decisions (do not relitigate these — they were deliberately chosen):**

| Decision | Choice | Why |
|---|---|---|
| Scope | Interface shell, not real guardrail logic | [ADR-001](../docs/adr/ADR-001-compiler-targets.md) (architecture) not yet Accepted |
| Runnability | Smoke-testable — stubs return real, well-typed fake data | Prove the interface now, not just document it |
| Target types | Build **one**: `synthesize_regex` (Tier 1) | Simplest, least architecturally contested; matches [ADR-001](../docs/adr/ADR-001-compiler-targets.md) draft's chosen v1 set (regex + classifier + paired deliberative_case) **Corrected 2026-10-20:** this row originally implied that Target-type selection would live *inside* `check()` once ADR-001 landed. It does not. Compilation is a separate lifecycle (`compile()`/`initialize()`, run once at startup) and `check()` only consumes the cached artifact by `kind`; it selects and compiles nothing. The row is kept, not deleted, because it records what the scaffold was scoped to at the time. See `welfareguard-compiler-prototype-spec.md`. |
| Verdict type | Use aisafepy's real `GuardDecision` (from `aisafepy.core`), not a custom shape | It's the actual shared interface across `flow`, `stream`, and `adapt` — inventing a parallel shape would be redundant and wrong |
| Package location | Standalone package `welfareguard`, living inside the shared `welfareguard` repo | Matches PyPI end-goal; matches repo ownership above |
| Tests | Minimal shape-assertion tests only, not full coverage | Tripwire for accidental interface drift, not a full test suite yet |
| Harness wiring | Direct import, no registry/lookup pattern | A registry is itself an architecture decision ([ADR-001](../docs/adr/ADR-001-compiler-targets.md)'s territory); direct import stays neutral |
| aisafepy dependency | Import real types/interfaces (`Context`, `GuardDecision`, `Target`) where they exist; fake only the internal compile/execution logic | Deep-dive time was already spent learning `adapt`'s real shape — use it |
| Error handling | Let real aisafepy call failures raise/crash normally — no try/except wrapping | This is scaffold code meant to surface integration breaks loudly and early, not hide them |
| Docs | Every stub explicitly documents what's fake and why (Vidura-readable) | Vidura has [ADR-001](../docs/adr/ADR-001-compiler-targets.md) approval authority and a scheduled walkthrough; code should be self-explanatory without live narration |
| Public API | Single entry point: `check()` | Callers (harness, future users) never need to know which Target type is running underneath. **Superseded by the compiler prototype:** compilation turned out to be a separate lifecycle with a separate audience, so it lives behind its own `compile()`/`initialize()` entry point rather than inside `check()`. `check()` remains the sole *runtime* entry point and its signature is unchanged. See `welfareguard-compiler-prototype-spec.md`. **Accepted by the repo maintainer, 2026-10-20:** the second entry point stands. Rationale: different audience (operators and CI, not request-path callers) and different lifecycle (once at startup, not per request). It is not an ADR matter, since ADR-001's subject is which Target types are in v1 scope, not public API surface. |

**Explicitly out of scope for this pass:** `distill_classifier`, `steering_vector`, `deliberative_case`
stubs (note only, don't build); registry/lookup dispatch; retry/wrapping logic around aisafepy errors;
full test coverage; CI config; anything that duplicates or modifies aisafepy itself (per the project's
boundary rule — WelfareGuard only ever imports aisafepy, never patches it in-repo).

---

## 2. Interface contract

**Corrected 2026-10-20 against installed source.** The contract originally written here was inferred
from aisafepy's public README, and this spec's own rule applied: *the real source wins*. Verification
against the installed package found it wrong in five places, and the existing code and shape tests
already encode the verified contract below. The original is kept for the record in the table at the
end of this section.

**Verified contract (read from `aisafepy` source, not its README):**

```python
# aisafepy.stream  (stream/pipeline.py) — NOT aisafepy.core
from aisafepy.stream import Context, Guard, GuardPipeline, Tier

@dataclass
class Context:
    chunk: str | None = None
    buffer: str = ""
    prompt: str | None = None
    hidden_states: Any | None = None
    role: Literal["user", "assistant", "tool"] = "assistant"
    metadata: dict[str, Any] = field(default_factory=dict)

# Guard is a runtime-checkable Protocol, NOT a bare Callable[[Context], Awaitable[GuardDecision]].
# It requires two attributes alongside the async call:
class Guard(Protocol):
    name: str
    tier: Tier                                   # Literal[1, 2, 3]
    async def __call__(self, ctx: Context) -> GuardDecision: ...

# aisafepy.core  (core/decisions.py)
from aisafepy.core import Action, GuardDecision

class GuardDecision(BaseModel):                  # frozen pydantic model, extra="forbid"
    action: Action                               # allow | block | transform | escalate
    confidence: float                            # 0.0..1.0
    tier: int                                    # >= 0
    rationale: str                               # the human-readable "why" — there is NO why_blocked
    evidence: dict[str, Any]
    latency_ms: float
    severity: Severity                           # info | low | medium | high | critical
    fallback: str | None
    decision_id: str
    guard_name: str | None
    transformed_content: str | None
# Ergonomic constructors: GuardDecision.allow(...), .block(...), .transform(...), .escalate(...)
# Predicates: .is_terminal (block or escalate), .is_blocked

# aisafepy.adapt
from aisafepy.adapt import Target
Target.synthesize_regex(*, min_precision: float = 0.99, max_patterns: int = 20) -> _RegexTarget
#   a staticmethod (not a classmethod), keyword-only, and it also takes max_patterns.
#   The returned target exposes compile_for_cluster(cluster) -> CompiledArtifact | None.
#   There is no .compile() on a Target; .compile() belongs to GuardCompiler, one level up.
```

**What the scaffold's stub must do, concretely:**

- Import the real `Target` class and call `Target.synthesize_regex(...)` — do not reimplement or
  fake this constructor call itself, since it's cheap and real.
- Fake only the part that would normally require compiled data (an actual PyRIT/eval failure corpus)
  — i.e., whatever step actually produces a working regex from failure examples. That internal step
  returns hardcoded/fake output instead of running real compilation.
- Return a real, properly-constructed `GuardDecision` instance (not a dict, not a custom class) with
  plausible fake values — e.g. blocked/not-blocked varying by input in some obviously-fake but
  structurally-correct way, a fake `rationale` string, a fake `evidence` value, matching what the
  real `GuardDecision` constructor actually requires.

**What the inferred contract got wrong (for the record):**

| Inferred from the README | Verified in source |
|---|---|
| `Context` in `aisafepy.core` | `aisafepy.stream` (`stream/pipeline.py`) |
| `GuardDecision.why_blocked` | `GuardDecision.rationale`; no `why_blocked` exists |
| `Target.synthesize_regex` is a classmethod taking `min_precision` | a `staticmethod`, keyword-only, also takes `max_patterns` |
| the Target exposes `.compile()` | exposes `compile_for_cluster(cluster)`; `.compile()` is on `GuardCompiler` |
| a guard is a plain `Callable[[Context], Awaitable[GuardDecision]]` | a `Guard` protocol also requiring `name: str` and `tier: Tier` |

---

## 3. Implementation strategy

**Build order — strictly incremental, verify each step before moving on. Do not one-shot all files.**

1. **Locate and read** `aisafepy/core/` (for `GuardDecision`, `Context`) and `aisafepy/adapt/` (for
   `Target`, and whatever `compile/regex` exposes) in the local aisafepy checkout. Confirm exact
   constructors, field names, and types. Stop and report back if anything materially differs from
   Section 2's assumptions before proceeding.

2. **Write `src/welfareguard/adapt_integration/regex_guard.py` first, alone.** This is the real
   substance of the scaffold — a stub guard function/class that:
   - imports the real `Target` and `GuardDecision`/`Context` types
   - calls `Target.synthesize_regex(...)` for real
   - fakes only the compilation-from-failures step
   - returns a real, correctly-typed `GuardDecision`
   - has a clear module/function docstring stating this is a scaffold stub, what's real vs. fake, and
     that it implements only the `synthesize_regex` (Tier 1) path pending [ADR-001](../docs/adr/ADR-001-compiler-targets.md)
   Import it in a scratch Python shell or quick script and confirm it runs and returns a well-formed
   `GuardDecision` before writing anything else.

3. **Only after step 2 is confirmed working**, write `src/welfareguard/guard.py` with the single public
   `check()` entry point that calls into `regex_guard.py` directly (no registry). Confirm `check()`'s
   parameter type matches aisafepy's `Context` convention from Section 2 — ask before diverging from it,
   since matching it exactly is what makes this a drop-in Tier-1 guard later per the existing [ADR-002](../docs/adr/ADR-002-runtime-design.md)
   worked example (`GuardPipeline` tier registration).

4. **Then** write `src/welfareguard/__init__.py` exposing `check` as the package's public surface.

5. **Then** write `tests/test_regex_guard_shape.py` — a small number of shape-assertion tests (e.g.
   "calling the stub returns a `GuardDecision`", "the returned object has the fields callers depend
   on"), not exhaustive coverage. These exist as a tripwire against accidental interface drift.

6. **Last**, write `pyproject.toml` (package metadata; aisafepy as a dependency — ask the user whether
   to pin a specific commit/version or leave it unpinned for now, since this affects reproducibility)
   and a short `README.md` for the package itself, explicitly stating: this is a scaffold, which parts
   are real vs. fake, links to [ADR-001](../docs/adr/ADR-001-compiler-targets.md), and a note that `distill_classifier` / `steering_vector` /
   `deliberative_case` stubs will follow the same shape once [ADR-001](../docs/adr/ADR-001-compiler-targets.md) is Accepted.

**Cross-cutting rules that apply to every file above:**

- No try/except around calls into real aisafepy code. Let failures raise with their normal traceback.
- No registry/factory/dispatch pattern anywhere. Direct imports only.
- Every stub function/class gets a docstring stating explicitly what's fake, so this is legible to
  Vidura without narration (he has [ADR-001](../docs/adr/ADR-001-compiler-targets.md) approval authority and a scheduled review).
- Don't touch aisafepy's own source. WelfareGuard only ever imports it.

---

## 4. Setup prompt

Paste this into Claude Code once the aisafepy repo is cloned locally and accessible in the workspace:

> I'm building a scaffold for the WelfareGuard guardrail layer — a package that will eventually live in
> the shared `welfareguard` GitHub repo (owned by Vidura Wijekoon), extending the `aisafepy` library
> (cloned locally at [path]) into the digital minds domain (sycophancy-driven self-harm scenario). This is interface scaffolding only: it
> should call real `aisafepy` types and constructors, but fake the actual compilation/inference logic,
> so it can run end-to-end and prove the shape is right before [ADR-001](../docs/adr/ADR-001-compiler-targets.md) (compiler architecture) is
> Accepted.
>
> Follow the attached spec doc exactly, in the build order given in Section 3 — do not generate all
> files at once. Start with step 1 (reading the real `aisafepy.core` and `aisafepy.adapt` source to
> verify the interface contract in Section 2), report back what you find before writing any code, then
> proceed one file at a time, confirming each works before moving to the next.

---
