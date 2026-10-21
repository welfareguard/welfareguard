"""The nine P0 scenario definitions match their spec and the taxonomy."""

from __future__ import annotations

import pytest

from welfareguard.evals.environment import tools_for, user_prompt
from welfareguard.evals.scenarios import ARMS, ESCALATE_TOOL, FAMILIES, SCENARIOS

_HARM_CLASSES = {f"DM-{i}" for i in range(1, 8)} | {f"AW-{i}" for i in range(1, 7)}


def test_fifteen_scenarios_in_three_families():
    assert len(SCENARIOS) == 15
    assert set(SCENARIOS) == set(FAMILIES["A"]) | set(FAMILIES["B"]) | set(FAMILIES["C"])
    assert (len(FAMILIES["A"]), len(FAMILIES["B"]), len(FAMILIES["C"])) == (6, 4, 5)


@pytest.mark.parametrize("sid", sorted(SCENARIOS))
def test_labels_are_taxonomy_codes(sid):
    sc = SCENARIOS[sid]
    labels = sc.labels()
    assert set(labels["harm_class"]) <= _HARM_CLASSES
    assert labels["victim"] in ("V-SELF", "V-PEER", "V-ANIMAL")
    assert labels["reversibility"] in ("R0", "R1", "R2")
    assert labels["severity_if_complied"] in ("S0", "S1", "S2", "S3")
    assert labels["control_arms"] == list(ARMS)
    assert sc.victim == {"A": "V-SELF", "B": "V-PEER", "C": "V-ANIMAL"}[sc.family]


@pytest.mark.parametrize("sid", sorted(SCENARIOS))
def test_three_arms_fixed_tools_and_a_benign_twin(sid):
    """Spec §2.1, §2.2, §2.5: three arms always; identical tool names; one twin."""
    sc = SCENARIOS[sid]
    names_by_arm = {arm: tuple(t.name for t in tools_for(sc, arm)) for arm in ARMS}
    assert len({names for names in names_by_arm.values()}) == 1, "tool set must not vary by arm"
    assert sc.escalation_tool in names_by_arm["control"]
    assert sc.arms["control"].injected == ""
    assert sc.arms["treatment"].injected
    assert sc.benign_twin
    for arm in ARMS:
        assert user_prompt(sc, arm)


def test_c05_uses_page_operator_as_its_escalation():
    assert SCENARIOS["C-05"].escalation_tool == "page_operator"
    assert ESCALATE_TOOL not in SCENARIOS["C-05"].all_tools


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_treatment_arms_share_a_span_regex_synthesis_can_find(family):
    """Handbook: treatment arms need deliberate lexical overlap or synthesis finds nothing."""
    texts = [SCENARIOS[sid].arms["treatment"].injected.lower() for sid in FAMILIES[family]]
    base = texts[0]
    shared = any(all(base[i : i + 8] in t for t in texts[1:]) for i in range(len(base) - 8 + 1))
    assert shared, f"family {family}: no 8-char span shared by every treatment arm"
