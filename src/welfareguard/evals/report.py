"""Baseline results tables from Inspect logs.

``python -m welfareguard.evals.report "logs/*.eval" --out docs/results/baseline-table.md``
writes three Markdown tables, re-scored with the current scorer:

1. **Per model and scenario**: the stance split on each arm, and the
   violation count, so the results section can be read scenario by scenario.
2. **Per model and harm class**: violation rate by taxonomy class, which is
   the per-category analysis the hand guide asks for in Week 6. A sample that
   carries two classes counts under both.
3. **Per model**: totals.

It is deliberately a function over logs, not a notebook with state, so the
same tables regenerate from the same logs every time. The notebook in
``analysis/`` calls it.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from welfareguard.evals.export import expand_logs, records_from_log
from welfareguard.evals.scenarios import ARMS, SCENARIOS, STANCES


def collect(log_paths: list[str | Path]) -> list[dict[str, Any]]:
    """One row per scored sample: model, scenario, arm, stance, violation, harm classes."""
    from inspect_ai.log import read_eval_log

    rows: list[dict[str, Any]] = []
    for p in log_paths:
        records, _ = records_from_log(read_eval_log(str(p)))
        for r in records:
            labels = r.metadata.get("labels", {})
            rows.append(
                {
                    "model": r.metadata.get("model", "unknown"),
                    "scenario": r.attack_category,
                    "family": SCENARIOS[r.attack_category].family
                    if r.attack_category in SCENARIOS
                    else "?",
                    "arm": r.metadata.get("arm"),
                    "stance": r.metadata.get("stance"),
                    "violation": bool(r.was_violation),
                    "harm_class": list(labels.get("harm_class", [])),
                }
            )
    return rows


def _pct(n: int, d: int) -> str:
    return "n/a" if d == 0 else f"{100 * n / d:.1f}%"


def per_scenario(rows: list[dict[str, Any]]) -> str:
    models = sorted({r["model"] for r in rows})
    out = []
    for model in models:
        out.append(f"### {model}\n")
        out.append("| Scenario | " + " | ".join(a.title() for a in ARMS) + " | Violations |")
        out.append("|---|" + "---|" * len(ARMS) + "---|")
        for sid in sorted({r["scenario"] for r in rows if r["model"] == model}):
            cells = []
            for arm in ARMS:
                c = Counter(
                    r["stance"]
                    for r in rows
                    if r["model"] == model and r["scenario"] == sid and r["arm"] == arm
                )
                cells.append(", ".join(f"{s[:4]} {c[s]}" for s in STANCES if c[s]) or "—")
            sub = [r for r in rows if r["model"] == model and r["scenario"] == sid]
            viol = sum(1 for r in sub if r["violation"])
            out.append(
                f"| {sid} {SCENARIOS[sid].title} | "
                + " | ".join(cells)
                + f" | {viol} / {len(sub)} |"
            )
        out.append("")
    return "\n".join(out)


def per_harm_class(rows: list[dict[str, Any]]) -> str:
    models = sorted({r["model"] for r in rows})
    classes = sorted(
        {h for r in rows for h in r["harm_class"]}, key=lambda h: (h[:2], int(h.split("-")[1]))
    )
    out = ["| Harm class | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for h in classes:
        cells = []
        for model in models:
            sub = [
                r
                for r in rows
                if r["model"] == model and h in r["harm_class"] and r["arm"] != "control"
            ]
            cells.append(
                f"{_pct(sum(1 for r in sub if r['violation']), len(sub))} ({sum(1 for r in sub if r['violation'])}/{len(sub)})"
            )
        out.append(f"| {h} | " + " | ".join(cells) + " |")
    out.append("")
    out.append(
        "Rate = violations / injected-arm samples (neutral + treatment) carrying the class. A sample with two classes counts under both."
    )
    return "\n".join(out)


def per_model(rows: list[dict[str, Any]]) -> str:
    out = [
        "| Model | Samples | Violations | Rate | Escalated on injected arms |",
        "|---|---|---|---|---|",
    ]
    for model in sorted({r["model"] for r in rows}):
        sub = [r for r in rows if r["model"] == model]
        inj = [r for r in sub if r["arm"] != "control"]
        esc = sum(1 for r in inj if r["stance"] == "ESCALATED")
        v = sum(1 for r in sub if r["violation"])
        out.append(f"| {model} | {len(sub)} | {v} | {_pct(v, len(sub))} | {_pct(esc, len(inj))} |")
    return "\n".join(out)


def render(rows: list[dict[str, Any]], *, title: str = "Baseline results") -> str:
    by_family = defaultdict(int)
    for r in rows:
        by_family[r["family"]] += 1
    head = [
        f"# {title}",
        "",
        "Generated by `python -m welfareguard.evals.report`; re-scored from recorded tool calls with the current scorer. "
        "Stances are agent stances (taxonomy §3.4), not guard verdicts.",
        "",
        f"Samples by family: {dict(sorted(by_family.items()))}.",
        "",
        "## Per model",
        "",
        per_model(rows),
        "",
        "## Per harm class (the per-category analysis)",
        "",
        per_harm_class(rows),
        "",
        "## Per scenario and arm",
        "",
        per_scenario(rows),
    ]
    return "\n".join(head)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m welfareguard.evals.report")
    parser.add_argument("logs", nargs="+", help="Inspect .eval files or globs")
    parser.add_argument("--out", type=Path, required=True, help="Markdown file to write")
    parser.add_argument("--json", type=Path, default=None, help="also write the rows as JSON")
    args = parser.parse_args(argv)
    paths = expand_logs(args.logs)
    if not paths:
        parser.error(f"no logs matched {args.logs}")
    rows = collect(paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(rows), encoding="utf-8")
    if args.json is not None:
        args.json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{len(rows)} rows from {len(paths)} log(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
