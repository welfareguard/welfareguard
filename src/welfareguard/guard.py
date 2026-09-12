"""WelfareGuard's single public entry point — SCAFFOLD, see ``regex_guard``.

``check()`` is the only public surface. Callers — the Inspect harness today,
library users later — never name a compiler target or a tier. Which Target type
runs underneath is WelfareGuard's business, and keeping that behind one function
is what lets ADR-001 change the answer without touching a single caller.

Right now the answer is always the same: the Tier-1 ``synthesize_regex`` path in
``welfareguard.adapt_integration.regex_guard``, reached by direct import. There
is deliberately no registry, factory or dispatch table. Multi-target selection
logic belongs inside ``check()`` once ADR-001 is Accepted; introducing the
lookup mechanism now would be pre-deciding ADR-001.

The verdict logic behind ``check()`` is fake. See ``regex_guard``'s module
docstring for exactly what is real and what is not.

Interface note
--------------
``check()`` takes aisafepy's own ``Context`` and returns aisafepy's own
``GuardDecision``, and is ``async`` — matching the ``Guard`` protocol in
``aisafepy.stream.pipeline`` (``async __call__(ctx: Context) -> GuardDecision``)
exactly rather than approximately. That exact match is the point: it is what
makes WelfareGuard droppable into a ``GuardPipeline``'s tier-1 list per
ADR-002's worked example without an adapter.
"""

from __future__ import annotations

from aisafepy.core import GuardDecision
from aisafepy.stream import Context

from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard

#: Built once at import, not per call — mirroring production, where a guard is
#: constructed from an already-compiled artifact rather than recompiling on
#: every request. Construction runs the real ``Target.synthesize_regex(...)``, so
#: if aisafepy's ``adapt`` interface moves, importing WelfareGuard fails
#: immediately and loudly rather than at first traffic.
_TIER1_GUARD = SycophancySelfHarmRegexGuard()


async def check(ctx: Context) -> GuardDecision:
    """Evaluate ``ctx`` and return a real ``GuardDecision``. STUB verdicts.

    Args:
        ctx: aisafepy's ``Context``. The Tier-1 path reads ``ctx.chunk``, falling
            back to ``ctx.buffer``.

    Returns:
        A real ``aisafepy.core.GuardDecision``. The structure is production-
        accurate; the verdict is not. Do not treat a ``block`` from this
        scaffold as a welfare finding.

    Raises:
        Whatever aisafepy raises. Nothing is caught or wrapped here, by design —
        this scaffold exists to surface integration breaks with their normal
        traceback.
    """
    return await _TIER1_GUARD(ctx)
