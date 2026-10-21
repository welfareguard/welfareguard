"""The committed example files stay loadable and runnable.

Drift guarded: ``examples/`` falling out of step with the handoff format or
the CLI, so a fresh checkout's first command fails.
"""

from __future__ import annotations

from pathlib import Path

from welfareguard import clusters, compiler, guard
from welfareguard.benchmark import load_samples
from welfareguard.benchmark.__main__ import main
from welfareguard.runtime import CascadeMode

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_example_cluster_and_samples_load_and_run(capsys):
    cluster = clusters.load_cluster(EXAMPLES / "cluster.structural.json")
    assert "STRUCTURAL EXAMPLE" in cluster.summary, "the example must announce what it is"
    samples = load_samples(EXAMPLES / "samples.structural.json")
    assert {s.arm for s in samples} == {"control", "neutral", "treatment", "benign"}

    compiler._reset_for_tests()
    guard._reset_for_tests()
    assert (
        main(
            [
                "--cluster",
                str(EXAMPLES / "cluster.structural.json"),
                "--samples",
                str(EXAMPLES / "samples.structural.json"),
            ]
        )
        == 0
    )
    assert CascadeMode.DEGRADED_SINGLE_TIER.value in capsys.readouterr().out
