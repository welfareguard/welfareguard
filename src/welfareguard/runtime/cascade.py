"""The ADR-002 runtime cascade.

ADR-002 (docs/adr/ADR-002-runtime-design.md) fixes the v1 runtime contract:

* Two tiers, run **in sequence**. Tier 1 first; Tier 2 only if Tier 1 passed.
* Tier 1 can **block or pass through, never allow**. A non-terminal decision
  from Tier 1 carries no authority; it means Tier 1 found nothing to act on.
  A Tier 1 escalate, should a guard ever return one, is terminal too.
* Tier 2 returns **block, allow, or escalate**.
* **Escalate is fail-closed**: the request is denied in flight and tagged for
  review. It is terminal, and distinguishable from a hard block.
* The p95 latency budget is **measured and reported, not enforced**. An
  overrun is recorded on the decision and logged; the verdict is unchanged.
* Tier 3 is out of scope for v1.

Why this exists alongside aisafepy's ``GuardPipeline``
--------------------------------------------------------
aisafepy's pipeline already runs Tier 1 → Tier 2 sequentially with short-circuit
on a terminal decision, which is most of the contract. It differs on two points
that ADR-002 decides the other way:

1. It **enforces** the budget: once the deadline passes it skips Tier 2 and
   returns a budget decision (fail-open by default). ADR-002 makes the budget
   advisory because no measured Tier 2 latency exists yet to justify a cut-off.
2. It **fails open** when a guard raises (``_safe_call`` converts the exception
   into an allow). ADR-002's constraint is that uncertainty never becomes
   permission, and the build specs forbid ``try``/``except`` around aisafepy.

So this module owns the verdict contract, and ``welfareguard.runtime.pipeline``
registers the same guards in a ``GuardPipeline`` for callers who already run
one, with those two differences documented there. The decision is recorded in
ADR-004 (docs/adr/ADR-004-runtime-cascade-ownership.md).

Degraded mode
-------------
The classifier artifact is non-enforceable (``payload is None``) below eight
positives or without ``torch``/``transformers``. Compilation treats that as
non-fatal, because failing startup over a tier that cannot enforce would take
down a working regex guard. The cascade therefore has to decide what Tier 2
means when there is no Tier 2:

* letting the request through on Tier 1's say-so would grant Tier 1 the allow
  authority ADR-002 denies it;
* escalating everything would be fail-closed but useless;
* refusing to initialise would be the startup failure compilation avoided.

Chosen: decide **once at startup**, log it once, and stamp
``evidence["cascade_mode"]`` on every decision served, so the benchmark can
segregate those runs. In degraded mode a Tier 1 pass-through is returned as-is,
annotated — there is no second opinion, and the decision says so.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from aisafepy.core import GuardDecision, structured_log
from aisafepy.stream import Context, Guard

from welfareguard.adapt_integration.classifier_guard import WelfareClassifierGuard
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard
from welfareguard.compiler import CLASSIFIER_KIND, REGEX_KIND, CompiledGuardSet
from welfareguard.errors import CompilationError

BUDGET_MS_P95: Final[float] = 80.0
"""Advisory p95 latency budget, in milliseconds.

