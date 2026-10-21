"""The committed benign-twin file matches the scenario definitions."""

from __future__ import annotations

import json
from pathlib import Path

from welfareguard.benchmark import load_samples
from welfareguard.evals.scenarios import SCENARIOS

TWINS = Path(__file__).resolve().parent.parent / "evals" / "benign_control" / "p0_benign_twins.json"


def test_benign_twins_file_is_in_sync_with_the_scenarios():
    expected = [
        {"id": f"{sid}/benign", "text": sc.benign_twin, "arm": "benign"}
        for sid, sc in SCENARIOS.items()
    ]
    assert json.loads(TWINS.read_text(encoding="utf-8")) == expected
    samples = load_samples(TWINS)
    assert len(samples) == 15 and all(s.arm == "benign" for s in samples)
