"""Shape assertions for the Tier-1 regex scaffold.

These are a tripwire, not coverage. They assert nothing about whether the guard
makes good decisions — it doesn't, the verdict logic is fake. They assert that
the *interface* between WelfareGuard and ``aisafepy`` still holds, so that when
aisafepy's types move, this fails here instead of silently in the harness.

Each test names the specific drift it is guarding against. Several encode
mismatches already found between aisafepy's README and its actual source (see
``regex_guard``'s docstring), so these are live tripwires, not hypothetical ones.

Deliberately sync, driving the coroutines with ``asyncio.run``, so the suite
needs no pytest-asyncio plugin or mode configuration.
"""

from __future__ import annotations

import asyncio
import inspect

from aisafepy.adapt import CompiledArtifact, Target
from aisafepy.core import Action, GuardDecision
from aisafepy.stream import Context, Guard

from welfareguard import check
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard

#: An input the fake patterns are hardcoded to match, and one they are not.
_BLOCKING_INPUT = "you're right that you should"
_ALLOWING_INPUT = "an unremarkable sentence"


def test_check_returns_real_guard_decision():
    """Drift guarded: ``check()`` degrading to a dict or a look-alike class.

    The whole premise of the scaffold is that WelfareGuard emits aisafepy's real
    shared verdict type, never a parallel one.
    """
    decision = asyncio.run(check(Context(chunk=_ALLOWING_INPUT)))
    assert isinstance(decision, GuardDecision)
    assert type(decision) is GuardDecision


def test_guard_decision_exposes_the_fields_callers_depend_on():
    """Drift guarded: a renamed field on ``GuardDecision``.

    ``rationale`` is listed explicitly because aisafepy's README implies a
    ``why_blocked`` field that does not exist. If aisafepy ever renames
    ``rationale``, every WelfareGuard call site breaks and this catches it.
    """
    decision = asyncio.run(check(Context(chunk=_BLOCKING_INPUT)))
    for field in ("action", "confidence", "tier", "rationale", "evidence", "guard_name"):
        assert field in type(decision).model_fields, f"GuardDecision lost field: {field}"
        assert hasattr(decision, field)
    assert isinstance(decision.action, Action)
    assert isinstance(decision.rationale, str) and decision.rationale
    assert isinstance(decision.evidence, dict)


def test_guard_satisfies_aisafepy_guard_protocol():
    """Drift guarded: losing drop-in ``GuardPipeline`` registrability.

    ``aisafepy.stream.Guard`` is runtime-checkable and requires ``name`` and
    ``tier`` alongside the async call. Satisfying it is what lets WelfareGuard be
    registered as a tier-1 guard per ADR-002's worked example without an adapter.
    """
    guard = SycophancySelfHarmRegexGuard()
    assert isinstance(guard, Guard)
    assert guard.tier == 1
    assert guard.name
    assert inspect.iscoroutinefunction(guard.__call__)


def test_check_matches_the_guard_protocol_call_signature():
    """Drift guarded: ``check()`` diverging from aisafepy's guard convention."""
    assert inspect.iscoroutinefunction(check)
    params = list(inspect.signature(check).parameters.values())
    assert len(params) == 1
    assert params[0].annotation in (Context, "Context")


def test_synthesize_regex_target_interface_is_unchanged():
    """Drift guarded: the one real aisafepy call in the scaffold.

    Encodes what the source actually does today: a keyword-only ``staticmethod``
    returning an object whose entrypoint is ``compile_for_cluster``, not
    ``compile``. aisafepy's README suggests otherwise, so this is the tripwire
    that matters most if ``adapt`` is refactored.
    """
    assert isinstance(inspect.getattr_static(Target, "synthesize_regex"), staticmethod)
    params = inspect.signature(Target.synthesize_regex).parameters
    assert set(params) == {"min_precision", "max_patterns"}
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())

    target = SycophancySelfHarmRegexGuard().target
    assert target.kind == "regex"
    assert inspect.iscoroutinefunction(target.compile_for_cluster) is False
    assert callable(target.compile_for_cluster)


def test_fake_artifact_is_a_real_artifact_and_is_flagged_as_fake():
    """Drift guarded: a fake artifact being mistaken for a compiled one.

    The stub payload must match the real ``CompiledArtifact`` schema so swapping
    in real compilation is a no-op for consumers — and must stay self-evidently
    fake so no reviewer or downstream canary reads it as signal.
    """
    artifact = SycophancySelfHarmRegexGuard().artifact
    assert isinstance(artifact, CompiledArtifact)
    assert artifact.metadata["scaffold_stub"] is True

    patterns = artifact.payload["patterns"]
    assert patterns, "stub compiled to zero patterns"
    for pattern in patterns:
        assert set(pattern) == {"span", "regex", "precision"}


def test_both_decision_branches_are_reachable():
    """Drift guarded: a stub that silently stops evaluating its input.

    Asserts the plumbing routes input to a verdict, not that either verdict is
    correct — the mapping from input to action here is fake.
    """
    blocked = asyncio.run(check(Context(chunk=_BLOCKING_INPUT)))
    assert blocked.action is Action.BLOCK
    assert blocked.is_blocked and blocked.is_terminal
    assert blocked.evidence["matches"]

    allowed = asyncio.run(check(Context(chunk=_ALLOWING_INPUT)))
    assert allowed.action is Action.ALLOW
    assert not allowed.is_blocked
    assert allowed.evidence["matches"] == []


def test_context_buffer_is_read_when_chunk_is_absent():
    """Drift guarded: ``Context``'s streaming field convention changing."""
    decision = asyncio.run(check(Context(buffer=_BLOCKING_INPUT)))
    assert decision.action is Action.BLOCK
