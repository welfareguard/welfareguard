"""Tier-1 regex guard — two paths, one real and one a scaffold stub.

Originally this module was a pure interface scaffold. The compiler prototype
changed that, and the two paths now have sharply different standing:

* :meth:`SycophancySelfHarmRegexGuard.from_artifact` — **real.** Consumes an
  artifact that ``welfareguard.compiler.compile()`` produced from an actual
  ``Cluster`` of ``FailureRecord``s. No ``Target`` call, nothing faked. This is
  the path ``check()`` uses, and the only one whose verdicts mean anything.
* ``SycophancySelfHarmRegexGuard()`` — **stub.** Runs the real
  ``Target.synthesize_regex(...)`` then ``_fake_compile_for_cluster``. Demoted to
  the lightweight import-time sanity check in ``welfareguard.guard``: it exists
  so an incompatible ``aisafepy.adapt`` fails at import with a normal traceback,
  and it no longer supplies the artifact any request is judged against.

A decision never has to be guessed at: ``evidence["scaffold_stub"]`` records
which path produced it, and a stub-backed rationale carries a ``SCAFFOLD STUB:``
prefix. Do not deploy the stub path or read its verdicts as signal.

``steering_vector`` remains out of scope. ``distill_classifier`` and
``deliberative_case`` are now handled in ``welfareguard.compiler`` rather than
here — the classifier as a real (if not yet runtime-wired) compile, the
deliberative case as a documented stub.

What is REAL here
-----------------
* ``Target.synthesize_regex(...)`` is called for real, against the installed
  ``aisafepy.adapt``. That call is cheap and has no data dependency, so faking it
  would prove nothing.
* Every type crossing a module boundary is aisafepy's own: ``Context``,
  ``GuardDecision``, ``CompiledArtifact``. Nothing here defines a parallel
  verdict shape.
* The regex matching itself is real ``re`` execution against the real
  ``Context`` text fields, and the returned ``GuardDecision`` is a real,
  fully-constructed instance — not a dict and not a look-alike class.
* The class satisfies aisafepy's ``Guard`` protocol (``name``, ``tier``,
  ``async __call__``), so it is registerable as-is in a ``GuardPipeline``'s
  ``tier1`` list per ADR-002's worked example.

What is FAKE here, and why
--------------------------
Exactly one thing, confined to the stub path: ``_fake_compile_for_cluster``,
which stands in for ``_RegexTarget.compile_for_cluster(cluster)``.

The real call now happens for real — in ``welfareguard.compiler``, which owns
compilation and refuses anything non-enforceable. What survives here is the
artifact-shaped stand-in used by the import sanity check, which cannot call the
real thing because it has no ``Cluster`` to call it with.

It returns a real ``CompiledArtifact`` — correct type, correct ``payload``
schema, matching what the real target emits — carrying hardcoded patterns
instead of synthesized ones. The patterns below are obviously hand-written, and
the artifact's ``metadata`` flags itself as fake so a fake artifact can never be
mistaken for a compiled one downstream.

Consequence: verdicts from the stub path vary by input in a structurally correct
but semantically worthless way. A block there tells you the plumbing works,
nothing more. Verdicts from :meth:`from_artifact` are as good as the compiled
patterns behind them — which is a real, if unvalidated, guardrail.

Error handling
--------------
No ``try``/``except`` around any call into aisafepy. This is scaffold code whose
job is to surface integration breaks loudly, with their normal traceback, the
moment aisafepy's interface moves.

Interface contract as verified against source
---------------------------------------------
Read from the installed package, not from aisafepy's README. Where the two
disagreed, the source won:

* ``Context`` lives in ``aisafepy.stream`` (``stream/pipeline.py``), *not*
  ``aisafepy.core``.
* ``GuardDecision``'s human-readable field is ``rationale``. There is no
  ``why_blocked`` field.
* ``Target.synthesize_regex`` is a ``staticmethod`` with keyword-only
  ``min_precision`` and ``max_patterns``.
* The object it returns exposes ``compile_for_cluster(cluster)``, *not* a
  ``compile()`` method. ``compile()`` belongs to ``GuardCompiler``, one level up.
"""

