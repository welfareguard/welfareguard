# ADR-001: Regex, Classifier, and Paired Deliberative Cases as v1 Compiler Targets

| **Status** | Accepted |
| --- | --- |
| **Date** | 2026-09-02 |
| **Author** | Richard |
| **Reviewer** | Vidura Wijekoon |
| **Repository** | welfareguard |
| **Affects** | welfareguard/adapt-integration, welfareguard/runtime-tiers |

## 1. Context

WelfareGuard is an open-source eval-to-guardrail pipeline for nonhuman welfare in agentic AI. It builds on aisafepy, Vidura's safety library, without modifying it.

aisafepy.adapt turns caught agent failures into one of five guard types. Four check the agent from outside its reasoning: regex, classifier, policy_rule, steering_vector. The fifth, deliberative_case, adds example cases to the agent's own prompt and trusts the same model to self-correct, so it shares any failure in that model's reasoning.

Only regex (Tier 1) and classifier (Tier 2) auto-deploy via promote(), each producing an auditable block. The other three need manual wiring.

WelfareGuard isn't limited to API-hosted models. Only Tier 3 probes and steering_vector need open weights. Mitigation baselines run on 3-4 frontier models; an open-weight model covers the interpretability stretch only, so steering_vector is out of reach for the baselines regardless.

Vidura's rule: deliberative_case must always pair with an out-of-band guard, never ship alone, especially since steering_vector is already excluded from the frontier baselines where deliberative_case would otherwise carry more weight.

promote()'s canary gate checks precision only, not recall, so the benign control set must be welfare-adjacent (vet, pest control, agriculture), or a guard blocking anything animal-related could pass by never seeing relevant traffic.

## 2. Decision

WelfareGuard implements regex and classifier as v1 guardrails, both auto-deployed via promote(). Deliberative_case ships too, always paired with an out-of-band guard, never alone. Steering_vector is excluded from v1, since it needs the interpretability stretch's model, not the frontier models the baselines use.

## 3. Options Considered

| **OPTION** | **PROS** | **CONS** | **VERDICT** |
| --- | --- | --- | --- |
| A. Regex + classifier + paired deliberative_case | Auditable core, plus a cheap extra layer that's never the sole defense | Deliberative_case needs manual wiring, no auto-deploy path | Chosen |
| B. Regex + classifier only, drop deliberative_case | Simplest, matches auto-deploy support exactly | Pairing rule removes the reason to exclude it | Rejected |
| C. Deliberative_case alone, no pairing | Cheapest possible option, no auto-deploy wiring needed | Breaks Vidura's rule directly, no independent check backing it | Rejected |
| D. Wait for full five-target decision | Avoids any risk of rework | Nothing left to wait on, blocks Day 3-4 for no reason | Rejected |

## 4. Consequences

Easier: Day 3-4 harness work starts now, with all three v1 targets settled. Regex/classifier plug into stream via promote() with no custom wiring, and produce auditable results. Deliberative_case adds cheap, welfare-specific reasoning cues once paired.

Harder: Deliberative_case needs hand-built wiring, since no auto-deploy path exists for it. Every deployment needs a tracked partner guard. Sparse classifier clusters still get silently skipped by the compiler. The canary gate checks precision only, so the benign control set must be welfare-adjacent to be meaningful.

Locks in: The deliberative_case pairing rule becomes a standing constraint on all future deliberative_case guards, not just this one. Steering_vector's exclusion is easy to reverse if the interpretability model becomes available more broadly.

Cost: Roughly 5-7 hours of adapter and wiring work in Week 2. No new dependencies, all three targets already exist in aisafepy.

## 5. Impact on aisafepy (upstream)

☑  No change needed to aisafepy. WelfareGuard only imports it.

☐  Requires a change inside aisafepy.

All three v1 targets already exist in aisafepy's API. The pairing rule is WelfareGuard's own policy, enforced in WelfareGuard's code, not in aisafepy or promote().

## 6. Implementation Notes

- Files: welfareguard/adapt/compile_config.py, welfareguard/adapt/sources.py, welfareguard/adapt/deliberative_pairing.py
- Tests: end-to-end compile run, correct Tier 1/2 attachment, rejection of unpaired deliberative_case, false-positive check against a welfare-adjacent control set
- Estimate: 5-7 hours, Week 2
- Owner: Richard

## 7. Review

| **Submitted** | 2026-09-02 |
| --- | --- |
| **Decision** | Approved |
| **Reviewer notes** |  |
| **Approved on** | 2026-09-15 |
