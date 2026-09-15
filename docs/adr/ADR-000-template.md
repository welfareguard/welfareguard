# ARCHITECTURE DECISION RECORD

**Template and Working Guide**

WelfareGuard  |  Sentient Futures Project Incubator  |  Aug 29 - Nov 6, 2026

## 1  Why We Write ADRs

An Architecture Decision Record is a one-page note that captures a technical decision at the moment it is made: what the situation was, what we chose, what we rejected, and what it costs us later. It is written before the code, not after.

In a 10-week project with three people in three timezones, ADRs do four specific jobs:

- They stop rework. A decision is reviewed and agreed before anyone spends twenty hours building on it.
- They make review possible asynchronously. Vidura can approve a design at 18:30 Colombo without a live call.
- They preserve reasoning. In Week 8, when the paper needs a methods section, the argument is already written down.
- They protect the aisafepy boundary. Every ADR must state whether the upstream library is affected.

**Golden rule from the hand guide: no architecture decisions outside an ADR. Write it, Vidura approves it, then build.**

### When an ADR is required

| **WRITE AN ADR** | **NO ADR NEEDED** |
| --- | --- |
| Choosing a library, framework, or algorithm (clustering method, probe type, eval harness structure) | Ordinary implementation inside an already-approved design |
| Defining or changing a public interface, schema, or file format | Bug fixes, refactors that preserve behaviour |
| Anything that touches the aisafepy boundary | Adding a test, a docstring, or a scenario that follows the template |
| Changing a metric definition after baselines have been run | Renaming a local variable, formatting, linting |
| Anything you would feel the need to explain in the paper's methods section | Anything you could reverse in under an hour |

*If you are unsure, write one. A short ADR costs twenty minutes; an unreviewed decision discovered in Week 7 costs a week.*

### How it flows

- Draft the ADR in the repo as docs/adr/ADR-NNN-short-slug.md and open a pull request.
- Tag Vidura. Review happens within 48 hours, the same SLA as code review.
- Outcome is Approved, Approved with changes, or Rejected - all three are recorded in the ADR itself.
- Only after approval does implementation start.
- An approved ADR is never edited. If the decision changes, write a new one and mark the old status as Superseded by ADR-NNN.

## 2  The Template

*Copy this structure into docs/adr/ADR-NNN-short-slug.md. Fill every section. If a section genuinely does not apply, write "not applicable" and one line of why - do not delete it.*

### Header block

| **Title** | ADR-NNN: short decision in the imperative (e.g. "Use HDBSCAN for failure clustering") |
| --- | --- |
| **Status** | Proposed \| Accepted \| Rejected \| Superseded by ADR-NNN |
| **Date** | YYYY-MM-DD |
| **Author** | Who is proposing this |
| **Reviewer** | Vidura - approval required before implementation |
| **Repository** | welfareguard or aisafepy |
| **Affects** | Which part of the system (evals harness, compiler pass, runtime layer) |

### 1. Context

What situation forces a decision? State facts, not conclusions. Cover what we are building, why the choice arose now, and the constraints that matter: the 10-week timeline, mentee hours, API budget, and the existing aisafepy API. Link any earlier ADR this must fit inside.

*Test for this section: if someone joins the project in Week 6, can they understand the problem without asking anyone?*

### 2. Decision

One or two sentences in the present tense: "We will use X." No hedging. If the decision is conditional, state the exact condition.

### 3. Options Considered

A short table of the realistic alternatives with pros, cons, and a verdict for each. Always include the option of doing nothing or deferring - sometimes it wins.

| **OPTION** | **PROS** | **CONS** | **VERDICT** |
| --- | --- | --- | --- |
| A. The chosen option |  |  | **Chosen** |
| B. |  |  | Rejected - why |
| C. Do nothing / defer |  |  | Rejected - why |

### 4. Consequences

- What becomes easier as a result of this decision.
- What becomes harder or riskier.
- What this locks in - how expensive is it to reverse after the design freeze?
- Cost: engineering hours, API spend, and any new dependency added.

### 5. Impact on aisafepy (upstream)

