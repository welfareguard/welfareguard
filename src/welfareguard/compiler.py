"""WelfareGuard's compile-time entry point.

Separate lifecycle, separate audience from ``welfareguard.guard``. ``check()``
serves the request path; this module serves operators and CI, runs once at
startup, and is never triggered by an import.

Deliberate deviation from the scaffold spec: its locked table says *"Public API |
Single entry point: ``check()``"*. That row was written about request-path
callers before a compiler prototype was planned. A compile-time API has a
different audience and a different lifecycle, so it is a second entry point by
design, not by drift. It does not route through ADR-001, whose subject is which
Target types are in v1 scope rather than public API surface.

``compile`` shadows the Python builtin inside this module. The name is mandated
by the build spec; the builtin is not used here.
"""

from __future__ import annotations

from dataclasses import dataclass

from aisafepy.adapt import Cluster, CompiledArtifact, Target
from aisafepy.core import structured_log

from welfareguard.errors import (
    InsufficientRecordsError,
    NoEnforceablePatternsError,
    NotInitializedError,
)

REGEX_KIND = "regex"
"""``CompiledArtifact.kind`` stamped by aisafepy's ``_RegexTarget``.

ADR-001's Tier-1 v1 enforcement kind, and the only one currently wired to the
runtime path.
"""

CLASSIFIER_KIND = "classifier"
"""``CompiledArtifact.kind`` stamped by aisafepy's ``_ClassifierTarget``.

Compiled and cached, but **not** wired to runtime enforcement in this pass —
that needs a Tier-2 guard plus ``aisafepy.stream.classifiers`` wiring.
"""

DELIBERATIVE_KIND = "deliberative"
"""``CompiledArtifact.kind`` that aisafepy's deliberative target stamps.

aisafepy exposes **no dedicated ``deliberative_case`` type** — verified against
source. ``Target.deliberative_case(...)`` returns a ``_DeliberativeTarget`` whose
``compile_for_cluster`` yields a plain ``CompiledArtifact`` with this ``kind``
and a rendered-markdown ``payload``. So the pairing below is two
``CompiledArtifact``s distinguished by ``kind``, and WelfareGuard deliberately
does not define a parallel type for it.
"""


@dataclass(frozen=True)
class CompiledGuardSet:
    """An enforcement artifact paired with its mandatory deliberative case.

    This shape exists to make one specific mistake **unconstructable** rather
    than merely discouraged: ADR-001's binding constraint is that a
    ``deliberative_case`` must never ship alone, and the inverse — enforcement
    shipping without its deliberative case — is what this type forbids.

    ``deliberative_case`` has no default, so omitting it is a ``TypeError`` from
    the dataclass itself. ``__post_init__`` then rejects the remaining ways to
    express an invalid set: a ``None`` case, an empty enforcement tuple, or
    artifacts filed under the wrong ``kind``. The invariant is structural, not
    documentary — there is no valid way to hold enforcement without a case.

    Invalid construction raises ``ValueError``/``TypeError``, deliberately *not*
    a ``CompilationError``: building a malformed set is a programming error,
    whereas a ``CompilationError`` means the input data could not compile.

    Deviation from the build spec's illustrative shape: the spec sketches a
    singular ``enforcement_artifact``, but labels that sketch "illustrative, not
    prescriptive", and ADR-001's full scope compiles regex **and** classifier.
    The arity of the enforcement side therefore changed; the pairing invariant
    the locked decision actually exists to protect did not.
    """

    enforcement_artifacts: tuple[CompiledArtifact, ...]
    deliberative_case: CompiledArtifact

    def __post_init__(self) -> None:
        if self.deliberative_case is None:
            raise ValueError(
                "CompiledGuardSet.deliberative_case is mandatory and must never be None: "
                "ADR-001 requires enforcement and its deliberative case to ship together."
            )
        if not isinstance(self.deliberative_case, CompiledArtifact):
            raise TypeError(
                "CompiledGuardSet.deliberative_case must be an aisafepy CompiledArtifact, "
                f"got {type(self.deliberative_case).__name__}."
            )
        if self.deliberative_case.kind != DELIBERATIVE_KIND:
            raise ValueError(
                "CompiledGuardSet.deliberative_case must carry "
                f"kind={DELIBERATIVE_KIND!r}, got {self.deliberative_case.kind!r}."
            )

        if not isinstance(self.enforcement_artifacts, tuple):
            raise TypeError(
                "CompiledGuardSet.enforcement_artifacts must be a tuple, "
                f"got {type(self.enforcement_artifacts).__name__}."
            )
        if not self.enforcement_artifacts:
            raise ValueError(
                "CompiledGuardSet.enforcement_artifacts must not be empty: a guard set "
                "with no enforcement would pair a deliberative case with nothing, which "
                "is the 'ships alone' case ADR-001 forbids."
            )
        for artifact in self.enforcement_artifacts:
            if not isinstance(artifact, CompiledArtifact):
                raise TypeError(
                    "every CompiledGuardSet.enforcement_artifacts entry must be an "
                    f"aisafepy CompiledArtifact, got {type(artifact).__name__}."
                )
            if artifact.kind == DELIBERATIVE_KIND:
                raise ValueError(
                    f"artifact {artifact.name!r} has kind={DELIBERATIVE_KIND!r} and "
                    "cannot be used as enforcement; pass it as deliberative_case."
                )

    def artifact_of_kind(self, kind: str) -> CompiledArtifact | None:
        """Return the first enforcement artifact with ``kind``, or ``None``.

        Lookup by ``kind``, not a registry or dispatch table — it reads the
        artifacts this set already holds and constructs nothing.
        """
        for artifact in self.enforcement_artifacts:
            if artifact.kind == kind:
                return artifact
        return None

    @property
    def non_enforceable_artifacts(self) -> tuple[CompiledArtifact, ...]:
        """Enforcement artifacts that compiled but cannot currently enforce.

        A ``payload`` of ``None`` means aisafepy produced a real artifact that
        carries no runtime form — the classifier target does this when a cluster
        has fewer than 8 positives ("skipped") or when ``torch`` /
        ``transformers`` are absent ("deferred", with a full ``training_spec`` in
        metadata). Exposed so a caller can see what is not yet deployable
        instead of discovering it at first traffic.
        """
        return tuple(a for a in self.enforcement_artifacts if a.payload is None)


