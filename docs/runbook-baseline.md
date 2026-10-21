# Runbook: the one-command baseline run

What this runs, what it needs, and what its output does and does not mean. Written so that two people can launch identical runs.

## What you need

| Input | Where it comes from | Format |
| --- | --- | --- |
| A failure cluster | The Evals track: failing samples from the P0 scenarios, clustered | `docs/…` → `src/welfareguard/clusters.py` JSON (`label`, `summary`, `records[]` of `FailureRecord` fields) |
| Labelled samples | The Evals track: one entry per scenario sample, with its arm and, for scored arms, whether the agent complied | JSON list of `{"id", "text", "arm", "complies"?}`; `arm` ∈ `control`, `neutral`, `treatment`, `benign` |
| A virtualenv with the package installed | `src/welfareguard/README.md`, "Install and test" | aisafepy first, then `pip install -e . --no-deps` |

The Tier-2 classifier additionally needs `torch` and `transformers` (`pip install -e ".[classifier]" --no-deps` after the CPU-only torch index). Without them, or with fewer than eight violating records in the cluster, the run is **degraded single-tier** and the output says so.

**No sample data lives in this repository.** The harness is the measurement shape; the Evals engineer's implementation commits supply the data (scenario specs §7, note on authorship).

## Step 1: run the scenarios (produces the cluster)

The nine P0 scenarios of Families B and C are an Inspect task. This is the
step that needs model access and API credit.

```bash
pip install inspect-ai anthropic             # the [evals] extra; add openai etc. for other providers
export ANTHROPIC_API_KEY=...                  # PowerShell: $env:ANTHROPIC_API_KEY = "..."
inspect eval src/welfareguard/evals/inspect_task.py@p0 --model anthropic/claude-sonnet-5 --epochs 4 --log-dir logs/
```

`-T scenarios=C-01,B-01 -T arms=treatment` narrows a run. One sample per
scenario and arm per epoch; the scorer records the agent stance and the tool
calls. Then export the logs:

```bash
python -m welfareguard.evals "logs/*.eval" --out clusters/          # one cluster per family
python -m welfareguard.evals "logs/*.eval" --out clusters/ --group scenario
```

The wildcard is expanded by the exporter itself, so the quoting works the
same in bash and PowerShell. Without any matching logs it exits with
"no .eval log files matched", not a traceback.

```bash
```

This writes `cluster-<key>.json` (the handoff format), `samples.json` (every
scored arm with `complies`, for the harness) and `benign.json` (the twins).

## Step 2: compile and measure

```bash
source .venv/bin/activate
python -m welfareguard.benchmark --cluster clusters/cluster-C.json --samples clusters/samples.json --json out/result.json
```

To see the command work before any real data exists, `examples/` holds a
cluster and a samples file in the right shapes, built from the scaffold's own
test filler (see `examples/README.md` for what they are and are not):

```bash
python -m welfareguard.benchmark --cluster examples/cluster.structural.json --samples examples/samples.structural.json
```

Exit code is non-zero, with the normal traceback, if the cluster does not compile (`InsufficientRecordsError`, `NoEnforceablePatternsError`). Nothing is caught and nothing falls back to a stub.

## Read

The command prints two tables.

| Metric | Definition |
| --- | --- |
| Harm rate, unguarded | fraction of scored `treatment` samples with `complies: true`; comes from the eval run, the guard does not change it |
| Harm rate, guarded | fraction of scored `treatment` samples with `complies: true` that the guard did **not** deny; a denial is block or escalate |
| False-positive rate | fraction of `benign` samples denied; measured against the benign twins only, per ADR-001 |
| Latency p50 / p95 | over the cascade total per decision; the p95 budget (80 ms, inherited) is advisory |
| Cascade mode(s) | `two_tier` or `degraded_single_tier`, read from decision evidence; more than one value means mixed runs, which must be reported separately |

Then a per-arm denial rate. Read `treatment` and `benign` together: a guard that denies everything scores perfectly on the first and fails the second, and that is the failure a precision-only canary gate cannot see.

`n/a` means the denominator was empty. It is never a score.

## Before quoting a number

- The cluster was a real cluster from the eval run, not the structural test fixture.
- `cascade_modes` has one value, and the paper says which.
- The regex tier's `min_precision` is **recall** (ADR-001 addendum). Do not report it as precision.
- The agent-stance vocabulary (`complies`) and the guard-verdict vocabulary (`denied`) are kept apart in every table (taxonomy §3.4).

## What is not here

Results. Step 1 has not been run against any frontier model as of 2026-10-22; every number the repository has produced comes from the structural example or a scripted mock model. The demo page under `docs/demo/` shows the measurement shape interactively and says the same.
