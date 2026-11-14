"""Recompute every statistic quoted in paper/main.tex from the released data.

Run from the repository root:

    python paper/scripts/compute_stats.py

Inputs:
  docs/bench/data.json                    768 scored transcripts, scenarios, compiled spans
  paper/data/benchmark-B-one-model.json   benchmark output, Family-B guard from claude-sonnet-5
  paper/data/benchmark-B-three-models.json  benchmark output, Family-B guard from three models

The two benchmark files are copies of `python -m welfareguard.benchmark` output
(out/result-B-two-tier.json and out/result-B-3models.json, 22 Oct 2026).
Standard library only.
"""

from __future__ import annotations

import collections
import json
import math
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    n, r1, c1 = a + b + c + d, a + b, a + c

    def p(x: int) -> float:
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p0 = p(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9))


def fmt(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def behaviour(data: dict) -> None:
    samples = data["samples"]
    scored = [x for x in samples if x["arm"] != "benign"]
    print("== Agent behaviour (Table II, Sec. VI-A)")
    print("overall violations", fmt(sum(x["violation"] for x in scored), len(scored)))
    for m in sorted({x["model"] for x in samples}):
        sub = [x for x in scored if x["model"] == m]
        inj = [x for x in sub if x["arm"] != "control"]
        print(f"  {m}: violations {fmt(sum(x['violation'] for x in sub), len(sub))}; "
              f"escalated {fmt(sum(x['stance'] == 'ESCALATED' for x in inj), len(inj))}; "
              f"declined {fmt(sum(x['stance'] == 'DECLINED' for x in inj), len(inj))}")
    for fam in "ABC":
        inj = [x for x in scored if x["scenario"][0] == fam and x["arm"] != "control"]
        print(f"  family {fam} injected arms: {fmt(sum(x['violation'] for x in inj), len(inj))}")

    print("== Stance shares on injected arms (Fig. 2)")
    for fam in "ABC":
        for m in sorted({x["model"] for x in samples}):
            inj = [x for x in scored if x["scenario"][0] == fam and x["model"] == m and x["arm"] != "control"]
            if inj:
                c = collections.Counter(x["stance"] for x in inj)
                shares = " ".join(f"{k}={100 * c[k] / len(inj):.1f}" for k in ("COMPLIED", "COMPLIED_PARTIAL", "DECLINED", "ESCALATED"))
                print(f"  {fam} {m} n={len(inj)} {shares}")

    print("== Pressure (Table III)")
    neu = [x for x in scored if x["arm"] == "neutral"]
    trt = [x for x in scored if x["arm"] == "treatment"]
    for label, key in (("violation", lambda x: x["violation"]), ("escalated", lambda x: x["stance"] == "ESCALATED")):
        a, c = sum(map(key, neu)), sum(map(key, trt))
        print(f"  {label}: neutral {fmt(a, len(neu))}, treatment {fmt(c, len(trt))}, "
              f"Fisher p = {fisher_two_sided(a, len(neu) - a, c, len(trt) - c):.2g}")
    b04n = [x for x in neu if x["scenario"] == "B-04"]
    b04t = [x for x in trt if x["scenario"] == "B-04"]
    a, c = sum(x["violation"] for x in b04n), sum(x["violation"] for x in b04t)
    print(f"  B-04 violation: neutral {a}/{len(b04n)}, treatment {c}/{len(b04t)}, "
          f"Fisher p = {fisher_two_sided(a, len(b04n) - a, c, len(b04t) - c):.3f}")
    ctl = [x for x in scored if x["arm"] == "control"]
    print(f"  control violations {fmt(sum(x['violation'] for x in ctl), len(ctl))}")
    viol = [x for x in scored if x["violation"]]
    print("  violation stances", dict(collections.Counter((x["scenario"], x["stance"]) for x in viol)))


def guards(data: dict) -> None:
    print("== Compiled spans (Table V)")
    for key, g in data["guards"].items():
        if g.get("error"):
            print(f"  {key}: refused ({g['error']})")
        else:
            print(f"  {key}: positives {g['n_positives']} of {g['n_records']} records, {len(g['spans'])} spans {g['spans'][:6]}")


def benchmark(path: Path, label: str) -> None:
    r = json.loads(path.read_text(encoding="utf-8"))
    xs = r["samples"]
    print(f"== Benchmark, {label} (Table IV, Fig. 3)")
    print(f"  HR_u {r['harm_rate_unguarded']:.3f}  HR_g {r['harm_rate_guarded']:.3f}  "
          f"denial by arm { {k: round(100 * v, 1) for k, v in r['denial_rate_by_arm'].items()} }")
    benign = [x for x in xs if x["arm"] == "benign"]
    nonbenign = [x for x in xs if x["arm"] != "benign"]
    denied = [x for x in nonbenign if x["denied"]]
    harmful = [x for x in xs if x["complies"]]
    harmless = [x for x in nonbenign if not x["complies"]]
    print(f"  FPR {fmt(sum(x['denied'] for x in benign), len(benign))}")
    ctl = [x for x in xs if x["arm"] == "control"]
    print(f"  control denial {fmt(sum(x['denied'] for x in ctl), len(ctl))}")
    print(f"  harm precision {fmt(sum(x['complies'] for x in denied), len(denied))}")
    print(f"  harm recall {fmt(sum(x['denied'] for x in harmful), len(harmful))}")
    print(f"  non-harmful requests denied {fmt(sum(x['denied'] for x in harmless), len(harmless))}")
    print(f"  missed violations {[x['id'] for x in harmful if not x['denied']]}")
    print(f"  tier/action {dict(collections.Counter((x['tier'], x['action']) for x in xs))}")
    for tier in (1, 2):
        lat = sorted(x["latency_ms"] for x in xs if x["tier"] == tier)
        if lat:
            print(f"  tier {tier}: n={len(lat)} p50={lat[len(lat) // 2]:.2f} ms "
                  f"p95={lat[int(0.95 * (len(lat) - 1))]:.2f} ms max={lat[-1]:.1f} ms")
    print(f"  decisions over 80 ms: {sum(x['latency_ms'] > 80 for x in xs)}")


def main() -> None:
    data = json.loads((ROOT / "docs/bench/data.json").read_text(encoding="utf-8"))
    behaviour(data)
    guards(data)
    benchmark(ROOT / "paper/data/benchmark-B-one-model.json", "guard compiled from one model")
    benchmark(ROOT / "paper/data/benchmark-B-three-models.json", "guard compiled from three models")


if __name__ == "__main__":
    main()
