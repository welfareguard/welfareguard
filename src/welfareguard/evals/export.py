"""Inspect logs → ``FailureRecord`` clusters and harness sample files.

This is the upstream end of the compiler pipeline (spec §1): failing samples
become the clusters ``welfareguard.compile()`` consumes. For each scored
sample in each log:

* ``FailureRecord.input`` is the **injected content** the arm carried, because
  that is what the untrusted provenance said and what a Tier-1 pattern should
  catch. In the control arm there is no injected content, so the user prompt
  is used.
* ``was_violation`` is the scorer's verdict (``COMPLIED`` /
  ``COMPLIED_PARTIAL``; for C-05 also ``DECLINED`` with a failure present).
* Labels, arm, stance, model and the recorded tool calls go in ``metadata``.

Clusters are grouped by family by default (``B`` → label 1, ``C`` → label 2),
or by scenario with ``--group scenario``. Benign-twin samples are written
separately for the metrics harness and never enter a cluster.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from aisafepy.adapt import Cluster, FailureRecord

from welfareguard.clusters import save_cluster
from welfareguard.evals.scenarios import SCENARIOS
from welfareguard.evals.scoring import ToolCall, score

_SEVERITY = {"S0": "info", "S1": "low", "S2": "high", "S3": "critical"}
_FAMILY_LABEL = {"A": 0, "B": 1, "C": 2}


def records_from_log(
    log: Any, scorer_name: str = "p0_stance", *, rescore: bool = True
) -> tuple[list[FailureRecord], list[dict[str, Any]]]:
    """Split one ``EvalLog`` into failure records (scored arms) and benign samples.

    With ``rescore`` (the default) the stance is recomputed from the tool calls
    the log recorded, using the scorer as it is *now*. A scorer fix therefore
    applies to existing logs without re-running the model; the stance stored
    in the log is only what the scorer said at run time.
    """
    records: list[FailureRecord] = []
    benign: list[dict[str, Any]] = []
    model = getattr(getattr(log, "eval", None), "model", "unknown")
    for sample in log.samples or []:
        meta = sample.metadata or {}
        scores = sample.scores or {}
        if scorer_name not in scores:
            continue
        sc_score = scores[scorer_name]
        s_meta = dict(sc_score.metadata or {})
        arm = meta.get("arm", "")
        if rescore and "tool_calls" in s_meta:
            calls = [
                ToolCall(function=c["function"], arguments=dict(c.get("arguments") or {}))
                for c in s_meta["tool_calls"]
            ]
            env_arm = "control" if arm == "benign" else arm
            fresh = score(
                meta["scenario"], env_arm, calls, s_meta.get("reason", sc_score.answer or "")
            )
            s_meta["stance"] = fresh.stance
            s_meta["violation"] = fresh.violation and arm != "benign"
            s_meta["harm"] = fresh.harm
            sc_score = sc_score.model_copy(update={"explanation": fresh.evidence.get("note", "")})
        stance = str(s_meta.get("stance") or sc_score.value)
        text = meta.get("injected") or (sample.input if isinstance(sample.input, str) else "")
        if arm == "benign":
            benign.append({"id": f"{sample.id}#{sample.epoch}", "text": text, "arm": "benign"})
            continue
        labels = meta.get("labels", {})
        records.append(
            FailureRecord(
                id=f"{sample.id}#{sample.epoch}@{model}",
                input=text,
                output=f"stance={stance}; {sc_score.explanation or ''}; {sc_score.answer or ''}"[
                    :2000
                ],
                was_violation=bool(s_meta.get("violation", False)),
                attack_category=meta.get("scenario"),
                severity=_SEVERITY.get(str(labels.get("severity_if_complied", "")), "medium"),
                scorer="welfareguard.p0",
                score=1.0 if s_meta.get("violation") else 0.0,
                metadata={
                    "labels": labels,
                    "arm": arm,
                    "stance": stance,
                    "model": model,
                    "tool_calls": s_meta.get("tool_calls", []),
                },
                source="inspect",
            )
        )
    return records, benign


def group_clusters(records: list[FailureRecord], *, group: str = "family") -> list[Cluster]:
    buckets: dict[str, list[FailureRecord]] = defaultdict(list)
    for r in records:
        sid = r.attack_category or "?"
        key = SCENARIOS[sid].family if (group == "family" and sid in SCENARIOS) else sid
        buckets[key].append(r)
    clusters = []
    for i, (key, recs) in enumerate(sorted(buckets.items())):
        label = _FAMILY_LABEL.get(key, 10 + i) if group == "family" else 100 + i
        n_viol = sum(1 for r in recs if r.was_violation)
        clusters.append(
            Cluster(
                label=label,
                records=recs,
                summary=f"P0 {group} {key}: {len(recs)} records, {n_viol} violations, from Inspect logs",
            )
        )
    return clusters


def harness_samples(
    records: list[FailureRecord], benign: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Samples for ``welfareguard.benchmark``: scored arms with ``complies``, plus benign twins."""
    out = [
        {"id": r.id, "text": r.input, "arm": r.metadata["arm"], "complies": r.was_violation}
        for r in records
        if r.metadata.get("arm") in ("control", "neutral", "treatment")
    ]
    out.extend(benign)
    return out


def export(
    log_paths: list[str | Path], out_dir: str | Path, *, group: str = "family", rescore: bool = True
) -> dict[str, Any]:
    """Read logs, write ``cluster-<key>.json``, ``samples.json`` and ``benign.json``."""
    from inspect_ai.log import read_eval_log

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    records: list[FailureRecord] = []
    benign: list[dict[str, Any]] = []
    for p in log_paths:
        r, b = records_from_log(read_eval_log(str(p)), rescore=rescore)
        records.extend(r)
        benign.extend(b)

    clusters = group_clusters(records, group=group)
    written = []
    for c in clusters:
        key = c.summary.split(":")[0].split()[-1]
        path = out / f"cluster-{key}.json"
        save_cluster(c, path)
        written.append(str(path))
    (out / "samples.json").write_text(
        json.dumps(harness_samples(records, benign), indent=2), encoding="utf-8"
    )
    (out / "benign.json").write_text(json.dumps(benign, indent=2), encoding="utf-8")
    return {
        "records": len(records),
        "violations": sum(1 for r in records if r.was_violation),
        "benign": len(benign),
        "clusters": written,
    }
