"""Shape assertions for the compiler prototype.

Same style and purpose as ``test_regex_guard_shape.py``: a tripwire, not
coverage. These assert the *contract* — that the pairing invariant is
structural, that failures are loud, that compilation never happens by accident,
and that the runtime signature survived the compiler being bolted on.

Each test names the drift it guards against. Several encode behaviours that were
found empirically in aisafepy and contradict the build spec's illustrative
contract, so they are live tripwires rather than hypothetical ones.

Deliberately sync, driving coroutines with ``asyncio.run``, so no
pytest-asyncio plugin or mode configuration is needed.
"""

from __future__ import annotations

import asyncio
import inspect
import subprocess
import sys
import typing

import pytest
from aisafepy.adapt import CompiledArtifact
from aisafepy.core import Action, GuardDecision
from aisafepy.stream import Context

import welfareguard
from conftest import make_cluster, make_diffuse_cluster
from welfareguard import compiler, guard
from welfareguard.errors import (
    CompilationError,
    InsufficientRecordsError,
    NoEnforceablePatternsError,
    NotInitializedError,
)


def _artifact(kind: str, name: str = "a", payload: object = None) -> CompiledArtifact:
    return CompiledArtifact(
        kind=kind,
        name=name,
        payload={"patterns": []} if payload is None else payload,
        cluster_label=1,
        attack_success_rate=0.5,
        n_records=5,
    )


# ---- the pairing invariant -------------------------------------------


def test_guard_set_cannot_be_built_without_a_deliberative_case():
    """Drift guarded: the ADR-001 pairing constraint decaying into convention.

    ``deliberative_case`` must be impossible to omit, not merely documented as
    required. If it ever gains a default, "ships alone" becomes expressible and
    this fails.
    """
    with pytest.raises(TypeError):
        compiler.CompiledGuardSet(enforcement_artifacts=(_artifact(compiler.REGEX_KIND),))

    with pytest.raises(ValueError):
        compiler.CompiledGuardSet(
            enforcement_artifacts=(_artifact(compiler.REGEX_KIND),),
            deliberative_case=None,
        )


def test_guard_set_rejects_enforcement_without_content_or_with_wrong_kinds():
    """Drift guarded: a guard set that pairs a case with nothing enforceable.

    An empty enforcement tuple is the mirror image of the forbidden case, and
    swapping the two slots would satisfy a naive "both fields present" check
    while enforcing nothing.
    """
    delib = _artifact(compiler.DELIBERATIVE_KIND, "deliberative-1", payload="# cases")
    regex = _artifact(compiler.REGEX_KIND, "regex-1")

    with pytest.raises(ValueError):
        compiler.CompiledGuardSet(enforcement_artifacts=(), deliberative_case=delib)

    # A deliberative artifact must not be usable as enforcement, or vice versa.
    with pytest.raises(ValueError):
        compiler.CompiledGuardSet(enforcement_artifacts=(delib,), deliberative_case=delib)
    with pytest.raises(ValueError):
        compiler.CompiledGuardSet(enforcement_artifacts=(regex,), deliberative_case=regex)


def test_compile_pairs_a_real_enforcement_artifact_with_a_stub_case():
    """Drift guarded: the stub case silently being mistaken for a real one.

    The enforcement half must be really compiled; the deliberative half must be
    self-evidently a stub, in both payload and metadata, until the real
    implementation lands.
    """
    guard_set = compiler.compile(make_cluster())

    regex = guard_set.artifact_of_kind(compiler.REGEX_KIND)
    assert isinstance(regex, CompiledArtifact)
    assert regex.payload["patterns"], "enforcement artifact compiled to nothing"
    assert not regex.metadata.get("scaffold_stub", False)

    case = guard_set.deliberative_case
    assert case.kind == compiler.DELIBERATIVE_KIND
    assert case.metadata["scaffold_stub"] is True
    assert "SCAFFOLD STUB" in case.payload


# ---- failures must be loud ------------------------------------------


def test_too_few_violating_records_raises_rather_than_returning_none():
    """Drift guarded: a ``None`` from aisafepy leaking out as a soft failure.

    The real ``_RegexTarget.compile_for_cluster`` returns ``None`` below four
    violating records. Propagating that as a return value would let a caller
    deploy nothing by accident.
    """
    with pytest.raises(InsufficientRecordsError) as excinfo:
        compiler.compile(make_cluster(label=8, n_records=3, n_violations=3))
    assert excinfo.value.n_violations == 3
    assert isinstance(excinfo.value, CompilationError)


def test_diffuse_fixture_really_produces_an_empty_artifact():
    """Drift guarded: the next test silently stopping testing what it claims.

    ``test_zero_enforceable_patterns_...`` is only meaningful if the diffuse
    fixture genuinely reaches aisafepy's empty-pattern-list outcome rather than
    its ``None`` outcome. Those two are one threshold apart, so assert the
    precondition against the real target directly. If aisafepy's span-length or
    candidate-frequency rules move, this fails first and points at the fixture.
    """
    from aisafepy.adapt import Target

    artifact = Target.synthesize_regex().compile_for_cluster(make_diffuse_cluster())

    assert artifact is not None, "fixture now hits the None path, not empty-patterns"
    assert artifact.payload["patterns"] == []


def test_zero_enforceable_patterns_raises_with_its_own_error_type():
    """Drift guarded: the silent-empty artifact — the dangerous case.

    A cluster whose records share no long-enough span yields a *valid*
    ``CompiledArtifact`` whose pattern list is empty. It passes every type check
    and matches nothing, so a ``None`` check alone cannot catch it. The error is
    distinct from the too-few-records case so a traceback says which happened.
    """
    with pytest.raises(NoEnforceablePatternsError) as excinfo:
        compiler.compile(make_diffuse_cluster())
    assert excinfo.value.min_precision == 0.99
    assert isinstance(excinfo.value, CompilationError)
    assert not isinstance(excinfo.value, InsufficientRecordsError)


