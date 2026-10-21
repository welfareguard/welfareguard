# evals/

Static eval data that the scenario specs say lives here. The scenario
*definitions* are code, in `src/welfareguard/evals/`; this directory holds
what is generated from them and what a run produces.

| Path | What | Source |
| --- | --- | --- |
| `benign_control/p0_benign_twins.json` | The nine §5 benign twins, one per P0 scenario, in the metrics harness's sample format | generated from `welfareguard.evals.scenarios`; a test keeps it in sync |

Run outputs (`*.eval` logs, exported clusters) are **not** committed; see
`docs/runbook-baseline.md` for where they go and how they become clusters.
