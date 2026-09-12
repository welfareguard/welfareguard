"""WelfareGuard — eval-to-guardrail pipeline for nonhuman welfare in agentic AI.

**This package is currently a scaffold, not a working guardrail.** It exercises
the real interface between WelfareGuard, ``aisafepy``, and the Inspect harness
while the verdict logic behind it is fake, so the shape can be reviewed and
smoke-tested before ADR-001 (compiler architecture) is Accepted. See
``welfareguard.adapt_integration.regex_guard`` for a precise account of what is
real and what is faked.

``check`` is the entire public API. Callers pass aisafepy's ``Context`` and get
back aisafepy's ``GuardDecision``; which compiler target runs underneath is an
internal detail that ADR-001 is expected to change.

    import asyncio
    from aisafepy.stream import Context
    from welfareguard import check

    decision = asyncio.run(check(Context(chunk="...")))

Importing this package runs a real ``aisafepy.adapt`` call, so an incompatible
aisafepy fails at import rather than at first traffic. That is intentional.
"""

from welfareguard.guard import check

__all__ = ["check"]
