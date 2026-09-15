"""WelfareGuard's fatal compile-time and startup errors.

These exist so failures are **loud, never silent**. A guard that comes up
serving traffic with an artifact enforcing nothing is worse than one that
refuses to come up at all: the first looks deployed and is not, which is exactly
the degraded-silently failure mode ADR-001's pairing constraint was written to
prevent.

Every error here is therefore intended to be fatal at startup. Nothing in
WelfareGuard catches them, and nothing falls back to a stub artifact when one is
raised.

They live in their own module so tests and callers can import them without
importing the compiler (and so pulling in ``torch`` via the classifier path).
"""

from __future__ import annotations


class WelfareGuardError(Exception):
    """Base class for every error WelfareGuard raises itself.

    Errors raised by ``aisafepy`` propagate unchanged and are deliberately not
    wrapped in this hierarchy — see the no-try/except rule in the build specs.
    """


class CompilationError(WelfareGuardError):
    """A cluster could not be compiled into a deployable guard artifact.

    Raised instead of returning ``None`` or an empty artifact, so a cluster that
    cannot produce enforcement stops startup rather than silently yielding a
    guard that matches nothing.
    """


class InsufficientRecordsError(CompilationError):
    """The cluster did not carry enough violating records to compile.

    Mirrors the real ``_RegexTarget.compile_for_cluster`` returning ``None``,
    which it does when the cluster has fewer than 4 violating records, when it
    has no violating records at all, or when no candidate spans emerge.

    Distinct from :class:`NoEnforceablePatternsError`: this means *not enough
    input*, which is a data problem.
    """

    def __init__(
        self,
        *,
        cluster_label: int,
        n_records: int,
        n_violations: int,
        kind: str,
    ) -> None:
        self.cluster_label = cluster_label
        self.n_records = n_records
        self.n_violations = n_violations
        self.kind = kind
        super().__init__(
            f"cluster {cluster_label} produced no {kind} artifact: "
            f"{n_violations} violating record(s) of {n_records} total. "
            f"aisafepy's {kind} target returned None. "
            f"Supply a cluster with more violating records."
        )


class NoEnforceablePatternsError(CompilationError):
    """Compilation returned a valid artifact that enforces nothing.

    The dangerous case, and the reason a ``None`` check alone is not enough. A
    cluster whose violating records share no sufficiently long common span
    yields a real ``CompiledArtifact`` whose ``payload["patterns"]`` is an empty
    list — it satisfies every type check, pairs correctly, and matches no input.

    Distinct from :class:`InsufficientRecordsError`: there *was* enough input,
    but nothing generalizable came out of it.

    Note ``min_precision`` is reported because aisafepy's threshold of that name
    is computed as **recall** — its own ``_estimate_precision`` docstring
    describes it as "the fraction of positives the pattern catches", with no
    negative set involved. A span must therefore appear in approximately every
    positive to survive the gate, which is why diffuse clusters land here.
    """

    def __init__(
        self,
        *,
        cluster_label: int,
        n_records: int,
        min_precision: float,
        artifact_name: str,
    ) -> None:
        self.cluster_label = cluster_label
        self.n_records = n_records
        self.min_precision = min_precision
        self.artifact_name = artifact_name
        super().__init__(
            f"cluster {cluster_label} compiled to artifact {artifact_name!r} "
            f"with zero enforceable patterns ({n_records} record(s), "
            f"min_precision={min_precision}). The artifact is structurally "
            f"valid but matches nothing, so it is refused rather than deployed. "
            f"Records shared no span long enough to clear the threshold."
        )


class NotInitializedError(WelfareGuardError):
    """``check()`` was called before ``initialize()``.

    Compilation is explicit and happens at ``initialize(cluster)``, never as an
    import side effect, so there is a window in which the runtime entry point
    has no artifact to enforce. Calling it then is a programming error, not a
    condition to degrade through.
    """

    def __init__(self) -> None:
        super().__init__(
            "welfareguard.check() called before welfareguard.initialize(cluster). "
            "Compilation is explicit: call initialize() once at startup with the "
            "cluster to compile. It is deliberately not triggered by import."
        )
