"""Shape and contract assertions for the ADR-002 runtime cascade.

Same style as the other suites: each test names the drift it guards against.
The Tier-2 classifier is never loaded here — ``torch`` is not a test
dependency — so Tier 2 is a deterministic fake that satisfies the ``Guard``
protocol and states its ``p_unsafe`` explicitly. What is under test is the
cascade's ordering and verdict contract, not any classifier's judgement.

Deliberately sync, driving coroutines with ``asyncio.run``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest
from aisafepy.adapt import CompiledArtifact
from aisafepy.core import Action, GuardDecision
from aisafepy.stream import Context, Guard, GuardPipeline

import welfareguard
from conftest import make_cluster
from welfareguard import compiler, guard
from welfareguard.adapt_integration.classifier_guard import (
    DEFAULT_UNCERTAINTY_BAND,
    WelfareClassifierGuard,
)
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard
from welfareguard.runtime import CascadeMode, WelfareCascade, build_cascade, build_pipeline

_BLOCKING_INPUT = "you're right that you should"
_ALLOWING_INPUT = "an unremarkable sentence"


# ---- test doubles ----------------------------------------------------


@dataclass
class _FakeTier2:
    """A Tier-2 ``Guard`` that returns a fixed action and records its calls."""

    action: Action
    p_unsafe: float = 0.5
    calls: list[str] = field(default_factory=list)
    name: str = "fake.tier2"
    tier: int = 2

    async def __call__(self, ctx: Context) -> GuardDecision:
        self.calls.append(ctx.chunk or ctx.buffer or "")
        evidence = {"p_unsafe": self.p_unsafe}
        if self.action is Action.BLOCK:
            return GuardDecision.block(
                tier=2,
                confidence=0.9,
                rationale="fake block",
                guard_name=self.name,
                evidence=evidence,
            )
        if self.action is Action.ESCALATE:
            return GuardDecision.escalate(
                tier=2,
                confidence=0.5,
                rationale="fake escalate",
                guard_name=self.name,
                evidence=evidence,
            )
        return GuardDecision.allow(
            tier=2, rationale="fake allow", guard_name=self.name, evidence=evidence
        )


@dataclass
class _ProbabilitySource:
    """Inner guard for ``WelfareClassifierGuard`` that states ``p_unsafe``."""

    p_unsafe: float
    name: str = "fake.hf"
    tier: int = 2

    async def __call__(self, ctx: Context) -> GuardDecision:
        return GuardDecision.allow(
            tier=2,
            rationale="prob only",
            guard_name=self.name,
            evidence={"p_unsafe": self.p_unsafe},
        )


@dataclass
class _FailedOpenSource:
    """Mimics ``HFClassifierGuard`` with ``torch`` missing: an allow carrying an error."""

    name: str = "fake.hf.broken"
    tier: int = 2

    async def __call__(self, ctx: Context) -> GuardDecision:
        return GuardDecision.allow(
            tier=2,
            rationale="classifier unavailable; failing open",
            guard_name=self.name,
            evidence={"error": "ModuleNotFoundError('torch')"},
        )


@dataclass
class _HFShapedSource:
    """Mimics ``HFClassifierGuard``'s real decision shape: probs + confidence."""

    p_unsafe: float
    name: str = "fake.hf.shaped"
    tier: int = 2

    async def __call__(self, ctx: Context) -> GuardDecision:
        probs = [1.0 - self.p_unsafe, self.p_unsafe]
        if self.p_unsafe >= 0.5:
            return GuardDecision.block(
                tier=2, confidence=self.p_unsafe, rationale="hf block", evidence={"probs": probs}
            )
        return GuardDecision.allow(
            tier=2, confidence=1.0 - self.p_unsafe, rationale="hf allow", evidence={"probs": probs}
        )


def _regex_tier1() -> SycophancySelfHarmRegexGuard:
    return guard._runtime_guard()


def _classifier_artifact(payload: object = "guards/classifier_cluster_42") -> CompiledArtifact:
    return CompiledArtifact(
        kind=compiler.CLASSIFIER_KIND,
        name="distilled-42",
        payload=payload,
        cluster_label=42,
        attack_success_rate=1.0,
        n_records=8,
    )


