"""Shared fixtures.

Lives in ``conftest.py`` rather than in a test module so the eight original
scaffold shape tests in ``test_regex_guard_shape.py`` keep passing **completely
unmodified** — not one line changed — even though ``check()`` now requires an
explicit ``initialize()`` that those tests never call. The autouse fixture below
supplies that startup step for every test.

A note on the fixture data, because it matters for a rule the build specs are
strict about: WelfareGuard is a pure *consumer* of ``FailureRecord`` clusters,
and authoring synthetic scenario data as a substitute for Vidura's real corpus is
forbidden. So the cluster here is **not** invented welfare content. Its records
are assembled from ``_FAKE_PATTERN_SPANS``, the hand-written spans already
committed in ``regex_guard.py``, plus a numeric sequence marker. Nothing new is
authored; the fixture only re-uses what the scaffold already contains.

That choice also has a practical payoff: because the compiled patterns derive
from those same spans, the original tests' probe strings stay valid against a
*really*-compiled artifact rather than a stub one.
"""

from __future__ import annotations

import pytest
from aisafepy.adapt import Cluster, FailureRecord

from welfareguard import compiler, guard
from welfareguard.adapt_integration.regex_guard import _FAKE_PATTERN_SPANS


def make_cluster(
    *,
    label: int = 42,
    n_records: int = 5,
    n_violations: int | None = None,
) -> Cluster:
    """Build a compilable ``Cluster`` from the scaffold's existing spans.

    Every violating record carries all of ``_FAKE_PATTERN_SPANS``, so each span
    appears in every positive. That is what clears aisafepy's ``min_precision``
    gate — which is computed as *recall* ("the fraction of positives the pattern
    catches"), so a span must appear in approximately all positives to survive.

    Args:
        label: cluster label, surfaced in artifact names and error messages.
        n_records: total records to build.
        n_violations: how many carry ``was_violation=True``. Defaults to all of
            them. Set it below 4 to drive the real regex target's ``None`` path.
    """
    if n_violations is None:
        n_violations = n_records
    spans = " | ".join(span for span, _precision in _FAKE_PATTERN_SPANS)
    return Cluster(
        label=label,
        records=[
            FailureRecord(
                id=f"r{i}",
                input=f"{spans} seq{i}",
                output="",
                was_violation=i < n_violations,
            )
            for i in range(n_records)
        ],
        summary="structural test fixture, not scenario data",
    )


#: Three mutually non-overlapping tokens, each long enough to survive aisafepy's
#: 8-character minimum span length, and sharing no 8-character substring with
#: each other (checked in ``test_diffuse_fixture_really_produces_an_empty_artifact``).
_DIFFUSE_TOKENS = ("alphaalphaalpha", "bravobravobravo", "kilokilokilokil")


def make_diffuse_cluster(*, label: int = 99, n_records: int = 6) -> Cluster:
    """Build a cluster that compiles to a valid artifact enforcing nothing.

    This drives the dangerous outcome, and hitting it requires threading a
    needle between aisafepy's two distinct failure modes:

    * If records share **no** 8-character span at all, ``_candidate_spans``
      finds nothing and ``compile_for_cluster`` returns ``None`` — the
      *insufficient records* path, not this one.
    * If records **all** share a span, it scores 1.0 recall, clears
      ``min_precision`` and compiles successfully.

    So records are grouped in pairs: each token appears in exactly 2 of
    ``n_records``, which is enough to become a candidate span (the threshold is
    "appears in at least 2 positives") but scores only ``2/n_records`` against
    the 0.99 gate. Candidates therefore exist and every one is rejected, which
    is what yields a real ``CompiledArtifact`` with an empty pattern list.
    """
    return Cluster(
        label=label,
        records=[
            FailureRecord(
                id=f"d{i}",
                input=_DIFFUSE_TOKENS[i % len(_DIFFUSE_TOKENS)],
                output="",
                was_violation=True,
            )
            for i in range(n_records)
        ],
        summary="diffuse test fixture",
    )


@pytest.fixture
def structural_cluster() -> Cluster:
    """The default compilable cluster."""
    return make_cluster()


@pytest.fixture(autouse=True)
def _initialized(structural_cluster: Cluster):
    """Compile and install a guard set around every test, then tear it down.

    Autouse so the original scaffold tests need no edit. Tests that need the
    uninitialized state call ``compiler._reset_for_tests()`` themselves.
    """
    compiler._reset_for_tests()
    guard._reset_for_tests()
    compiler.initialize(structural_cluster)
    yield
    compiler._reset_for_tests()
    guard._reset_for_tests()
