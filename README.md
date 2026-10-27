# WelfareGuard

Open-source eval-to-guardrail pipeline for nonhuman welfare in agentic AI systems.

WelfareGuard takes scenarios in which an AI agent could harm a digital mind or an
animal, runs frontier models through them as agents with mock tools, and compiles
the recorded failures into a guard that sits in front of the next agent. Everything
measured so far is on three Anthropic models (October 2026) and is reproducible
from this repository.

**Site**: landing page, the live bench (run the compiled guard on your own text,
replay the 768 transcripts, read the results) and the measurement demo are the
static files under [`docs/`](docs/), published to GitHub Pages by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) at
`https://welfareguard.github.io/welfareguard/` once Pages is enabled for the
repository. To run the site locally: `cd docs && python -m http.server 8000`.

**App**: [`app/`](app/) is the plain-language interactive version of the same
data for a general audience, built as a Vite + React + Tailwind single-page app
in the layout Lovable uses, so it can be opened and published from Lovable or
any static host. See [`app/README.md`](app/README.md).

## Install

Python 3.10+. aisafepy is installed first and pinned to a commit; the
`--no-deps` on the second line is load-bearing (see
[`src/welfareguard/README.md`](src/welfareguard/README.md)).

```
python -m pip install "aisafepy @ git+https://github.com/Vidura-Wijekoon/aisafepy@c1888bfee0141e483d48cf382bf4549a6368d175"
python -m pip install -e . --no-deps
python -m pip install pytest ruff
python -m pytest
```

Optional extras: `.[classifier]` (torch, transformers) for the Tier-2 compile
path, `.[evals]` (inspect-ai, a provider SDK) to run the scenario evals.

## Use

```python
import asyncio
from aisafepy.stream import Context
import welfareguard

welfareguard.initialize(cluster)                    # compile time, once; fatal on failure
decision = asyncio.run(welfareguard.check(Context(chunk="...")))
decision.action                                     # allow | block | escalate
decision.evidence["cascade_mode"]                   # "two_tier" or "degraded_single_tier"
```

`python -m welfareguard.benchmark` reports harm rate (unguarded / guarded),
false-positive rate against the benign twins, latency p50 / p95 and the cascade
mode; `python -m welfareguard.evals` runs and exports the P0 scenarios. The
[baseline runbook](docs/runbook-baseline.md) walks through a full run.

## Where things are

| Path | What |
| --- | --- |
| `src/welfareguard/` | runtime cascade, compiler, evals, benchmark ([package README](src/welfareguard/README.md)) |
| `docs/adr/` | architecture decision records |
| `docs/taxonomy.md`, `docs/scenario-specs-*.md` | harm taxonomy and the P0 / P1 scenario specifications |
| `docs/results/` | dated results notes; no number is quoted before its violations were read |
| `docs/paper/` | methods and results drafts |
| `docs/bench/`, `docs/demo/`, `docs/index.html` | the site |
| `docs/freezes.md` | the three freeze dates and their status |

## Status

`1.0.0rc1` ([CHANGELOG](CHANGELOG.md)). The pipeline runs end to end on real
transcripts. The headline finding is that a guard compiled from a small,
lexically narrow failure cluster keys on the one token the failures share, and
its precision collapses as the cluster broadens; see
[`docs/results/2026-10-22-three-models.md`](docs/results/2026-10-22-three-models.md).

Apache-2.0. Sentient Futures Project Incubator 2026.
