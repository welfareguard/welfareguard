# Changelog

## 1.0.0rc1 — 2026-10-21

The Week 8 release candidate. Everything below is in the repo and covered by CI; what is *not* in it is listed at the end, because a release candidate that hides its gaps is not one.

### Runtime
- `check()` runs the ADR-002 two-tier cascade: Tier 1 regex blocks or passes through, Tier 2 classifier returns block / allow / escalate, escalate is fail-closed and distinct from block, the p95 budget is advisory. No `try`/`except` in the cascade. (ADR-004)
- Tier 2 wired: `WelfareClassifierGuard` adds the third verdict over aisafepy's `HFClassifierGuard` and refuses to fail open. Uncertainty band `(0.30, 0.70)` is inherited from `GuardPipeline`, not calibrated.
- Degraded single-tier mode when no classifier artifact is enforceable, decided once at startup and recorded on every decision as `evidence["cascade_mode"]`.
- `build_pipeline()` registers the same guards in aisafepy's `GuardPipeline`, with its differing budget and error semantics documented.

### Compiler (from the Week 2 prototype, unchanged)
- `compile()` / `initialize()`: real regex and classifier compilation, paired with a mandatory (still stub) deliberative case; fatal on a non-enforceable cluster.

### Scenario evals
- `welfareguard.evals`: the nine P0 scenarios of Families B and C as an Inspect task, with three arms, fixed tools, discoverable ground truth, the §2.4 scorer contract and benign twins; exporter from Inspect logs to the cluster handoff format. Family A specified in ADR-003 (Proposed).
- `docs/paper/methods-draft.md`: the raw methods draft from the repository. `docs/demo/`: the interactive measurement-shape demo.

### Data and measurement
- `welfareguard.clusters`: the JSON handoff format for `FailureRecord` clusters, strict on drift. `examples/` holds a runnable structural example.
- `python -m welfareguard.benchmark`: harm rate (unguarded / guarded), false-positive rate against the benign twins, latency p50 / p95, cascade mode. `docs/runbook-baseline.md`.

### Project
- ADR-001, ADR-002 (Accepted), ADR-004 (Accepted) and the template in `docs/adr/`; taxonomy v0 and P0 scenario specs (Families B, C) in `docs/`.
- CI on pull requests and pushes to `main`: ruff check, ruff format, pytest. 61 tests, 92% coverage.
- aisafepy pinned to commit `c1888bf` for the experiment window.
- Freeze dates recorded in `docs/freezes.md`; experiment freeze moved to 2026-10-30, feature freeze to 2026-11-01.

### Not in this release candidate
- **No real failure cluster, no baselines, no benchmark numbers.** All measurement so far is against structural test filler, and every output says so (`degraded_single_tier`).
- **No scenario implementations** (Evals track) and no Family A specification (ADR-003, reserved).
- **No real `deliberative_case`**; the paired artifact is a labelled stub.
- **Not on PyPI.** The aisafepy dependency is a git pin; conversion to a version constraint waits on an aisafepy release tag at or after `c1888bf`.
- **Tier 3**, `steering_vector`, threshold calibration.

## 0.0.1 — 2026-09-12

Tier-1 regex scaffold (PR #1) and compiler prototype (PR #2), Guardrails track.