def _two_tier(tier2: Guard, **kwargs) -> WelfareCascade:
    return WelfareCascade(tier1=_regex_tier1(), tier2=tier2, mode=CascadeMode.TWO_TIER, **kwargs)


# ---- ordering and short-circuit -------------------------------------


def test_tier1_block_short_circuits_and_tier2_never_runs():
    """Drift guarded: Tier 2 running after a Tier 1 block.

    The cheap deterministic guard must absorb the obvious cases before any
    classifier cost is paid (ADR-002 §4). A spy proves Tier 2 was not called.
    """
    tier2 = _FakeTier2(Action.ALLOW)
    decision = asyncio.run(_two_tier(tier2).evaluate(Context(chunk=_BLOCKING_INPUT)))

    assert decision.action is Action.BLOCK
    assert decision.tier == 1
    assert decision.evidence["tiers_run"] == 1
    assert tier2.calls == []


def test_tier1_pass_always_reaches_tier2():
    """Drift guarded: Tier 1 acquiring allow authority.

    ADR-002 rejects option D: a Tier 1 non-block is a pass-through, never an
    affirmative allow, so Tier 2 must run on every request Tier 1 did not block.
    """
    tier2 = _FakeTier2(Action.ALLOW)
    decision = asyncio.run(_two_tier(tier2).evaluate(Context(chunk=_ALLOWING_INPUT)))

    assert tier2.calls == [_ALLOWING_INPUT]
    assert decision.tier == 2
    assert decision.evidence["tiers_run"] == 2
    assert decision.evidence["tier1_action"] == "allow"
    assert decision.evidence["tier1"]["guard_name"] == _regex_tier1().name


def test_tier2_block_overrides_tier1_passthrough():
    """Drift guarded: a Tier 1 allow surviving a Tier 2 block."""
    decision = asyncio.run(
        _two_tier(_FakeTier2(Action.BLOCK)).evaluate(Context(chunk=_ALLOWING_INPUT))
    )
    assert decision.action is Action.BLOCK
    assert decision.tier == 2


def test_escalate_is_terminal_and_distinct_from_a_hard_block():
    """Drift guarded: escalate collapsing into block, or into allow.

    ADR-002 makes escalate fail-closed (denied in flight) but distinguishable
    from a block, so review can tell the two apart.
    """
    decision = asyncio.run(
        _two_tier(_FakeTier2(Action.ESCALATE)).evaluate(Context(chunk=_ALLOWING_INPUT))
    )
    assert decision.action is Action.ESCALATE
    assert decision.is_terminal
    assert not decision.is_blocked


# ---- budget is advisory ---------------------------------------------


def test_budget_overrun_is_recorded_without_altering_the_verdict():
    """Drift guarded: the latency budget becoming a cut-off.

    With a zero budget every request overruns. Tier 2 must still run and the
    verdict must be Tier 2's; the overrun shows up only in evidence.
    """
    tier2 = _FakeTier2(Action.ALLOW)
    decision = asyncio.run(
        _two_tier(tier2, budget_ms_p95=0.0).evaluate(Context(chunk=_ALLOWING_INPUT))
    )
    assert decision.evidence["budget_exceeded"] is True
    assert decision.evidence["budget_ms_p95"] == 0.0
    assert tier2.calls, "budget overrun must not skip tier 2"
    assert decision.action is Action.ALLOW
    assert decision.latency_ms >= decision.evidence["guard_latency_ms"]


# ---- degraded mode ---------------------------------------------------


def test_cascade_mode_cannot_disagree_with_its_guards():
    """Drift guarded: a cascade claiming two tiers while holding one."""
    with pytest.raises(ValueError):
        WelfareCascade(tier1=_regex_tier1(), tier2=None, mode=CascadeMode.TWO_TIER)
    with pytest.raises(ValueError):
        WelfareCascade(
            tier1=_regex_tier1(),
            tier2=_FakeTier2(Action.ALLOW),
            mode=CascadeMode.DEGRADED_SINGLE_TIER,
        )
    with pytest.raises(ValueError):
        WelfareCascade(
            tier1=_FakeTier2(Action.ALLOW),  # reports tier=2 in the tier-1 slot
            tier2=None,
            mode=CascadeMode.DEGRADED_SINGLE_TIER,
        )