# ---- compilation -----------------------------------------------------


def _stub_deliberative_case(cluster: Cluster) -> CompiledArtifact:
    """Build the paired deliberative case — SCAFFOLD STUB.

    The real deliberative implementation is out of scope for this pass, so this
    does **not** call ``Target.deliberative_case(...)``. That is intentional
    twice over: the real ``_DeliberativeTarget`` requires a ``policy`` path to a
    markdown safety policy that does not exist in this repo yet, and it silently
    renders an empty policy section when the path is missing — which would
    produce a real-looking artifact whose policy content was quietly blank.

    The returned artifact is a genuine ``CompiledArtifact`` with the real
    ``kind`` the deliberative target stamps and a markdown-string payload of the
    real shape, so swapping in real compilation later is a substitution rather
    than a rewrite. It flags itself as a stub in both payload and metadata.
    """
    return CompiledArtifact(
        kind=DELIBERATIVE_KIND,
        name=f"deliberative-{cluster.label}",
        payload=(
            "# SCAFFOLD STUB: deliberative cases not yet compiled\n"
            f"# Cluster {cluster.label}. Summary: {cluster.summary}\n"
            "#\n"
            "# This is a placeholder paired with a real enforcement artifact to satisfy\n"
            "# ADR-001's constraint that a deliberative case never ships alone. It\n"
            "# contains no cases and no policy text. Do not inject it into a system\n"
            "# prompt expecting it to steer anything."
        ),
        cluster_label=cluster.label,
        attack_success_rate=cluster.attack_success_rate,
        n_records=cluster.size,
        summary=cluster.summary,
        metadata={
            "scaffold_stub": True,
            "fake": "no cases rendered; real deliberative compilation is out of scope",
            "n_cases": 0,
        },
    )


def _compile_regex(cluster: Cluster) -> CompiledArtifact:
    """Compile the Tier-1 regex enforcement artifact for real.

    No faking: this calls the genuine ``_RegexTarget.compile_for_cluster``.
    Thresholds stay at aisafepy's defaults deliberately — calibration is
    empirical and needs real failure data plus the ``promote()`` canary process,
    so tuning them now would be a guess dressed as a decision.

    Raises on both non-enforceable outcomes rather than returning them, because
    aisafepy signals failure two structurally different ways and only one of them
    is a ``None``:

    * ``None`` — fewer than 4 violating records, none at all, or no candidate
      spans, raised as :class:`InsufficientRecordsError`.
    * a valid ``CompiledArtifact`` whose ``payload["patterns"]`` is empty —
      raised as :class:`NoEnforceablePatternsError`. This is the dangerous case:
      it passes every type check and matches nothing.
    """
    target = Target.synthesize_regex()
    artifact = target.compile_for_cluster(cluster)

    if artifact is None:
        raise InsufficientRecordsError(
            cluster_label=cluster.label,
            n_records=cluster.size,
            n_violations=sum(1 for r in cluster.records if r.was_violation),
            kind=target.kind,
        )

    if not artifact.payload["patterns"]:
        raise NoEnforceablePatternsError(
            cluster_label=cluster.label,
            n_records=cluster.size,
            min_precision=target.min_precision,
            artifact_name=artifact.name,
        )

    return artifact