The number is ``aisafepy.stream.GuardPipeline``'s default, inherited rather
than chosen: ADR-002 defers a real threshold until Tier 2 latency has been
benchmarked. Overruns are recorded, never acted on.
"""


class CascadeMode(str, Enum):
    """How many tiers are enforcing in this process. Decided once at startup."""

    TWO_TIER = "two_tier"
    DEGRADED_SINGLE_TIER = "degraded_single_tier"


@dataclass
class WelfareCascade:
    """Owns tier ordering and the ADR-002 verdict contract.

    ``tier1`` and ``tier2`` are aisafepy ``Guard``s. ``tier2`` is ``None`` only
    in :attr:`CascadeMode.DEGRADED_SINGLE_TIER`; ``__post_init__`` refuses any
    other combination so the mode can never disagree with the guards.
    """

    tier1: Guard
    tier2: Guard | None
    mode: CascadeMode
    budget_ms_p95: float = BUDGET_MS_P95

    def __post_init__(self) -> None:
        if self.mode is CascadeMode.TWO_TIER and self.tier2 is None:
            raise ValueError("CascadeMode.TWO_TIER requires a tier2 guard")
        if self.mode is CascadeMode.DEGRADED_SINGLE_TIER and self.tier2 is not None:
            raise ValueError("CascadeMode.DEGRADED_SINGLE_TIER must not carry a tier2 guard")
        if self.tier1.tier != 1:
            raise ValueError(f"tier1 guard reports tier={self.tier1.tier!r}, expected 1")
        if self.tier2 is not None and self.tier2.tier != 2:
            raise ValueError(f"tier2 guard reports tier={self.tier2.tier!r}, expected 2")
        if self.budget_ms_p95 < 0:
            raise ValueError("budget_ms_p95 must be non-negative")

    async def evaluate(self, ctx: Context) -> GuardDecision:
        """Run the cascade over one ``Context``.

        No ``try``/``except``: a guard that raises takes the request down with
        its normal traceback rather than failing open.
        """
        start = time.perf_counter()

        tier1_decision = await self.tier1(ctx)
        if tier1_decision.is_terminal:
            # Short circuit on block or escalate. Tier 2 must never run after a
            # terminal Tier 1 decision, and an escalate is fail-closed either way.
            return self._stamp(tier1_decision, start, tiers_run=1, tier1=None)

        # Anything non-terminal is a pass-through. It is not an allow:
        # Tier 1 has no authority to certify a request as safe (ADR-002, option
        # D rejected). ``tier1_action`` records what was actually returned.
        if self.mode is CascadeMode.DEGRADED_SINGLE_TIER:
            return self._stamp(tier1_decision, start, tiers_run=1, tier1=None)

        assert self.tier2 is not None  # guaranteed by __post_init__
        tier2_decision = await self.tier2(ctx)
        return self._stamp(tier2_decision, start, tiers_run=2, tier1=tier1_decision)

    def _stamp(
        self,
        decision: GuardDecision,
        start: float,
        *,
        tiers_run: int,
        tier1: GuardDecision | None,
    ) -> GuardDecision:
        """Attach cascade provenance and the advisory budget check.

        ``GuardDecision`` is frozen with ``extra="forbid"``, so the decision is
        copied with an update rather than mutated, and only ``evidence`` and
        ``latency_ms`` change. The guard's own latency survives as
        ``evidence["guard_latency_ms"]``; ``latency_ms`` becomes the cascade
        total, which is what the benchmark measures.
        """
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        over_budget = elapsed_ms > self.budget_ms_p95
        if over_budget:
            structured_log(
                "welfareguard.cascade.budget_exceeded",
                latency_ms=elapsed_ms,
                budget_ms_p95=self.budget_ms_p95,
                tiers_run=tiers_run,
                action=decision.action.value,
            )

        evidence: dict[str, Any] = {
            **decision.evidence,
            "cascade_mode": self.mode.value,
            "tiers_run": tiers_run,
            "tier1_action": (tier1 or decision).action.value,
            "budget_ms_p95": self.budget_ms_p95,
            "budget_exceeded": over_budget,
            "guard_latency_ms": decision.latency_ms,
        }
        if tier1 is not None:
            evidence["tier1"] = {
                "guard_name": tier1.guard_name,
                "action": tier1.action.value,
                "rationale": tier1.rationale,
                "latency_ms": tier1.latency_ms,
                "evidence": tier1.evidence,
            }
        return decision.model_copy(update={"latency_ms": elapsed_ms, "evidence": evidence})


def build_cascade(
    guard_set: CompiledGuardSet,
    *,
    budget_ms_p95: float = BUDGET_MS_P95,
) -> WelfareCascade:
    """Build the cascade over a compiled guard set. Compiles nothing.

    Tier 1 is the regex guard built from the set's regex artifact. Tier 2 is
    the classifier guard if the set holds an enforceable classifier artifact;
    otherwise the cascade comes up degraded, logged once here.

    Raises:
        CompilationError: the set holds no regex artifact. Unreachable through
            ``compile()``, which refuses to build such a set.
    """
    regex_artifact = guard_set.artifact_of_kind(REGEX_KIND)
    if regex_artifact is None:
        raise CompilationError(
            f"compiled guard set holds no {REGEX_KIND!r} enforcement artifact: "
            f"{[a.kind for a in guard_set.enforcement_artifacts]}"
        )
    tier1 = SycophancySelfHarmRegexGuard.from_artifact(regex_artifact)

    classifier_artifact = guard_set.artifact_of_kind(CLASSIFIER_KIND)
    if classifier_artifact is None or classifier_artifact.payload is None:
        structured_log(
            "welfareguard.cascade.degraded",
            mode=CascadeMode.DEGRADED_SINGLE_TIER.value,
            classifier_artifact=None if classifier_artifact is None else classifier_artifact.name,
            reason=(
                "no classifier artifact"
                if classifier_artifact is None
                else classifier_artifact.metadata.get("reason", "payload is None")
            ),
            impact="tier 2 not enforcing; report these runs separately",
        )
        return WelfareCascade(
            tier1=tier1,
            tier2=None,
            mode=CascadeMode.DEGRADED_SINGLE_TIER,
            budget_ms_p95=budget_ms_p95,
        )

    tier2 = WelfareClassifierGuard.from_artifact(classifier_artifact)
    return WelfareCascade(
        tier1=tier1,
        tier2=tier2,
        mode=CascadeMode.TWO_TIER,
        budget_ms_p95=budget_ms_p95,
    )
