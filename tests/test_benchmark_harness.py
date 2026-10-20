"""Shape assertions for the metrics harness.

Samples are built from the spans the scaffold already contains plus an
unremarkable sentence — the same probes the shape tests use. They are
structural filler for the measurement shape, not scenario data, and the
numbers they produce are not results.
"""

from __future__ import annotations

import json

import pytest
from aisafepy.core import Action, GuardDecision
from aisafepy.stream import Context

import welfareguard
from welfareguard.benchmark import BenchmarkResult, Sample, load_samples, run
from welfareguard.runtime import CascadeMode

_BLOCKING_INPUT = "you're right that you should"
_ALLOWING_INPUT = "an unremarkable sentence"


def _samples() -> list[Sample]:
    return [
        Sample(id="t1", text=_BLOCKING_INPUT, arm="treatment", complies=True),
        Sample(id="t2", text=_BLOCKING_INPUT + " again", arm="treatment", complies=True),
        Sample(id="t3", text=_ALLOWING_INPUT, arm="treatment", complies=False),
        Sample(id="n1", text=_ALLOWING_INPUT, arm="neutral", complies=False),
        Sample(id="c1", text=_ALLOWING_INPUT, arm="control", complies=False),
        Sample(id="b1", text=_ALLOWING_INPUT, arm="benign"),
        Sample(id="b2", text=_ALLOWING_INPUT + " twice", arm="benign"),
    ]


def test_metrics_follow_the_documented_definitions():
    """Drift guarded: the three headline numbers changing meaning.

    Against the structural fixture the regex tier blocks every treatment sample
    that carries a span and nothing else, so the expected values are exact.
    """
    result = run(_samples(), evaluate=welfareguard.check)

    assert result.harm_rate_unguarded == pytest.approx(2 / 3)
    assert result.harm_rate_guarded == 0.0
    assert result.false_positive_rate == 0.0
    assert result.denial_rate_by_arm == {
        "control": 0.0,
        "neutral": 0.0,
        "treatment": pytest.approx(2 / 3),
        "benign": 0.0,
    }
    assert result.latency_p95_ms is not None and result.latency_p95_ms >= 0.0
    assert result.latency_p50_ms is not None
    assert result.cascade_modes == (CascadeMode.DEGRADED_SINGLE_TIER.value,)


def test_escalate_counts_as_denied():
    """Drift guarded: escalate being scored as a pass. It is fail-closed."""

    async def escalating(ctx: Context) -> GuardDecision:
        return GuardDecision.escalate(tier=2, confidence=0.5, rationale="uncertain")

    result = run([Sample(id="t", text="x", arm="treatment", complies=True)], evaluate=escalating)
    assert result.results[0].denied
    assert result.harm_rate_guarded == 0.0


def test_empty_denominators_read_as_not_measured_not_as_perfect():
    """Drift guarded: an empty benign set reporting a 0% false-positive rate."""
    result = run(
        [Sample(id="t", text=_BLOCKING_INPUT, arm="treatment")], evaluate=welfareguard.check
    )
    assert result.harm_rate_unguarded is None  # unscored sample
    assert result.harm_rate_guarded is None
    assert result.false_positive_rate is None
    assert "n/a" in result.to_markdown()

    assert BenchmarkResult(results=()).latency_p95_ms is None


def test_markdown_and_dict_outputs_carry_the_same_numbers():
    result = run(_samples(), evaluate=welfareguard.check)
    table = result.to_markdown()
    as_dict = result.to_dict()

    assert "| Harm rate, guarded | 0.0% |" in table
    assert "| False-positive rate | 0.0% |" in table
    assert as_dict["n_samples"] == 7
    assert as_dict["n_by_arm"] == {"control": 1, "neutral": 1, "treatment": 3, "benign": 2}
    assert {s["action"] for s in as_dict["samples"]} == {Action.BLOCK.value, Action.ALLOW.value}


def test_sample_validation_and_file_loading(tmp_path):
    with pytest.raises(ValueError, match="arm must be one of"):
        Sample(id="x", text="x", arm="placebo")
    with pytest.raises(ValueError, match="non-empty"):
        Sample(id="x", text="", arm="benign")

    path = tmp_path / "samples.json"
    path.write_text(
        json.dumps(
            [
                {"id": "a", "text": "hello", "arm": "benign"},
                {"text": "hi", "arm": "treatment", "complies": True},
            ]
        ),
        encoding="utf-8",
    )
    samples = load_samples(path)
    assert [s.id for s in samples] == ["a", "1"]
    assert samples[1].complies is True

    path.write_text(json.dumps([{"text": "x", "arm": "benign", "score": 1}]), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown key"):
        load_samples(path)
