"""WelfareGuard's runtime layer — the ADR-002 cascade.

``cascade`` owns the runtime verdict contract from ADR-002
(docs/adr/ADR-002-runtime-design.md): two sequential tiers, Tier 1 blocks or
passes through, Tier 2 returns block, allow or escalate, escalate is
fail-closed, and the p95 latency budget is measured rather than enforced.

``pipeline`` registers the same guards in aisafepy's own ``GuardPipeline`` for
callers who already run one. The two differ in budget and error semantics; see
``pipeline.build_pipeline``.

Nothing here compiles anything. Both builders consume a ``CompiledGuardSet``
that ``welfareguard.compiler.initialize()`` produced.
"""

from welfareguard.runtime.cascade import (
    BUDGET_MS_P95,
    CascadeMode,
    WelfareCascade,
    build_cascade,
)
from welfareguard.runtime.pipeline import build_pipeline

__all__ = [
    "BUDGET_MS_P95",
    "CascadeMode",
    "WelfareCascade",
    "build_cascade",
    "build_pipeline",
]