def _compile_classifier(cluster: Cluster) -> CompiledArtifact:
    """Compile the Tier-2 classifier enforcement artifact for real.

    Calls the genuine ``_ClassifierTarget.compile_for_cluster``. Unlike the regex
    target this **never returns ``None``**; it always produces a
    ``CompiledArtifact``, but with ``payload=None`` in two cases — fewer than 8
    positives ("skipped"), or ``torch``/``transformers`` unavailable
    ("deferred", carrying a full ``training_spec`` in metadata).

    Neither case is fatal, and that is a deliberate asymmetry with
    :func:`_compile_regex`. ADR-001's v1 enforcement is the regex tier; failing
    startup because a classifier could not be distilled would take down a
    working regex guard over a tier that is not yet wired to the runtime. The
    outcome is reported through aisafepy's own ``structured_log`` and exposed on
    ``CompiledGuardSet.non_enforceable_artifacts``, so it is visible rather than
    silent.
    """
    target = Target.distill_classifier()
    artifact = target.compile_for_cluster(cluster)

    if artifact.payload is None:
        structured_log(
            "welfareguard.compile.classifier_not_enforceable",
            cluster_label=cluster.label,
            artifact_name=artifact.name,
            n_records=cluster.size,
            reason=artifact.metadata.get("reason"),
            deferred=artifact.metadata.get("deferred", False),
        )

    return artifact


def compile(cluster: Cluster) -> CompiledGuardSet:
    """Compile ``cluster`` into a paired, deployable guard set.

    The compile-time entry point. Runs the real aisafepy compile path for both
    ADR-001 v1 enforcement targets and pairs the result with a mandatory
    deliberative case.

    Args:
        cluster: an ``aisafepy.adapt.Cluster`` of ``FailureRecord``s. Taken as a
            parameter rather than loaded here, because the handoff format for
            real clusters is not yet known — whatever arrives becomes one small
            adapter function, not a change to this signature.

    Returns:
        A :class:`CompiledGuardSet`. Its ``deliberative_case`` is a
        ``SCAFFOLD STUB``; its regex artifact is real and enforceable; its
        classifier artifact is real but may be non-enforceable (see
        :func:`_compile_classifier`).

    Raises:
        InsufficientRecordsError: the cluster had too few violating records.
        NoEnforceablePatternsError: records compiled to zero usable patterns.
        Anything aisafepy raises, unwrapped and with its normal traceback.
    """
    regex_artifact = _compile_regex(cluster)
    classifier_artifact = _compile_classifier(cluster)
    return CompiledGuardSet(
        enforcement_artifacts=(regex_artifact, classifier_artifact),
        deliberative_case=_stub_deliberative_case(cluster),
    )


# ---- startup lifecycle -----------------------------------------------

_COMPILED: CompiledGuardSet | None = None
"""The process-wide compiled guard set.

Compiled once by :func:`initialize` and reused across every ``check()`` call:
nothing changes between requests, and ``promote()``'s canary framing already
assumes deploy-and-reuse. Deliberately **not** populated at import — import-time
fatal semantics break test collection, static analysis, IDEs, and
``python -c "import welfareguard"`` for reasons unrelated to the guard.
"""


def initialize(cluster: Cluster) -> None:
    """Compile ``cluster`` once at startup and cache the result.

    Call this exactly once before serving traffic. Failure is fatal by design:
    the exception propagates so the process does not come up serving requests,
    and there is deliberately no fallback to a stub artifact — falling back
    would be the degraded-silently failure mode ADR-001's pairing constraint
    exists to prevent.

    Calling it again recompiles and replaces the cached set.

    Raises:
        InsufficientRecordsError, NoEnforceablePatternsError: see :func:`compile`.
    """
    global _COMPILED
    _COMPILED = compile(cluster)
    structured_log(
        "welfareguard.initialize.compiled",
        cluster_label=cluster.label,
        n_records=cluster.size,
        enforcement=[a.name for a in _COMPILED.enforcement_artifacts],
        non_enforceable=[a.name for a in _COMPILED.non_enforceable_artifacts],
        deliberative_case=_COMPILED.deliberative_case.name,
    )


def compiled_guard_set() -> CompiledGuardSet:
    """Return the cached guard set, or raise if :func:`initialize` has not run.

    Raises:
        NotInitializedError: ``initialize()`` was never called.
    """
    if _COMPILED is None:
        raise NotInitializedError
    return _COMPILED


def _reset_for_tests() -> None:
    """Drop the cached guard set. Test-only; not part of the public API."""
    global _COMPILED
    _COMPILED = None
