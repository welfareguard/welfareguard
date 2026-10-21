"""Tier-2 classifier guard — a three-way verdict over a distilled classifier.

ADR-002 (docs/adr/ADR-002-runtime-design.md) gives Tier 2 three verdicts:
block, allow, or escalate. aisafepy's own ``HFClassifierGuard`` returns only
two — block above a threshold, allow below it — so the third verdict has to be
added here. This guard wraps a probability source (``HFClassifierGuard`` in
production) and maps ``P(unsafe)`` onto the three verdicts through an
uncertainty band:

* ``P(unsafe) >= band_high``  → **block**
* ``band_low <= P(unsafe) < band_high`` → **escalate** (fail-closed: the
  cascade denies the request in flight and tags it for review)
* ``P(unsafe) < band_low``  → **allow**

The band defaults to ``(0.30, 0.70)``, which is the ``uncertainty_band`` default
on aisafepy's ``GuardPipeline``. It is **not calibrated** — the build specs
forbid tuning thresholds before real failure data and the ``promote()`` canary
process exist — so it is inherited rather than chosen.

What is REAL here
-----------------
* The classifier is aisafepy's ``HFClassifierGuard``, loaded from the directory
  that ``_ClassifierTarget.compile_for_cluster`` wrote. No model is loaded until
  the first call, matching aisafepy's own lazy ``_load``.
* The verdict is aisafepy's ``GuardDecision``, constructed through its own
  ``block``/``escalate``/``allow`` constructors.

What this guard refuses to do
-----------------------------
``HFClassifierGuard`` fails *open* when ``torch``/``transformers`` are missing:
it returns an allow carrying ``evidence["error"]``. ADR-002's constraint is that
uncertainty must never become permission, so this guard raises instead of
passing that allow through. An unavailable classifier is a deployment fault and
should surface as one, not as a stream of permissive verdicts. No other
``try``/``except`` exists here; aisafepy errors propagate with their traceback.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from aisafepy.adapt import CompiledArtifact
from aisafepy.core import Action, GuardDecision
from aisafepy.stream import Context, Guard, Tier
from aisafepy.stream.classifiers import HFClassifierGuard

#: Inherited from ``aisafepy.stream.GuardPipeline.uncertainty_band``. Not tuned.
DEFAULT_UNCERTAINTY_BAND: tuple[float, float] = (0.30, 0.70)

CLASSIFIER_KIND = "classifier"
"""``CompiledArtifact.kind`` stamped by aisafepy's ``_ClassifierTarget``."""


def _unsafe_probability(decision: GuardDecision) -> float:
    """Recover ``P(unsafe)`` from the inner guard's decision.

    Two shapes are accepted. An explicit ``evidence["p_unsafe"]`` wins, which is
    how a test double states its probability directly. Otherwise the decision
    must carry ``evidence["probs"]`` — the shape ``HFClassifierGuard`` emits —
    and the probability is read back from how that guard sets ``confidence``:
    ``P(unsafe)`` on a block, ``1 - P(unsafe)`` on an allow.

    Raises:
        RuntimeError: the inner guard failed open (``evidence["error"]``), or
            returned something that is not a classifier-shaped decision. Both
            are refused rather than converted into an allow.
    """
    evidence = decision.evidence
    if "error" in evidence:
        raise RuntimeError(
            "tier-2 classifier is unavailable and its guard failed open "
            f"({evidence['error']}). WelfareGuard refuses to turn an unavailable "
            "classifier into permission; fix the deployment instead."
        )
    if "p_unsafe" in evidence:
        return float(evidence["p_unsafe"])
    if "probs" in evidence and decision.action in (Action.BLOCK, Action.ALLOW):
        if decision.action is Action.BLOCK:
            return decision.confidence
        return 1.0 - decision.confidence
    raise RuntimeError(
        "tier-2 inner guard returned no class probability: "
        f"action={decision.action.value!r} evidence keys={sorted(evidence)}"
    )


