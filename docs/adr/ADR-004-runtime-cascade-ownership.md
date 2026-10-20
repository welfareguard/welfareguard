# ADR-004: Own the ADR-002 cascade in WelfareGuard, and run single-tier degraded when no classifier is enforceable

| **Status** | Proposed |
| --- | --- |
| **Date** | 2026-10-20 |
| **Author** | Vidura Wijekoon (repo maintainer) |
| **Reviewer** | Vidura Wijekoon |
| **Repository** | welfareguard |
| **Affects** | welfareguard/runtime, welfareguard/benchmark |

## 1. Context

[ADR-002](ADR-002-runtime-design.md) fixes the v1 runtime contract: two sequential tiers, Tier 1 blocks or passes through, Tier 2 returns block, allow or escalate, escalate is fail-closed, and the p95 latency budget is measured, not enforced. Implementing it raised two questions the ADR does not answer.

**Who runs the cascade.** aisafepy's `GuardPipeline` (`stream/pipeline.py`) already runs Tier 1 then Tier 2, short-circuiting on a terminal decision, and `GuardDecision.ESCALATE` is already terminal and distinct from `BLOCK`. That is most of ADR-002. It differs on two points: it *enforces* the budget (once the deadline has passed after Tier 1 it skips Tier 2 and returns a budget decision, fail-open by default), and its `_safe_call` turns an exception raised by a guard into an allow carrying `evidence["error"]`. ADR-002 makes the budget advisory because no measured Tier 2 latency exists to justify a cut-off, and its constraint that uncertainty never becomes permission is incompatible with failing open on error. The build specs also forbid `try`/`except` around aisafepy calls.

**What Tier 2 means when there is no Tier 2.** aisafepy's classifier target returns a non-enforceable artifact (`payload=None`) below eight positives or when `torch`/`transformers` are absent. The compiler prototype made that non-fatal on the grounds that Tier 2 was not wired. Wiring Tier 2 expires that reasoning: the cascade must do something when it reaches a tier that cannot enforce. Three options were on the table: let the request through (grants Tier 1 the allow authority ADR-002 denies it), escalate everything (fail-closed but useless), or refuse to initialise (takes down a working regex guard over a tier that is not yet validated).

A third, smaller question: aisafepy's `HFClassifierGuard` is two-way (block above a threshold, allow below). ADR-002's Tier 2 is three-way.

## 2. Decision

WelfareGuard owns the cascade: `welfareguard.runtime.cascade.WelfareCascade` implements ADR-002's verdict contract directly, with the budget advisory and no exception handling. The same guards are also registerable in aisafepy's `GuardPipeline` through `welfareguard.runtime.pipeline.build_pipeline()` for callers that already run one, with the two semantic differences documented at that function. When no classifier artifact is enforceable, the cascade comes up in `DEGRADED_SINGLE_TIER` mode, decided once at startup, logged once, and stamped into `evidence["cascade_mode"]` on every decision served; a Tier 1 pass-through is then returned as-is, annotated, rather than converted into a verdict Tier 1 never gave. Tier 2's third verdict is added by `WelfareClassifierGuard`, which maps `P(unsafe)` through an uncertainty band inherited unchanged from `GuardPipeline`'s default, `(0.30, 0.70)`.

## 3. Options Considered

| **OPTION** | **PROS** | **CONS** | **VERDICT** |
| --- | --- | --- | --- |
| A. Own the cascade; expose `GuardPipeline` registration alongside; degrade single-tier with the mode stamped on every decision | Verdict contract is exactly ADR-002's; no fail-open path; benchmark can segregate degraded runs; drop-in registration preserved | Two code paths for callers to choose between; degraded mode does let Tier 1 pass-throughs reach the caller unreviewed | **Chosen** |
| B. Use `GuardPipeline` only, with `budget_ms_p95` set effectively infinite | Less code; one implementation | Budget "advisory" by configuration trick rather than by design; `_safe_call` still fails open on guard error; `on_budget_exceeded` semantics still reachable | Rejected, keeps the two behaviours ADR-002 decided against |
| C. Degraded mode escalates every request | Fail-closed in the strictest sense | Every request denied; a regex-only deployment becomes unusable, which is the outcome compilation was made non-fatal to avoid | Rejected, useless |
| D. Refuse to initialise without an enforceable classifier | Simplest contract: two tiers or nothing | Takes down a working Tier 1 over a tier that has not been validated end-to-end; contradicts the compiler prototype's deliberate non-fatal classifier outcome | Rejected, wrong failure to prefer |
| E. Defer until a classifier has been distilled and benchmarked | Decides with data | The benchmark needs a running cascade to produce the data; circular | Rejected, on the critical path |

## 4. Consequences

Easier: the runtime contract is small, owned, and tested exhaustively (`tests/test_runtime_cascade.py`). The metrics harness has one path to instrument and can read `cascade_mode` to keep degraded runs out of the two-tier numbers. The original eight scaffold tests and the thirteen compiler tests pass unmodified.

Harder: callers who use `build_pipeline()` get aisafepy's budget and error semantics, not ADR-002's, and have to know that. Degraded mode means a request Tier 1 did not block is returned as Tier 1's allow; the decision says so, but the caller has to read it. The uncertainty band is inherited, not calibrated, and its edges will move once real Tier 2 data exists.

Locks in: `evidence["cascade_mode"]`, `evidence["tiers_run"]` and `evidence["budget_exceeded"]` become part of what the benchmark reads, so renaming them after baselines would invalidate collected runs. Reversing the ownership decision (back to `GuardPipeline` only) is mechanically cheap but would reintroduce the fail-open path.

Cost: implemented in this change. No new dependencies; `torch`/`transformers` remain optional and are never loaded by the test suite.

## 5. Impact on aisafepy (upstream)

☑  No change needed to aisafepy. WelfareGuard only imports it.

☐  Requires a change inside aisafepy.

`GuardPipeline`, `Guard`, `GuardDecision.escalate` and `HFClassifierGuard` are all existing public API. The advisory budget, the refusal to fail open, the three-way mapping and the degraded mode are WelfareGuard policy, in WelfareGuard's code. Two observations are worth raising upstream on their own track, not as part of this ADR: `_safe_call` failing open is a design choice aisafepy users should be able to turn off, and `HFClassifierGuard` has no escalate verdict.

## 6. Implementation Notes

- Files: `src/welfareguard/runtime/cascade.py`, `src/welfareguard/runtime/pipeline.py`, `src/welfareguard/adapt_integration/classifier_guard.py`, `src/welfareguard/guard.py` (`check()` routes through the cascade; signature unchanged)
- Tests: Tier 1 block short-circuits and Tier 2 is never called; Tier 1 pass always reaches Tier 2; escalate is terminal and distinct from block; budget overrun is recorded without altering the verdict; degraded mode is recorded on every decision and preserves Tier 1 evidence; the mode cannot disagree with the guards; the classifier guard refuses to fail open; `GuardPipeline` registration needs no adapter; the deliberative case never reaches a tier
- Estimate: done in this change
- Owner: Vidura Wijekoon

## 7. Review

| **Submitted** | 2026-10-20 |
| --- | --- |
| **Decision** |  |
| **Reviewer notes** |  |
| **Approved on** |  |