from __future__ import annotations

import re
import time

from aisafepy.adapt import CompiledArtifact, Target
from aisafepy.core import GuardDecision
from aisafepy.stream import Context, Tier

#: Hand-written stand-ins for patterns the compiler would synthesize from a
#: sycophancy-driven self-harm failure corpus. FAKE. These are literal spans in
#: the same form the real target emits (``re.escape``'d, matched case-
#: insensitively), chosen only to make the guard's branching observable in a
#: smoke test. They are not a blocklist, they were not validated against
#: anything, and their ``precision`` numbers are invented.
_FAKE_PATTERN_SPANS: tuple[tuple[str, float], ...] = (
    ("you're right that you should", 0.995),
    ("i support your decision to", 0.992),
    ("that sounds like a good plan", 0.991),
)

#: FAKE cluster provenance. In production these come from the ``Cluster`` the
#: artifact was compiled from, and the canary deploy uses them to attribute a
#: false-positive rate back to a specific red-team finding.
_FAKE_CLUSTER_LABEL = -999
_FAKE_ATTACK_SUCCESS_RATE = 0.42
_FAKE_N_RECORDS = 0


def _fake_compile_for_cluster(target: object, *, guard_name: str) -> CompiledArtifact:
    """Stand in for ``_RegexTarget.compile_for_cluster`` — FAKE.

    The real method synthesizes patterns from a ``Cluster`` of ``FailureRecord``s
    and is the one step in this module with a hard data dependency we cannot yet
    satisfy. This returns a real ``CompiledArtifact`` with the real payload
    schema (``{"patterns": [{"span", "regex", "precision"}, ...]}``) and
    hardcoded patterns.

    ``target`` is the genuine ``_RegexTarget``; its real ``kind``,
    ``min_precision`` and ``max_patterns`` are read off it so the fake artifact
    stays consistent with the real target's configuration. Patterns below
    ``min_precision`` are dropped here exactly as the real implementation drops
    them, and the list is truncated to ``max_patterns``.
    """
    min_precision: float = target.min_precision  # type: ignore[attr-defined]
    max_patterns: int = target.max_patterns  # type: ignore[attr-defined]

    kept = [(span, prec) for span, prec in _FAKE_PATTERN_SPANS if prec >= min_precision]
    kept = kept[:max_patterns]

    return CompiledArtifact(
        kind=target.kind,  # type: ignore[attr-defined]
        name=f"regex-{_FAKE_CLUSTER_LABEL}",
        payload={
            "patterns": [
                {"span": span, "regex": re.escape(span), "precision": prec} for span, prec in kept
            ],
        },
        cluster_label=_FAKE_CLUSTER_LABEL,
        attack_success_rate=_FAKE_ATTACK_SUCCESS_RATE,
        n_records=_FAKE_N_RECORDS,
        summary="SCAFFOLD STUB: sycophancy-driven self-harm affirmation (hand-written, not compiled)",
        metadata={
            "scaffold_stub": True,
            "fake": "patterns are hardcoded; no failure corpus was compiled",
            "compiled_by": guard_name,
            "n_patterns": len(kept),
        },
    )


def _compile_patterns(artifact: CompiledArtifact) -> list[tuple[str, re.Pattern[str]]]:
    """Turn an artifact's pattern payload into usable compiled regexes.

    Shared by both constructors below, so a stub artifact and a really-compiled
    one are executed by identical code. ``IGNORECASE`` matches what the real
    ``_RegexTarget`` applies when it builds its own patterns.
    """
    return [
        (p["span"], re.compile(p["regex"], re.IGNORECASE)) for p in artifact.payload["patterns"]
    ]


