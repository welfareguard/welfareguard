# ADR-002: Run the v1 welfare runtime as a fail-closed two-tier cascade

| **Status** | Accepted |
| --- | --- |
| **Date** | 2026-09-12 |
| **Author** | Richard |
| **Reviewer** | Vidura Wijekoon |
| **Repository** | welfareguard |
| **Affects** | welfareguard/runtime-tiers, benchmark harness |

## 1. Context

ADR-001 settled which guards the compiler produces: regex and classifier auto-deploy via `promote()`, deliberative_case ships only when paired with an out-of-band guard, steering_vector is out of v1. This ADR settles how those guards behave once they are running against live traffic.

`aisafepy.stream` ships a cascade with deterministic Tier 1, small-classifier Tier 2, and optional Tier 3 activation probes or LLM judge, plus a `budget_ms_p95` parameter and a shared `GuardDecision` return type. WelfareGuard registers its guards inside that cascade rather than wrapping the agent separately. That placement is assumed here, not decided here, and it is currently only recorded in the ADR template's worked example. If it needs a real record, it should be written as its own ADR.

What the cascade does not yet define for WelfareGuard is the runtime semantics: whether tiers run in sequence or together, what authority each tier has, what verdicts a tier can return, what happens to an uncertain request in flight, and whether the latency budget cuts anything off. Those are the open questions. They block the Week 2 design freeze and the Week 6 mitigation benchmark, which needs stable runtime behaviour before it can measure added latency and false-positive rate against anything.

Two constraints shape the answers. The benign control set is welfare-adjacent, and `promote()`'s canary gate measures precision only, so the runtime must not quietly convert uncertainty into permission. And there is no real Tier 2 latency data yet, because no classifier has been distilled and benchmarked.

## 2. Decision

**The v1 welfare runtime is a two-tier sequential cascade. Tier 1 runs first and can block or pass through, never allow. Tier 2 runs only if Tier 1 passes, and returns block, allow, or escalate. Escalate is fail-closed: the request is denied in flight and tagged for review. The p95 latency budget is measured and reported, not enforced. Tier 3 is out of scope for v1.**

## 3. Options Considered

| **OPTION** | **PROS** | **CONS** | **VERDICT** |
| --- | --- | --- | --- |
| A. Two-tier sequential, Tier 1 block-only, Tier 2 three-way, escalate fail-closed, budget advisory | Matches the guards ADR-001 actually produces; short-circuit keeps latency low; uncertainty never becomes permission; no speculative interfaces | Fail-closed escalate raises the false-positive rate against `fp_budget`; advisory budget means a slow Tier 2 is visible but not contained | **Chosen** |
| B. Design Tier 3 now alongside Tiers 1 and 2 | Interface complete from day one, no rework when probes arrive | Nothing populates Tier 3 in v1; steering_vector and probes both need self-hosted weights already excluded by ADR-001; locks in an interface with no concrete guard behind it | Rejected, speculative |
| C. Run both tiers on every request and combine verdicts | Every request gets both signals; richer evidence for the paper | Defeats the point of tiering; burns the latency budget on cases Tier 1 already caught; needs a combination rule that is itself a new decision | Rejected, cost without benefit |
| D. Let Tier 1 return an affirmative allow and skip Tier 2 | Saves classifier cost on confidently safe traffic | Synthesized regexes are compiled against attack traffic to hit `min_attack_success_rate`; they detect bad patterns and cannot certify good ones; reintroduces the precision/recall conflation ADR-001 flagged | Rejected, exceeds what the guard was compiled to claim |
| E. Escalate fails open, request proceeds and is logged | Protects availability; keeps false positives inside `fp_budget` | The least certain requests are exactly the ones let through live, which inverts the purpose of a detective layer in a harm-prevention project | Rejected, wrong failure direction |
| F. Enforce the latency budget with a hard timeout | Contains a slow or hanging Tier 2 | Creates a new failure mode needing its own fail-open/closed decision; no measured Tier 2 latency exists yet to justify a threshold | Rejected for v1, revisit once benchmarked |
| G. Defer runtime semantics until after baselines | Decides with real data instead of assumptions | Baselines cannot run without defined runtime behaviour; blocks the Week 2 freeze and the Week 6 benchmark | Rejected, circular and on the critical path |

Deliberative_case is not an option in this table. It is prompt-side only with no independent enforcement, so it is consumed upstream during prompt assembly and never executes inside the cascade. It is absent by construction, not by exclusion.

## 4. Consequences

Easier: the runtime contract is small enough to test exhaustively. Short-circuiting on a Tier 1 block means the cheap deterministic guard absorbs the obvious cases before any classifier cost is paid. One decision path means the Week 6 benchmark has one thing to instrument, and latency, false-positive rate, and harm-rate all describe the same pipeline.

Harder: fail-closed escalate pushes against `fp_budget`, so the welfare-adjacent control set has to be good enough to tell a real escalation from a nervous classifier. Tier 1 having no allow authority means every request that is not blocked pays Tier 2 cost, which sets a floor on p95 latency. An advisory budget makes a slow Tier 2 visible in telemetry but does nothing about it in flight.

Locks in: three-way `GuardDecision` semantics become the runtime contract everything downstream reads, so adding or changing a verdict category after the Week 7 experiment freeze would invalidate collected baselines. Tier 3's absence is cheap to reverse, since adding a tier does not change Tier 1 or Tier 2 behaviour. The fail-closed direction is cheap to reverse mechanically but not evidentially, because flipping it after baselines changes what the numbers mean.

Cost: roughly 5 to 7 hours of runtime and test work in Week 2. No new dependencies.

## 5. Impact on aisafepy (upstream)

☑  No change needed to aisafepy. WelfareGuard only imports it.

☐  Requires a change inside aisafepy.

Sequential tiering, the `GuardDecision` type, and `budget_ms_p95` are all part of the existing public API. The fail-closed escalate rule and Tier 1's lack of allow authority are WelfareGuard policy, enforced in WelfareGuard's own code, not in aisafepy.

## 6. Implementation Notes

- Files: `welfareguard/runtime/cascade.py`, `welfareguard/runtime/decisions.py`, `welfareguard/benchmark/harness.py`
- Tests: Tier 1 block short-circuits and Tier 2 never runs; Tier 1 pass always reaches Tier 2; Tier 2 escalate produces a deny action distinguishable from a hard block; budget overrun is recorded without altering the verdict; false-positive check against the welfare-adjacent control set
- Estimate: 5 to 7 hours, Week 2
- Owner: Richard

## 7. Review

| **Submitted** | 2026-09-12 |
| --- | --- |
| **Decision** | Approved |
| **Reviewer notes** |  |
| **Approved on** | 2026-09-15 |