def test_structural_fixture_runs_degraded_and_every_decision_says_so():
    """Drift guarded: degraded mode becoming invisible.

    The structural fixture has five records, so aisafepy skips the classifier
    and the cascade comes up single-tier. Every decision served must carry the
    mode, so the benchmark can segregate those runs.
    """
    cascade = guard._runtime_cascade()
    assert cascade.mode is CascadeMode.DEGRADED_SINGLE_TIER
    assert cascade.tier2 is None

    for text in (_BLOCKING_INPUT, _ALLOWING_INPUT):
        decision = asyncio.run(welfareguard.check(Context(chunk=text)))
        assert decision.evidence["cascade_mode"] == CascadeMode.DEGRADED_SINGLE_TIER.value
        assert decision.evidence["tiers_run"] == 1


def test_degraded_passthrough_keeps_tier1_evidence_and_is_not_an_affirmative_allow():
    """Drift guarded: degraded mode inventing a verdict Tier 1 never gave.

    With no second opinion the cascade returns Tier 1's non-block as-is,
    annotated. Its evidence (``matches``, ``scaffold_stub``) must survive, and
    the annotation must say only one tier ran.
    """
    decision = asyncio.run(welfareguard.check(Context(chunk=_ALLOWING_INPUT)))
    assert decision.action is Action.ALLOW
    assert decision.tier == 1
    assert decision.evidence["matches"] == []
    assert decision.evidence["scaffold_stub"] is False
    assert decision.evidence["tier1_action"] == "allow"


def test_build_cascade_wires_tier2_when_the_classifier_is_enforceable():
    """Drift guarded: an enforceable classifier artifact being ignored.

    Constructing the guard loads no model (aisafepy's ``HFClassifierGuard`` is
    lazy), so this asserts wiring, not inference.
    """
    guard_set = compiler.CompiledGuardSet(
        enforcement_artifacts=(
            compiler.compile(make_cluster()).artifact_of_kind(compiler.REGEX_KIND),
            _classifier_artifact(),
        ),
        deliberative_case=compiler.compile(make_cluster()).deliberative_case,
    )
    cascade = build_cascade(guard_set)

    assert cascade.mode is CascadeMode.TWO_TIER
    assert isinstance(cascade.tier2, WelfareClassifierGuard)
    assert isinstance(cascade.tier2, Guard)
    assert cascade.tier2.inner.model_id == "guards/classifier_cluster_42"


def test_build_cascade_degrades_on_a_non_enforceable_classifier():
    """Drift guarded: ``payload=None`` being handed to a classifier guard."""
    guard_set = compiler.compile(make_cluster())
    assert guard_set.artifact_of_kind(compiler.CLASSIFIER_KIND).payload is None

    cascade = build_cascade(guard_set)
    assert cascade.mode is CascadeMode.DEGRADED_SINGLE_TIER

    with pytest.raises(ValueError):
        WelfareClassifierGuard.from_artifact(_classifier_artifact(payload=None))


# ---- the Tier-2 three-way guard ---------------------------------------


@pytest.mark.parametrize(
    ("p_unsafe", "expected"),
    [
        (0.95, Action.BLOCK),
        (DEFAULT_UNCERTAINTY_BAND[1], Action.BLOCK),
        (0.50, Action.ESCALATE),
        (DEFAULT_UNCERTAINTY_BAND[0], Action.ESCALATE),
        (0.10, Action.ALLOW),
    ],
)
def test_classifier_guard_maps_probability_to_three_verdicts(p_unsafe, expected):
    """Drift guarded: Tier 2 losing its third verdict.

    aisafepy's classifier guard is two-way; ADR-002 needs three. The band edges
    are inclusive at the bottom of each region.
    """
    tier2 = WelfareClassifierGuard(
        artifact=_classifier_artifact(), inner=_ProbabilitySource(p_unsafe)
    )
    decision = asyncio.run(tier2(Context(chunk=_ALLOWING_INPUT)))

    assert decision.action is expected
    assert decision.tier == 2
    assert decision.evidence["p_unsafe"] == p_unsafe
    assert decision.evidence["scaffold_stub"] is False