Answer explicitly. This is the boundary rule from the hand guide, and it is the one section that is never optional:

☐  No change needed to aisafepy. WelfareGuard only imports it.

☐  Requires a change inside aisafepy - stop. Raise a separate ADR and pull request against the aisafepy repository, and name it here. Never bundle an upstream change into a WelfareGuard PR.

### 6. Implementation Notes

- Files or modules affected.
- Tests required before this can be marked done.
- Rough estimate in hours.
- Owner.

### 7. Review

| **Submitted** | YYYY-MM-DD |
| --- | --- |
| **Decision** | Approved \| Approved with changes \| Rejected |
| **Reviewer notes** |  |
| **Approved on** | YYYY-MM-DD |

## 3  Worked Example

*A filled-in ADR of roughly the right length and tone. Yours should be about this size - one to two pages, not five.*

**ADR-002: Run welfare guardrails as a cascade tier, not a wrapper**

| **Status** | Accepted |
| --- | --- |
| **Date** | 2026-09-10 |
| **Author** | Richard Lin |
| **Reviewer** | Vidura Wijekoon |
| **Repository** | welfareguard |
| **Affects** | Runtime layer, benchmark harness |

### 1. Context

The compiler produces welfare guards from failed evals. Those guards have to run somewhere at inference time. aisafepy.stream already ships a three-tier cascade with a p95 latency budget and a shared GuardDecision return type. We can either place welfare guards inside that cascade as an additional set of guards, or wrap the agent separately and run welfare checks outside aisafepy's pipeline. This decision blocks the Week 6 mitigation benchmark, because the benchmark measures added latency and needs one place to instrument.

### 2. Decision

**We will register welfare guards inside the existing aisafepy.stream cascade - deterministic checks at Tier 1, the distilled welfare classifier at Tier 2 - rather than building a separate wrapper around the agent.**

### 3. Options Considered

| **OPTION** | **PROS** | **CONS** | **VERDICT** |
| --- | --- | --- | --- |
| A. Register inside the aisafepy cascade | Reuses the latency budget, telemetry, and GuardDecision type; one instrumentation point for the benchmark | Constrained by the existing tier structure | **Chosen** |
| B. Separate welfare wrapper around the agent | Total freedom over structure | Duplicates budget and telemetry logic; two latency numbers to reconcile in the paper; more code to test in 10 weeks | Rejected - cost outweighs the flexibility |
| C. Defer until after baselines | Keeps options open | Blocks the Week 6 benchmark, which is the paper's core evidence | Rejected - it is on the critical path |

### 4. Consequences

- Easier: latency, false-positive rate, and harm-rate all come from one harness, so the results table is internally consistent.
- Harder: welfare guards must conform to the existing tier timing budgets, so anything slower than roughly 100 ms has to go to Tier 3 or be distilled.
- Locks in: reversing this after the Week 7 experiment freeze would invalidate collected baselines, so it is effectively permanent from Week 5.
- Cost: about 6 hours of adapter work, no new dependencies.

### 5. Impact on aisafepy (upstream)

**No change needed to aisafepy. Registering guards in a tier is part of the library's existing public API, so WelfareGuard only imports it.**

### 6. Implementation Notes

- Files: welfareguard/runtime/tiers.py, welfareguard/benchmark/harness.py.
- Tests: tier registration, budget-exceeded path, and a benign-control false-positive check.
- Estimate: 6 hours. Owner: Richard.

### 7. Review

| **Submitted** | 2026-09-10 |
| --- | --- |
| **Decision** | Approved |
| **Reviewer notes** | Agreed. Record the Tier 2 timing headroom in the methods section so the paper can report it. |
| **Approved on** | 2026-09-11 |

## 4  Filing Conventions

- Path: docs/adr/ADR-NNN-short-slug.md, numbered sequentially from 001. Numbers are never reused.
- One decision per ADR. If you are writing "and also", it is two ADRs.
- Length: one to two pages. If it runs longer, the decision is probably several decisions.
- Status is updated in place only to record Accepted, Rejected, or Superseded - the body is never rewritten after approval.
- Link related ADRs by number so the chain of reasoning stays readable in Week 10.
