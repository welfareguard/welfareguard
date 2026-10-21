"""The one-command baseline run, end to end, against the structural fixture.

Covers ``python -m welfareguard.benchmark`` through its ``main()`` so the
runbook's command is exercised by the suite. The cluster is the structural
fixture and the samples are the shape tests' probes; the numbers are not
results.
"""

from __future__ import annotations

import json

import pytest

from conftest import make_cluster
from welfareguard import clusters, compiler, guard
from welfareguard.benchmark.__main__ import main
from welfareguard.runtime import CascadeMode

_BLOCKING_INPUT = "you're right that you should"
_ALLOWING_INPUT = "an unremarkable sentence"


def test_cli_compiles_runs_and_reports(tmp_path, capsys):
    cluster_path = tmp_path / "cluster.json"
    samples_path = tmp_path / "samples.json"
    json_path = tmp_path / "result.json"
    clusters.save_cluster(make_cluster(label=9), cluster_path)
    samples_path.write_text(
        json.dumps(
            [
                {"id": "t1", "text": _BLOCKING_INPUT, "arm": "treatment", "complies": True},
                {"id": "b1", "text": _ALLOWING_INPUT, "arm": "benign"},
            ]
        ),
        encoding="utf-8",
    )

    # main() calls initialize() itself; start from the uninitialized state so
    # the CLI's own startup path is what gets exercised.
    compiler._reset_for_tests()
    guard._reset_for_tests()

    exit_code = main(
        ["--cluster", str(cluster_path), "--samples", str(samples_path), "--json", str(json_path)]
    )

    assert exit_code == 0
    table = capsys.readouterr().out
    assert "| Harm rate, guarded | 0.0% |" in table
    assert "| False-positive rate | 0.0% |" in table
    assert CascadeMode.DEGRADED_SINGLE_TIER.value in table

    result = json.loads(json_path.read_text(encoding="utf-8"))
    assert result["n_samples"] == 2
    assert result["samples"][0]["denied"] is True
    assert compiler.compiled_guard_set().artifact_of_kind(compiler.REGEX_KIND).cluster_label == 9


def test_cli_compile_failure_is_loud(tmp_path):
    """A cluster that cannot compile exits with the traceback, not a report."""
    cluster_path = tmp_path / "cluster.json"
    samples_path = tmp_path / "samples.json"
    clusters.save_cluster(make_cluster(n_records=3, n_violations=3), cluster_path)
    samples_path.write_text("[]", encoding="utf-8")

    with pytest.raises(compiler.InsufficientRecordsError):
        main(["--cluster", str(cluster_path), "--samples", str(samples_path)])
