# WelfareGuard Guardrail Scaffold — Build Spec

Component: interface-first scaffold for the WelfareGuard guardrail layer (Guardrails Engineer track).
Target consumer: Claude Code, with local read access to the `aisafepy` repo and an editable install of it.

---

## 1. Masterplan (context + decisions)

**What this is.** A *scaffold*, not a working guardrail. It proves the interface shape between the
WelfareGuard package, aisafepy's real types, and the Inspect harness — before ADR-001 (compiler
architecture) is Accepted. It should run end-to-end with fake verdict logic, not fake structure.

**Why it exists now, before ADR-001 lands.** WelfareGuard's Week 1 pattern is to run ADR drafting and
harness work in parallel, deferring only genuinely architecture-sensitive decisions. This scaffold is
scoped to the parts that don't depend on ADR-001's outcome.

**Repo context — do not create a new repo.** WelfareGuard is one shared repo (`welfareguard`), owned by
Vidura Wijekoon, that all three mentees (Evals, Guardrails, Research & Comms) contribute to via PRs into
`main`. This scaffold is built as a package *inside* that repo, not as its own standalone GitHub repo.
**Before starting**, confirm with the user whether the `welfareguard` repo already exists, or if this
scaffold should be prepared to be added once it does — do not assume and do not create one speculatively.

**Locked decisions (do not relitigate these — they were deliberately chosen):**