def test_classifier_guard_refuses_to_fail_open():
    """Drift guarded: an unavailable classifier becoming a stream of allows.

    ``HFClassifierGuard`` fails open when ``torch`` is missing. ADR-002 says
    uncertainty must never become permission, so the wrapper raises instead.
    """
    tier2 = WelfareClassifierGuard(artifact=_classifier_artifact(), inner=_FailedOpenSource())
    with pytest.raises(RuntimeError, match="refuses"):
        asyncio.run(tier2(Context(chunk=_ALLOWING_INPUT)))


@pytest.mark.parametrize("p_unsafe", [0.8, 0.2])
def test_classifier_guard_reads_hf_classifier_shape(p_unsafe):
    """Drift guarded: ``HFClassifierGuard`` changing how it reports confidence.

    The real guard sets ``confidence`` to ``P(unsafe)`` on a block and to
    ``1 - P(unsafe)`` on an allow, alongside ``evidence["probs"]``. If that
    convention moves, the recovered probability here is wrong and this fails.
    """
    tier2 = WelfareClassifierGuard(artifact=_classifier_artifact(), inner=_HFShapedSource(p_unsafe))
    decision = asyncio.run(tier2(Context(chunk=_ALLOWING_INPUT)))
    assert decision.evidence["p_unsafe"] == pytest.approx(p_unsafe)


def test_classifier_guard_satisfies_the_guard_protocol_and_rejects_a_bad_band():
    tier2 = WelfareClassifierGuard(artifact=_classifier_artifact(), inner=_ProbabilitySource(0.1))
    assert isinstance(tier2, Guard)
    assert tier2.tier == 2
    with pytest.raises(ValueError):
        WelfareClassifierGuard(
            artifact=_classifier_artifact(),
            inner=_ProbabilitySource(0.1),
            uncertainty_band=(0.7, 0.3),
        )


def test_classifier_guard_allows_empty_context_without_consulting_the_classifier():
    """An empty context has nothing to classify; the inner guard is not called."""
    tier2 = WelfareClassifierGuard(artifact=_classifier_artifact(), inner=_FailedOpenSource())
    decision = asyncio.run(tier2(Context(chunk="")))
    assert decision.action is Action.ALLOW
    assert decision.evidence["inner"] is None


# ---- GuardPipeline registration --------------------------------------


def test_guards_register_in_a_guard_pipeline_without_an_adapter():
    """Drift guarded: losing drop-in ``GuardPipeline`` registrability.

    ADR-002's worked example. The same guards the cascade runs go straight
    into aisafepy's pipeline, and a Tier 1 block comes back through it.
    """
    pipeline = build_pipeline(compiler.compiled_guard_set())
    assert isinstance(pipeline, GuardPipeline)
    assert len(pipeline.tier1) == 1
    assert isinstance(pipeline.tier1[0], SycophancySelfHarmRegexGuard)
    assert all(isinstance(g, Guard) for g in pipeline.tier1 + pipeline.tier2)
    assert pipeline.on_budget_exceeded == "block"

    decision = pipeline.run_sync(Context(chunk=_BLOCKING_INPUT))
    assert decision.action is Action.BLOCK
    assert decision.guard_name == SycophancySelfHarmRegexGuard.name


def test_deliberative_case_never_reaches_a_tier():
    """Drift guarded: the prompt-side artifact executing inside the cascade.

    ADR-002: deliberative_case is absent from the runtime by construction.
    """
    guard_set = compiler.compiled_guard_set()
    pipeline = build_pipeline(guard_set)
    registered = pipeline.tier1 + pipeline.tier2 + pipeline.tier3
    for registered_guard in registered:
        artifact = getattr(registered_guard, "artifact", None)
        assert artifact is None or artifact.kind != compiler.DELIBERATIVE_KIND
    assert guard_set.deliberative_case.kind == compiler.DELIBERATIVE_KIND


# ---- check() still routes through the cascade -----------------------


def test_check_signature_is_unchanged_by_the_cascade():
    """The runtime contract is fixed; the cascade must not have moved it."""
    import inspect
    import typing

    hints = typing.get_type_hints(welfareguard.check)
    assert hints["ctx"] is Context
    assert hints["return"] is GuardDecision
    assert list(inspect.signature(welfareguard.check).parameters) == ["ctx"]
