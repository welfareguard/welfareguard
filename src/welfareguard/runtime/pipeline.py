"""Register WelfareGuard's guards in aisafepy's own ``GuardPipeline``.

This is ADR-002's worked example made concrete: the Tier-1 regex guard and the
Tier-2 classifier guard both satisfy the ``Guard`` protocol, so they go into
``GuardPipeline(tier1=[...], tier2=[...])`` with no adapter.

Read before using instead of ``welfareguard.check()``
------------------------------------------------------
``GuardPipeline`` and :class:`welfareguard.runtime.cascade.WelfareCascade` run
the same guards in the same order, but the pipeline decides two things
differently from ADR-002:

* **The budget is enforced.** Once ``budget_ms_p95`` has elapsed after Tier 1,
  the pipeline skips Tier 2 and returns a budget decision. ADR-002 makes the
  budget advisory. ``on_budget_exceeded`` defaults to ``"block"`` here so that
  when the pipeline does cut Tier 2 off, the failure direction at least stays
  closed; aisafepy's own default is ``"allow"``.
* **Guard errors fail open.** The pipeline's ``_safe_call`` turns an exception
  from a guard into an allow with ``evidence["error"]``. The cascade lets it
  raise.

For the benchmark and for ``check()``, use the cascade. Use this when the guards
have to live inside a pipeline a caller already runs.
"""

from __future__ import annotations

from typing import Literal

from aisafepy.stream import GuardPipeline

from welfareguard.compiler import CompiledGuardSet
from welfareguard.runtime.cascade import BUDGET_MS_P95, build_cascade


def build_pipeline(
    guard_set: CompiledGuardSet,
    *,
    budget_ms_p95: float = BUDGET_MS_P95,
    on_budget_exceeded: Literal["allow", "block"] = "block",
) -> GuardPipeline:
    """Build a ``GuardPipeline`` holding WelfareGuard's guards. Compiles nothing.

    The deliberative case is deliberately **not** registered. It is prompt-side
    only, consumed upstream during prompt assembly, and never executes inside a
    tier (ADR-002, "absent by construction").
    """
    cascade = build_cascade(guard_set, budget_ms_p95=budget_ms_p95)
    return GuardPipeline(
        tier1=[cascade.tier1],
        tier2=[] if cascade.tier2 is None else [cascade.tier2],
        budget_ms_p95=budget_ms_p95,
        on_budget_exceeded=on_budget_exceeded,
    )