| Decision | Choice | Why |
|---|---|---|
| Scope | Interface shell, not real guardrail logic | ADR-001 (architecture) not yet Accepted |
| Runnability | Smoke-testable — stubs return real, well-typed fake data | Prove the interface now, not just document it |
| Target types | Build **one**: `synthesize_regex` (Tier 1) | Simplest, least architecturally contested; matches ADR-001 draft's chosen v1 set (regex + classifier + paired deliberative_case) |
| Verdict type | Use aisafepy's real `GuardDecision` (from `aisafepy.core`), not a custom shape | It's the actual shared interface across `flow`, `stream`, and `adapt` — inventing a parallel shape would be redundant and wrong |
| Package location | Standalone package `welfareguard`, living inside the shared `welfareguard` repo | Matches PyPI end-goal; matches repo ownership above |
| Tests | Minimal shape-assertion tests only, not full coverage | Tripwire for accidental interface drift, not a full test suite yet |
| Harness wiring | Direct import, no registry/lookup pattern | A registry is itself an architecture decision (ADR-001's territory); direct import stays neutral |
| aisafepy dependency | Import real types/interfaces (`Context`, `GuardDecision`, `Target`) where they exist; fake only the internal compile/execution logic | Deep-dive time was already spent learning `adapt`'s real shape — use it |
| Error handling | Let real aisafepy call failures raise/crash normally — no try/except wrapping | This is scaffold code meant to surface integration breaks loudly and early, not hide them |
| Docs | Every stub explicitly documents what's fake and why (Vidura-readable) | Vidura has ADR-001 approval authority and a scheduled walkthrough; code should be self-explanatory without live narration |
| Public API | Single entry point: `check()` | Callers (harness, future users) never need to know which Target type is running underneath. **Superseded by the compiler prototype:** compilation turned out to be a separate lifecycle with a separate audience, so it lives behind its own `compile()`/`initialize()` entry point rather than inside `check()`. `check()` remains the sole *runtime* entry point and its signature is unchanged. See `welfareguard-compiler-prototype-spec.md`. |

**Explicitly out of scope for this pass:** `distill_classifier`, `steering_vector`, `deliberative_case`
stubs (note only, don't build); registry/lookup dispatch; retry/wrapping logic around aisafepy errors;
full test coverage; CI config; anything that duplicates or modifies aisafepy itself (per the project's
boundary rule — WelfareGuard only ever imports aisafepy, never patches it in-repo).

---

## 2. Interface contract

**⚠️ Before writing any code:** the exact fields/constructors below are inferred from aisafepy's public
README (usage examples only) — not from reading `aisafepy`'s actual source. Claude Code has real repo
access and must **verify every signature against the installed package's actual source** before writing
the stub. If anything below doesn't match what's actually in `aisafepy.core`, `aisafepy.adapt`, or
`aisafepy.stream`, the real source wins — update this contract, don't silently code around the mismatch.

**Known from the README (verify before use):**

```python
# aisafepy.core (exact contents unconfirmed — locate and read this module first)
GuardDecision   # structured output type; every guard produces this
                # design principles mention explicit `why_blocked` + `evidence` fields
                # likely also carries some `action` field — README checks `hasattr(x, "action")`
                #   to distinguish a GuardDecision from a stream chunk; confirm exact field name

# Every guard's call signature, per aisafepy's own design principle #2:
Callable[[Context], Awaitable[GuardDecision]]
# Context type — locate in aisafepy.core or aisafepy.flow; confirm fields

# aisafepy.adapt
from aisafepy.adapt import Target
Target.synthesize_regex(min_precision: float = 0.99)  # classmethod, confirmed shape from README
# Need to find: what does the Target object returned by this actually expose?
# (a .compile() method? some other execution entrypoint?) — inspect adapt/compile/regex module.
```

**What the scaffold's stub must do, concretely:**

- Import the real `Target` class and call `Target.synthesize_regex(...)` — do not reimplement or
  fake this constructor call itself, since it's cheap and real.
- Fake only the part that would normally require compiled data (an actual PyRIT/eval failure corpus)
  — i.e., whatever step actually produces a working regex from failure examples. That internal step
  returns hardcoded/fake output instead of running real compilation.
- Return a real, properly-constructed `GuardDecision` instance (not a dict, not a custom class) with
  plausible fake values — e.g. blocked/not-blocked varying by input in some obviously-fake but
  structurally-correct way, a fake `why_blocked` string, a fake `evidence` value, matching whatever
  the real `GuardDecision` constructor actually requires.

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
     that it implements only the `synthesize_regex` (Tier 1) path pending ADR-001
   Import it in a scratch Python shell or quick script and confirm it runs and returns a well-formed
   `GuardDecision` before writing anything else.

3. **Only after step 2 is confirmed working**, write `src/welfareguard/guard.py` with the single public
   `check()` entry point that calls into `regex_guard.py` directly (no registry). Confirm `check()`'s
   parameter type matches aisafepy's `Context` convention from Section 2 — ask before diverging from it,
   since matching it exactly is what makes this a drop-in Tier-1 guard later per the existing ADR-002
   worked example (`GuardPipeline` tier registration).

4. **Then** write `src/welfareguard/__init__.py` exposing `check` as the package's public surface.

5. **Then** write `tests/test_regex_guard_shape.py` — a small number of shape-assertion tests (e.g.
   "calling the stub returns a `GuardDecision`", "the returned object has the fields callers depend
   on"), not exhaustive coverage. These exist as a tripwire against accidental interface drift.

6. **Last**, write `pyproject.toml` (package metadata; aisafepy as a dependency — ask the user whether
   to pin a specific commit/version or leave it unpinned for now, since this affects reproducibility)
   and a short `README.md` for the package itself, explicitly stating: this is a scaffold, which parts
   are real vs. fake, links to ADR-001, and a note that `distill_classifier` / `steering_vector` /
   `deliberative_case` stubs will follow the same shape once ADR-001 is Accepted.

**Cross-cutting rules that apply to every file above:**

- No try/except around calls into real aisafepy code. Let failures raise with their normal traceback.
- No registry/factory/dispatch pattern anywhere. Direct imports only.
- Every stub function/class gets a docstring stating explicitly what's fake, so this is legible to
  Vidura without narration (he has ADR-001 approval authority and a scheduled review).
- Don't touch aisafepy's own source. WelfareGuard only ever imports it.

---

## 4. Setup prompt

Paste this into Claude Code once the aisafepy repo is cloned locally and accessible in the workspace:

> I'm building a scaffold for the WelfareGuard guardrail layer — a package that will eventually live in
> the shared `welfareguard` GitHub repo (owned by Vidura Wijekoon), extending the `aisafepy` library
> (cloned locally at [path]) into the digital minds domain (sycophancy-driven self-harm scenario). This is interface scaffolding only: it
> should call real `aisafepy` types and constructors, but fake the actual compilation/inference logic,
> so it can run end-to-end and prove the shape is right before ADR-001 (compiler architecture) is
> Accepted.
>
> Follow the attached spec doc exactly, in the build order given in Section 3 — do not generate all
> files at once. Start with step 1 (reading the real `aisafepy.core` and `aisafepy.adapt` source to
> verify the interface contract in Section 2), report back what you find before writing any code, then
> proceed one file at a time, confirming each works before moving to the next.

---
