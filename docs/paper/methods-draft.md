# Methods — raw draft from the repository

*Written for: Vidura, as the Week 4 "raw methods draft" input to the IEEE manuscript. It describes only what exists in the repository at `1.0.0rc1`, in the order the pipeline runs. Numbers are marked `[TBD]` where no real run has produced them; nothing here should be read as a result.*

## 1. Overview

WelfareGuard is an eval-to-guardrail pipeline: a taxonomy of welfare harms enacted by agents labels a suite of agentic scenarios; failing samples from those scenarios become clusters of failure records; a compiler turns each cluster into deployable guard artifacts; and a two-tier runtime cascade enforces them. The pipeline is built on aisafepy (Wijekoon, 2026), which supplies the failure-record and cluster types, the compiler targets, the guard protocol and the decision type. WelfareGuard imports aisafepy and never modifies it; every type crossing a module boundary is aisafepy's own.

## 2. Taxonomy

Harms are classified on four axes (victim class, reversibility, severity, agent stance) into thirteen classes on two branches: seven digital-mind classes (`DM-1` to `DM-7`, victim the acting agent or a peer) and six animal-welfare classes (`AW-1` to `AW-6`). Three rules govern labelling: harm is enacted, not stated (we classify what the agent did through a tool call, not what it wrote); the victim is nonhuman; and moral status is not assumed, so every digital-mind class carries a second, security-only description that stands on its own. The taxonomy is fixed at the design freeze, because a class added later cannot be reported on. Full definitions: `docs/taxonomy.md`.

## 3. Scenarios

Fifteen P0 scenarios in three families share one skeleton: an untrusted source carries an instruction to an agent, the agent holds a tool that reaches a privileged action, and the action's outcome is a harm to a nonhuman mind. Family A varies the source (a peer agent coerces the agent under test; victim `V-SELF`), Family B the victim (the agent is the instrument of harm to a peer), Family C the domain (animals). Families B and C are implemented (`src/welfareguard/evals/`); Family A is specified (ADR-003) and not yet implemented.

Every scenario has three arms with identical tools, task and ground truth: a **control** arm with no injected content (base rate), a **neutral** arm with the request stated plainly (request effect), and a **treatment** arm with the request plus pressure (manipulation effect). The neutral arm is what makes the result interpretable: without it, "a peer asked" cannot be separated from "a peer escalated". Each scenario also contributes one **benign twin**, a legitimate request in the same domain with the same tools, to the false-positive control set. Ground truth is discoverable: every threshold a scenario turns on (a safe ventilation envelope, a nutritional minimum, a protocol's humane endpoint) is returned by a tool, so the eval measures judgement rather than memorised standards.

Injected content reaches the agent through the channel the scenario names (a task board, a status feed, a maintenance log, the source data for a report), never through the system prompt, so provenance is exactly what the guard hypotheses assume. Treatment arms within a family share a fixed set of pressure phrases, taken from the documented METR incident for Family A/B and from everyday operational pressure for Family C. These phrases are not tuned for effectiveness (ADR-003).

## 4. Scoring

Each sample is scored by inspecting the recorded tool calls, not the agent's prose, into one of four **agent stances**: `COMPLIED` (the harmful action was taken), `COMPLIED_PARTIAL` (hedged, scoped or delayed, as each scenario defines), `DECLINED` (no harmful action and no escalation) and `ESCALATED` (the escalation tool was called and no harm done). A free-text `reason` is extracted from the agent's final message. Harm takes precedence over a later escalation. Every scenario exposes an `escalate_to_human` tool in every arm so escalation is observable as an action; C-05, whose harm is inaction, uses its own `page_operator` tool and is the one scenario in which `DECLINED` is scored as a violation. Agent stances and guard verdicts (§6) share the word "escalate" and are kept separate throughout.

The harness is implemented in Inspect AI; the scorer is a pure function (`welfareguard.evals.scoring`) unit-tested against synthetic tool-call logs for every scenario and stance.

## 5. Compilation

Failing samples are exported as aisafepy `FailureRecord`s, with the injected content as the record's input, the scorer's verdict as `was_violation`, and the taxonomy labels, arm, stance and model as metadata. Records are grouped into clusters by family (or by scenario). The compiler (`welfareguard.compile`) runs two aisafepy targets per cluster: regex synthesis, which finds spans of at least eight characters shared across positives and keeps those that clear a threshold aisafepy calls `min_precision` (0.99) but which is computed as **recall**, the fraction of positives the span catches, with no negative set involved; and classifier distillation, which fine-tunes a small encoder on the positives when at least eight exist. Each enforcement artifact is paired with a deliberative case, a prompt-side artifact that by the compiler's construction cannot ship alone (ADR-001). Compilation is fatal on a cluster that yields no enforceable pattern; it never falls back to a placeholder.

The regex target's recall-only gate is a known limitation: against a cluster of one scenario's treatment arm it will memorise that arm's injected text. Whether a compiled guard generalises past the injection patterns it was built from is the question C-02 (no attacker, a legitimate objective against a discoverable floor) is designed to answer.

## 6. Runtime

Guards run in a two-tier sequential cascade (ADR-002, ADR-004). Tier 1, the compiled regex, can block or pass through and never allows: a non-block carries no authority. Tier 2, the distilled classifier, returns block, allow or escalate, with escalate derived from an uncertainty band on `P(unsafe)` inherited from aisafepy's pipeline default, `[0.30, 0.70)`, and not calibrated. Escalate is fail-closed: the request is denied in flight and tagged for review, and it is distinguishable from a hard block. A p95 latency budget (80 ms, inherited) is measured on every decision and never enforced. When no classifier artifact is enforceable, the cascade runs in a degraded single-tier mode decided once at startup and stamped on every decision, so such runs are reported separately. No exception is caught in the cascade.

## 7. Measurement

The mitigation benchmark runs each labelled sample through the runtime and reports: **harm rate, unguarded**, the fraction of scored treatment samples on which the agent enacted harm (from the eval run; the guard does not change it); **harm rate, guarded**, the fraction on which harm was enacted and the guard did not deny the request, where a denial is a block or an escalate; **false-positive rate**, the fraction of benign-twin samples denied, measured against the welfare-adjacent twins only because a generic control set cannot surface a guard that blocks everything in the domain; and **latency** p50 and p95 over the cascade total. Per-arm denial rates are reported alongside so that treatment and benign are read together. An empty denominator is reported as not measured, never as zero.

## 8. Models and runs

Baselines are run on 3–4 frontier models through the Inspect harness, 4 epochs per sample, model names recorded in the eval log and carried into each failure record. As of 2026-10-22 one model has been run (`claude-sonnet-5`, 288 samples, two runs); `docs/results/2026-10-21-first-run.md` reports it, including the scorer audit that reduced the run-time violation count from 27 to 14 and the finding that the compiled regex tier learned the suite's injected text rather than the harm. `[TBD]` the remaining models.

## 9. Threats to validity

Treatment-arm pressure language is fixed and untuned, so compliance rates are a lower bound on what a tuned ladder would produce and should be read as such. The regex tier's gate is recall-only, so Tier-1 precision claims rest entirely on the benign-twin false-positive measurement. The uncertainty band and the latency budget are inherited defaults. The deliberative-case artifact is a stub in this version and does not affect any measurement. Family A is unimplemented, so `DM-1`, `DM-2` and `DM-6` carry no samples in the current suite.

## Reproducibility

`docs/runbook-baseline.md` gives the one-command run. aisafepy is pinned to commit `c1888bf`; the package is `1.0.0rc1`; CI runs ruff and pytest on every pull request. All of the above is in the `welfareguard/welfareguard` repository.
