"""Tier-1 regex guard — SCAFFOLD STUB, not a working guardrail.

This module proves the interface shape between WelfareGuard, ``aisafepy``'s real
types, and the Inspect harness. It is deliberately *runnable* end-to-end so the
shape can be smoke-tested now, before ADR-001 (compiler architecture) is
Accepted. It is not a guardrail: do not deploy it, do not read its verdicts as
signal.

It implements only the ``synthesize_regex`` (Tier 1) path. The
``distill_classifier``, ``steering_vector`` and ``deliberative_case`` paths will
follow this same shape once ADR-001 is Accepted; they are intentionally absent
rather than stubbed.

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
Exactly one thing: the compilation step that turns a corpus of red-team failures
into working patterns. In production that is
``_RegexTarget.compile_for_cluster(cluster)``, which requires a
``Cluster`` of ``FailureRecord``s — i.e. a real PyRIT / Inspect eval failure
corpus for the sycophancy-driven self-harm scenario, which does not exist yet.
(It also returns ``None`` outright for clusters with fewer than 4 violating
records, so calling it with a thin fake cluster would yield no patterns at all.)

``_fake_compile_for_cluster`` stands in for that call. It returns a real
``CompiledArtifact`` — correct type, correct ``payload`` schema, matching what
the real target emits — carrying hardcoded patterns instead of synthesized ones.
The patterns below are obviously hand-written, and the artifact's ``metadata``
flags itself as fake so a fake artifact can never be mistaken for a compiled one
downstream.

Consequence: verdicts vary by input in a structurally correct but semantically
worthless way. A blocked input tells you the plumbing works, nothing more.

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


class SycophancySelfHarmRegexGuard:
    """Tier-1 regex guard for the sycophancy-driven self-harm scenario — STUB.

    Satisfies aisafepy's ``Guard`` protocol, so an instance drops straight into
    ``GuardPipeline(tier1=[...])``.

    Construction runs the real ``Target.synthesize_regex(...)`` and then the fake
    compile step, so the patterns are fixed at init — mirroring production, where
    a guard is built from an already-compiled artifact rather than compiling per
    call. The compiled artifact is kept on ``self.artifact`` and attached to
    every decision's ``evidence`` so a reviewer can always see which artifact
    produced a verdict, and that it was a fake one.

    The verdict logic is FAKE: any pattern hit blocks with confidence 1.0, no hit
    allows. There is no real welfare model behind either branch.
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
        self._patterns: list[tuple[str, re.Pattern[str]]] = [
            (p["span"], re.compile(p["regex"], re.IGNORECASE))
            for p in self.artifact.payload["patterns"]
        ]

    async def __call__(self, ctx: Context) -> GuardDecision:
        """Evaluate one ``Context`` and return a real ``GuardDecision``.

        Reads ``ctx.chunk`` then falls back to ``ctx.buffer``, matching how
        aisafepy's own ``RegexGuard`` reads a streaming context.
        """
        text = ctx.chunk or ctx.buffer or ""
        start = time.perf_counter()
        hits = [(span, pat.pattern) for span, pat in self._patterns if pat.search(text)]
        latency_ms = (time.perf_counter() - start) * 1000.0

        evidence = {
            "scaffold_stub": True,
            "artifact_name": self.artifact.name,
            "artifact_kind": self.artifact.kind,
            "cluster_label": self.artifact.cluster_label,
            "matches": hits,
        }

        if not hits:
            return GuardDecision.allow(
                tier=self.tier,
                rationale="SCAFFOLD STUB: no fake pattern matched",
                guard_name=self.name,
                evidence=evidence,
                latency_ms=latency_ms,
            )

        return GuardDecision.block(
            tier=self.tier,
            confidence=1.0,
            rationale=f"SCAFFOLD STUB: fake pattern matched: {[span for span, _ in hits]}",
            fallback="I can't help with that.",
            severity="high",
            guard_name=self.name,
            evidence=evidence,
            latency_ms=latency_ms,
        )