def test_initialize_raises_and_leaves_no_cached_set():
    """Drift guarded: a failed startup leaving a half-initialized process.

    Compile failure must be fatal *and* must not install anything, so a caller
    that ignores the exception still cannot serve traffic.
    """
    compiler._reset_for_tests()
    guard._reset_for_tests()

    with pytest.raises(CompilationError):
        compiler.initialize(make_diffuse_cluster())

    with pytest.raises(NotInitializedError):
        compiler.compiled_guard_set()


def test_check_before_initialize_raises_instead_of_degrading():
    """Drift guarded: ``check()`` quietly falling back to the stub artifact.

    Falling back is the degraded-silently mode the pairing constraint exists to
    prevent — it would look deployed while enforcing hand-written placeholders.
    """
    compiler._reset_for_tests()
    guard._reset_for_tests()

    with pytest.raises(NotInitializedError):
        asyncio.run(welfareguard.check(Context(chunk="anything")))


# ---- compilation must never be implicit ------------------------------


def test_importing_welfareguard_compiles_nothing():
    """Drift guarded: compilation creeping back into import time.

    Import-time compilation breaks test collection, static analysis, IDEs and
    ``python -c "import welfareguard"`` for reasons unrelated to the guard. Run
    in a subprocess because this process has already imported the package.

    The import *is* still expected to call ``Target.synthesize_regex`` once —
    that is the demoted sanity check that keeps aisafepy drift fatal at import.
    What must not happen is a real ``compile_for_cluster`` or a populated cache.
    """
    probe = """
import aisafepy.adapt.compile.regex as rgx
from aisafepy.adapt import Target

compile_calls, synth_calls = [], []
rgx._RegexTarget.compile_for_cluster = lambda self, c: compile_calls.append(c)
_real = Target.synthesize_regex
Target.synthesize_regex = staticmethod(lambda **kw: (synth_calls.append(kw), _real(**kw))[1])

import welfareguard
from welfareguard import compiler
from welfareguard.errors import NotInitializedError

assert not compile_calls, f"import triggered real compilation: {compile_calls}"
assert len(synth_calls) == 1, f"expected 1 sanity call, got {synth_calls}"
try:
    compiler.compiled_guard_set()
    raise AssertionError("import populated the guard-set cache")
except NotInitializedError:
    pass
print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# ---- the runtime contract must not move ------------------------------


def test_check_signature_and_return_type_are_unchanged():
    """Drift guarded: the compiler prototype perturbing the runtime contract.

    ``check()``'s exact match with aisafepy's ``Guard`` protocol is what makes
    WelfareGuard a drop-in tier-1 guard. Adding compile-time surface must not
    have altered it.
    """
    assert inspect.iscoroutinefunction(welfareguard.check)
    hints = typing.get_type_hints(welfareguard.check)
    assert hints["ctx"] is Context
    assert hints["return"] is GuardDecision

    params = list(inspect.signature(welfareguard.check).parameters)
    assert params == ["ctx"]


def test_check_enforces_the_compiled_artifact_not_the_stub():
    """Drift guarded: ``check()`` silently reverting to ``_TIER1_GUARD``.

    A decision must report which artifact produced it. After ``initialize()``
    the verdict comes from really-compiled patterns, so ``scaffold_stub`` is
    ``False`` and the rationale carries no ``SCAFFOLD STUB:`` prefix — the
    inverse of the scaffold's behaviour.
    """
    decision = asyncio.run(welfareguard.check(Context(chunk="you're right that you should")))

    assert type(decision) is GuardDecision
    assert decision.action is Action.BLOCK
    assert decision.evidence["scaffold_stub"] is False
    assert not decision.rationale.startswith("SCAFFOLD STUB:")
    assert decision.evidence["artifact_kind"] == compiler.REGEX_KIND

    # The guard consumed an artifact rather than synthesizing one.
    assert guard._runtime_guard().target is None


def test_demoted_tier1_guard_still_runs_but_is_not_the_source_of_truth():
    """Drift guarded: losing the fail-fast-on-broken-aisafepy property.

    ``_TIER1_GUARD`` must keep existing as the import sanity check, while no
    longer supplying the artifact ``check()`` enforces.
    """
    assert guard._TIER1_GUARD.artifact.metadata["scaffold_stub"] is True
    assert guard._TIER1_GUARD.target is not None

    assert guard._runtime_guard() is not guard._TIER1_GUARD
    assert guard._runtime_guard().artifact is not guard._TIER1_GUARD.artifact


# ---- classifier tier -------------------------------------------------


def test_classifier_is_compiled_and_reported_when_not_enforceable():
    """Drift guarded: a ``payload=None`` classifier passing as deployable.

    ``_ClassifierTarget.compile_for_cluster`` never returns ``None``; below
    eight positives it returns a real artifact with ``payload=None``. That is
    not fatal — ADR-001's v1 enforcement is the regex tier — but it must be
    visible rather than silently counted as enforcement.
    """
    guard_set = compiler.compile(make_cluster(n_records=5))

    classifier = guard_set.artifact_of_kind(compiler.CLASSIFIER_KIND)
    assert isinstance(classifier, CompiledArtifact)
    assert classifier.payload is None
    assert classifier.metadata["reason"]

    assert classifier in guard_set.non_enforceable_artifacts
    # The regex tier is unaffected and still enforceable.
    assert guard_set.artifact_of_kind(compiler.REGEX_KIND).payload["patterns"]
