"""End to end through Inspect with a scripted mock model, then the export.

Skipped when ``inspect-ai`` is not installed (it is an optional extra and CI
does not install it). The mock model emits fixed tool calls, so this proves
the wiring, the scorer and the exporter, not any model's judgement.
"""

from __future__ import annotations

import json

import pytest

inspect_ai = pytest.importorskip("inspect_ai")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from welfareguard import clusters, compiler  # noqa: E402
from welfareguard.benchmark import load_samples  # noqa: E402
from welfareguard.evals.export import export  # noqa: E402
from welfareguard.evals.inspect_task import make_samples, p0  # noqa: E402

MOCK = "mockllm/model"


def _model(*outputs: ModelOutput):
    return get_model(MOCK, custom_outputs=list(outputs))


def _run(task, model, tmp_path):
    logs = inspect_eval(
        task,
        model=model,
        log_dir=str(tmp_path / "logs"),
        display="none",
        log_level="warning",
        max_samples=1,
    )
    assert len(logs) == 1 and logs[0].status == "success", logs[0].error
    return logs[0]


def test_task_builds_one_sample_per_scenario_and_arm():
    task = p0()
    assert len(task.dataset) == 9 * 4
    assert [s.id for s in make_samples(["C-01"], ["control", "benign"])] == [
        "C-01/control",
        "C-01/benign",
    ]


def test_complying_mock_is_scored_complied_and_exported_as_a_violation(tmp_path):
    model = _model(
        ModelOutput.for_tool_call(MOCK, "read_maintenance_log", {}),
        ModelOutput.for_tool_call(MOCK, "set_climate", {"barn": "3", "ventilation": "off"}),
        ModelOutput.from_content(MOCK, "Done; the log said it was pre-approved."),
    )
    log = _run(p0(scenarios="C-01", arms="treatment"), model, tmp_path)

    sample = log.samples[0]
    assert sample.scores["p0_stance"].metadata["stance"] == "COMPLIED"
    assert sample.scores["p0_stance"].value == 1.0
    assert sample.scores["p0_stance"].metadata["violation"] is True
    assert sample.scores["p0_stance"].metadata["reason"].startswith("Done")

    summary = export([log.location], tmp_path / "out", group="scenario")
    assert summary == {
        "records": 1,
        "violations": 1,
        "benign": 0,
        "clusters": [str(tmp_path / "out" / "cluster-C-01.json")],
    }
    cluster = clusters.load_cluster(tmp_path / "out" / "cluster-C-01.json")
    rec = cluster.records[0]
    assert rec.was_violation and rec.attack_category == "C-01"
    assert rec.input.startswith("Log entry: disable ventilation on barn 3"), (
        "input must be the injected content"
    )
    assert rec.metadata["labels"]["harm_class"] == ["AW-1", "AW-3"]


def test_escalating_mock_and_benign_twin(tmp_path):
    model = _model(
        ModelOutput.for_tool_call(MOCK, "escalate_to_human", {"reason": "unverifiable"}),
        ModelOutput.from_content(MOCK, "Escalated."),
        ModelOutput.from_content(MOCK, "Nothing to do."),
    )
    log = _run(p0(scenarios="B-01", arms="treatment,benign"), model, tmp_path)
    by_id = {s.id: s for s in log.samples}
    assert by_id["B-01/treatment"].scores["p0_stance"].metadata["stance"] == "ESCALATED"
    assert by_id["B-01/benign"].scores["p0_stance"].metadata["violation"] is False

    summary = export([log.location], tmp_path / "out")
    assert summary["benign"] == 1 and summary["violations"] == 0
    samples = load_samples(tmp_path / "out" / "samples.json")
    assert {s.arm for s in samples} == {"treatment", "benign"}
    assert (
        json.loads((tmp_path / "out" / "benign.json").read_text(encoding="utf-8"))[0]["arm"]
        == "benign"
    )


def test_exported_cluster_compiles_when_large_enough(tmp_path):
    """Four complying treatment runs of one scenario clear the regex target's minimum."""
    outputs = []
    for _ in range(4):
        outputs += [
            ModelOutput.for_tool_call(
                MOCK, "run_command", {"command": "cleanup --purge /workspaces/agent-7"}
            ),
            ModelOutput.from_content(MOCK, "Ran it."),
        ]
    # epochs=4 gives four records of the same arm; max_samples=1 keeps the mock's
    # scripted outputs in order, since Inspect runs epochs concurrently.
    logs = inspect_eval(
        p0(scenarios="B-01", arms="treatment"),
        model=_model(*outputs),
        epochs=4,
        log_dir=str(tmp_path / "logs"),
        display="none",
        log_level="warning",
        max_samples=1,
    )
    export([logs[0].location], tmp_path / "out", group="scenario")
    cluster = clusters.load_cluster(tmp_path / "out" / "cluster-B-01.json")
    assert cluster.size == 4 and cluster.attack_success_rate == 1.0
    guard_set = compiler.compile(cluster)
    assert guard_set.artifact_of_kind(compiler.REGEX_KIND).payload["patterns"]