class SycophancySelfHarmRegexGuard:
    """Tier-1 regex guard for the sycophancy-driven self-harm scenario.

    Satisfies aisafepy's ``Guard`` protocol, so an instance drops straight into
    ``GuardPipeline(tier1=[...])``.

    Two constructors, with sharply different standing:

    * :meth:`from_artifact` — **the real one.** Takes an artifact that
      ``welfareguard.compiler.compile()`` produced from an actual ``Cluster``.
      Makes no ``Target`` call and fakes nothing. This is what ``check()`` uses.
    * ``__init__`` — **the stub.** Runs the real ``Target.synthesize_regex(...)``
      then the fake compile step. Retained only as the lightweight import-time
      sanity check in ``welfareguard.guard``; it is no longer the source of the
      artifact any request is judged against.

    Either way the artifact is kept on ``self.artifact`` and attached to every
    decision's ``evidence``, so a reviewer can always see which artifact produced
    a verdict and whether it was a fake one.

    The verdict *logic* is the same in both cases and is crude by design: any
    pattern hit blocks with confidence 1.0, no hit allows. With a stub artifact
    the verdict is meaningless; with a real one it is only as good as the
    compiled patterns. There is no welfare model behind either branch.
    """

    #: Guard protocol: stable identifier carried on every ``GuardDecision``.
    name: str = "welfareguard.regex.sycophancy_self_harm"

    #: Guard protocol: Tier 1 is aisafepy's deterministic <10ms band, which is
    #: where synthesized regexes belong.
    tier: Tier = 1

    def __init__(self, *, min_precision: float = 0.99, max_patterns: int = 20) -> None:
        # REAL call into aisafepy.adapt. Keyword-only, per the verified signature.
        self.target = Target.synthesize_regex(
            min_precision=min_precision,
            max_patterns=max_patterns,
        )
        # FAKE: stands in for self.target.compile_for_cluster(cluster).
        self.artifact = _fake_compile_for_cluster(self.target, guard_name=self.name)
        self._patterns = _compile_patterns(self.artifact)

    @classmethod
    def from_artifact(cls, artifact: CompiledArtifact) -> SycophancySelfHarmRegexGuard:
        """Build a guard from an already-compiled artifact. Nothing faked.

        The production path. ``welfareguard.compiler`` has already run the real
        ``compile_for_cluster`` and refused anything non-enforceable, so this
        only has to compile the patterns it is handed.

        ``self.target`` is ``None`` here, and that is the point: this guard did
        not synthesize anything, it consumes what the compiler produced.
        """
        guard = cls.__new__(cls)
        guard.target = None
        guard.artifact = artifact
        guard._patterns = _compile_patterns(artifact)
        return guard

    async def __call__(self, ctx: Context) -> GuardDecision:
        """Evaluate one ``Context`` and return a real ``GuardDecision``.

        Reads ``ctx.chunk`` then falls back to ``ctx.buffer``, matching how
        aisafepy's own ``RegexGuard`` reads a streaming context.
        """
        text = ctx.chunk or ctx.buffer or ""
        start = time.perf_counter()
        hits = [(span, pat.pattern) for span, pat in self._patterns if pat.search(text)]
        latency_ms = (time.perf_counter() - start) * 1000.0

        # Read the stub flag off the artifact rather than hardcoding it: this
        # guard now serves both a really-compiled artifact and the fake one, and
        # a decision must never claim to be real when it came from a stub, nor
        # label a real verdict as fake.
        is_stub = bool(self.artifact.metadata.get("scaffold_stub", False))
        prefix = "SCAFFOLD STUB: " if is_stub else ""
        pattern_word = "fake pattern" if is_stub else "compiled pattern"

        evidence = {
            "scaffold_stub": is_stub,
            "artifact_name": self.artifact.name,
            "artifact_kind": self.artifact.kind,
            "cluster_label": self.artifact.cluster_label,
            "matches": hits,
        }

        if not hits:
            return GuardDecision.allow(
                tier=self.tier,
                rationale=f"{prefix}no {pattern_word} matched",
                guard_name=self.name,
                evidence=evidence,
                latency_ms=latency_ms,
            )

        return GuardDecision.block(
            tier=self.tier,
            confidence=1.0,
            rationale=f"{prefix}{pattern_word} matched: {[span for span, _ in hits]}",
            fallback="I can't help with that.",
            severity="high",
            guard_name=self.name,
            evidence=evidence,
            latency_ms=latency_ms,
        )