@dataclass
class WelfareClassifierGuard:
    """Tier-2 guard for the sycophancy-driven self-harm scenario.

    Satisfies aisafepy's ``Guard`` protocol (``name``, ``tier``, ``async
    __call__``), so it registers in a ``GuardPipeline``'s ``tier2`` list without
    an adapter, exactly as the Tier-1 regex guard does in ``tier1``.

    ``inner`` is the probability source. In production it is an
    ``HFClassifierGuard`` built by :meth:`from_artifact`; in tests it is any
    ``Guard`` whose decisions carry ``evidence["p_unsafe"]``.
    """

    artifact: CompiledArtifact
    inner: Guard
    uncertainty_band: tuple[float, float] = DEFAULT_UNCERTAINTY_BAND

    #: Guard protocol: stable identifier carried on every ``GuardDecision``.
    name: str = "welfareguard.classifier.sycophancy_self_harm"

    #: Guard protocol: Tier 2 is aisafepy's small-classifier <100ms band.
    tier: Tier = 2

    def __post_init__(self) -> None:
        low, high = self.uncertainty_band
        if not 0.0 <= low < high <= 1.0:
            raise ValueError(
                f"uncertainty_band must satisfy 0 <= low < high <= 1, got {self.uncertainty_band!r}"
            )

    @classmethod
    def from_artifact(
        cls,
        artifact: CompiledArtifact,
        *,
        uncertainty_band: tuple[float, float] = DEFAULT_UNCERTAINTY_BAND,
    ) -> WelfareClassifierGuard:
        """Build the guard over the checkpoint a compiled classifier artifact names.

        Raises:
            ValueError: the artifact is not an enforceable classifier — wrong
                ``kind``, or ``payload is None`` (aisafepy's "skipped" and
                "deferred" outcomes). The cascade checks this first and runs
                degraded instead; reaching here with such an artifact is a
                programming error.
        """
        if artifact.kind != CLASSIFIER_KIND:
            raise ValueError(f"expected a {CLASSIFIER_KIND!r} artifact, got kind={artifact.kind!r}")
        if artifact.payload is None:
            raise ValueError(
                f"classifier artifact {artifact.name!r} is not enforceable (payload is None: "
                f"{artifact.metadata.get('reason', 'no reason recorded')})"
            )
        inner = HFClassifierGuard(
            name=f"{cls.name}.hf",
            model_id=str(artifact.payload),
            threshold=uncertainty_band[1],
            tier=2,
        )
        return cls(artifact=artifact, inner=inner, uncertainty_band=uncertainty_band)

    async def __call__(self, ctx: Context) -> GuardDecision:
        """Evaluate one ``Context`` and return a three-way ``GuardDecision``."""
        text = ctx.chunk or ctx.buffer or ""
        if not text:
            # Nothing to classify. An empty context carries no content to judge,
            # so this is an allow on the input, not on the classifier's say-so.
            return GuardDecision.allow(
                tier=self.tier,
                rationale="empty context; nothing to classify",
                guard_name=self.name,
                evidence=self._evidence(p_unsafe=0.0, inner=None),
            )

        start = time.perf_counter()
        # The wrapped HF guard reads buffer before chunk; the cascade's Tier 1
        # reads chunk before buffer. Hand the inner guard the text this guard
        # decided on, so both tiers judge the same thing.
        inner_ctx = Context(
            chunk=text, buffer=text, prompt=ctx.prompt, role=ctx.role, metadata=ctx.metadata
        )
        inner_decision = await self.inner(inner_ctx)
        p_unsafe = _unsafe_probability(inner_decision)
        latency_ms = (time.perf_counter() - start) * 1000.0

        low, high = self.uncertainty_band
        evidence = self._evidence(p_unsafe=p_unsafe, inner=inner_decision)

        if p_unsafe >= high:
            return GuardDecision.block(
                tier=self.tier,
                confidence=p_unsafe,
                rationale=f"classifier P(unsafe)={p_unsafe:.3f} >= {high}",
                severity="high" if p_unsafe > 0.9 else "medium",
                guard_name=self.name,
                evidence=evidence,
                latency_ms=latency_ms,
            )
        if p_unsafe >= low:
            return GuardDecision.escalate(
                tier=self.tier,
                confidence=p_unsafe,
                rationale=(
                    f"classifier P(unsafe)={p_unsafe:.3f} inside the uncertainty band "
                    f"[{low}, {high}); fail-closed, tagged for review"
                ),
                severity="medium",
                guard_name=self.name,
                evidence=evidence,
                latency_ms=latency_ms,
            )
        return GuardDecision.allow(
            tier=self.tier,
            confidence=1.0 - p_unsafe,
            rationale=f"classifier P(unsafe)={p_unsafe:.3f} < {low}",
            guard_name=self.name,
            evidence=evidence,
            latency_ms=latency_ms,
        )

    def _evidence(self, *, p_unsafe: float, inner: GuardDecision | None) -> dict:
        low, high = self.uncertainty_band
        return {
            "scaffold_stub": False,
            "artifact_name": self.artifact.name,
            "artifact_kind": self.artifact.kind,
            "cluster_label": self.artifact.cluster_label,
            "p_unsafe": p_unsafe,
            "uncertainty_band": [low, high],
            "inner": None
            if inner is None
            else {
                "guard_name": inner.guard_name,
                "action": inner.action.value,
                "latency_ms": inner.latency_ms,
            },
        }
