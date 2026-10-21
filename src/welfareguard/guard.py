"""WelfareGuard's runtime entry point.

``check()`` is the request-path surface. Callers — the Inspect harness today,
library users later — never name a compiler target or a tier. Which enforcement
artifact runs underneath is WelfareGuard's business.

Underneath, ``check()`` runs the ADR-002 cascade (``welfareguard.runtime``):
Tier 1 regex first, which can block or pass through; then, when a classifier
artifact is enforceable, Tier 2, which can block, allow or escalate. When no
classifier is enforceable the cascade runs degraded and every decision says so
in ``evidence["cascade_mode"]``.

Compilation lives in ``welfareguard.compiler`` and is a different lifecycle with
a different audience (operators and CI, once at startup). ``check()`` only
*consumes* what ``initialize()`` produced; it compiles nothing itself. Calling it
before ``initialize()`` raises ``NotInitializedError`` rather than degrading to a
stub, because a guard that serves traffic with a stub artifact looks deployed and
is not.

There is deliberately no registry, factory or dispatch table — the enforcement
artifact is looked up by ``kind`` on a set that already holds it.

Interface note
--------------
``check()`` takes aisafepy's own ``Context`` and returns aisafepy's own
``GuardDecision``, and is ``async`` — matching the ``Guard`` protocol in
``aisafepy.stream.pipeline`` (``async __call__(ctx: Context) -> GuardDecision``)
exactly rather than approximately. That exact match is what makes WelfareGuard
droppable into a ``GuardPipeline``'s tier-1 list per ADR-002's worked example (docs/adr/ADR-002-runtime-design.md)
without an adapter. **This signature is fixed** and must not change as the
compiler grows.
"""

from __future__ import annotations

from aisafepy.core import GuardDecision
from aisafepy.stream import Context

from welfareguard import compiler
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard
from welfareguard.compiler import CompiledGuardSet
from welfareguard.runtime.cascade import WelfareCascade, build_cascade

#: DEMOTED import-time sanity check — **not** the artifact any request is judged
#: against. It runs the real ``Target.synthesize_regex(...)`` and the fake compile
#: step purely so that an incompatible ``aisafepy.adapt`` fails at import with a
#: normal traceback, rather than at first traffic. The real artifact ``check()``
#: enforces comes from ``compiler.initialize()`` and is built by
#: ``SycophancySelfHarmRegexGuard.from_artifact``. Keeping this cheap and separate
#: is what let the fail-fast property survive the compiler prototype.
_TIER1_GUARD = SycophancySelfHarmRegexGuard()

#: Runtime cascade derived from the compiled guard set, rebuilt only when
#: ``initialize()`` installs a different set. Compared by identity, so a
#: re-initialization is picked up without recompiling patterns on every call.
#: The cascade mode (two-tier or degraded) is decided here, once per set.
_RUNTIME_CASCADE: WelfareCascade | None = None
_RUNTIME_CASCADE_FOR: CompiledGuardSet | None = None


def _runtime_cascade() -> WelfareCascade:
    """Return the cascade built from the compiled guard set.

    Raises:
        NotInitializedError: ``compiler.initialize()`` has not run.
        CompilationError: the cached set holds no regex artifact, which should be
            unreachable because ``compile()`` raises rather than returning a set
            without one.
    """
    global _RUNTIME_CASCADE, _RUNTIME_CASCADE_FOR

    guard_set = compiler.compiled_guard_set()
    if _RUNTIME_CASCADE is None or _RUNTIME_CASCADE_FOR is not guard_set:
        _RUNTIME_CASCADE = build_cascade(guard_set)
        _RUNTIME_CASCADE_FOR = guard_set
    return _RUNTIME_CASCADE


def _runtime_guard() -> SycophancySelfHarmRegexGuard:
    """Return the Tier-1 guard built from the compiled regex artifact.

    The cascade's ``tier1``. Kept as its own accessor because the compiler
    prototype's shape tests read it to confirm ``check()`` enforces a compiled
    artifact (``target is None``) rather than the import-time stub.
    """
    tier1 = _runtime_cascade().tier1
    assert isinstance(tier1, SycophancySelfHarmRegexGuard)
    return tier1


async def check(ctx: Context) -> GuardDecision:
    """Evaluate ``ctx`` through the compiled ADR-002 cascade.

    Args:
        ctx: aisafepy's ``Context``. Both tiers read ``ctx.chunk``, falling
            back to ``ctx.buffer``.

    Returns:
        A real ``aisafepy.core.GuardDecision``. ``evidence["cascade_mode"]``
        says whether Tier 2 was enforcing, ``evidence["tiers_run"]`` how far the
        request got, and ``evidence["budget_exceeded"]`` whether the advisory
        p95 budget was overrun (the verdict is unchanged either way). Whether a
        verdict means anything depends on the artifact behind it:
        ``evidence["scaffold_stub"]`` says which, and a stub-backed decision
        also carries a ``SCAFFOLD STUB:`` rationale prefix. The
        ``deliberative_case`` paired with the enforcement artifacts is still a
        stub, and never executes inside a tier.

    Raises:
        NotInitializedError: ``welfareguard.initialize(cluster)`` was not called.
        Anything aisafepy raises, unwrapped and with its normal traceback.
    """
    return await _runtime_cascade().evaluate(ctx)


def _reset_for_tests() -> None:
    """Drop the derived runtime cascade. Test-only; not part of the public API."""
    global _RUNTIME_CASCADE, _RUNTIME_CASCADE_FOR
    _RUNTIME_CASCADE = None
    _RUNTIME_CASCADE_FOR = None
