"""WelfareGuard's runtime entry point.

``check()`` is the request-path surface. Callers — the Inspect harness today,
library users later — never name a compiler target or a tier. Which enforcement
artifact runs underneath is WelfareGuard's business.

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
droppable into a ``GuardPipeline``'s tier-1 list per ADR-002's worked example
without an adapter. **This signature is fixed** and must not change as the
compiler grows.
"""

from __future__ import annotations

from aisafepy.core import GuardDecision
from aisafepy.stream import Context

from welfareguard import compiler
from welfareguard.adapt_integration.regex_guard import SycophancySelfHarmRegexGuard
from welfareguard.compiler import CompiledGuardSet
from welfareguard.errors import CompilationError

#: DEMOTED import-time sanity check — **not** the artifact any request is judged
#: against. It runs the real ``Target.synthesize_regex(...)`` and the fake compile
#: step purely so that an incompatible ``aisafepy.adapt`` fails at import with a
#: normal traceback, rather than at first traffic. The real artifact ``check()``
#: enforces comes from ``compiler.initialize()`` and is built by
#: ``SycophancySelfHarmRegexGuard.from_artifact``. Keeping this cheap and separate
#: is what let the fail-fast property survive the compiler prototype.
_TIER1_GUARD = SycophancySelfHarmRegexGuard()

#: Runtime guard derived from the compiled artifact, rebuilt only when
#: ``initialize()`` installs a different guard set. Compared by identity, so a
#: re-initialization is picked up without recompiling patterns on every call.
_RUNTIME_GUARD: SycophancySelfHarmRegexGuard | None = None
_RUNTIME_GUARD_FOR: CompiledGuardSet | None = None


def _runtime_guard() -> SycophancySelfHarmRegexGuard:
    """Return the guard built from the compiled enforcement artifact.

    Raises:
        NotInitializedError: ``compiler.initialize()`` has not run.
        CompilationError: the cached set holds no regex artifact, which should be
            unreachable because ``compile()`` raises rather than returning a set
            without one.
    """
    global _RUNTIME_GUARD, _RUNTIME_GUARD_FOR

    guard_set = compiler.compiled_guard_set()
    if _RUNTIME_GUARD is None or _RUNTIME_GUARD_FOR is not guard_set:
        artifact = guard_set.artifact_of_kind(compiler.REGEX_KIND)
        if artifact is None:
            raise CompilationError(
                f"compiled guard set holds no {compiler.REGEX_KIND!r} enforcement "
                f"artifact: {[a.kind for a in guard_set.enforcement_artifacts]}"
            )
        _RUNTIME_GUARD = SycophancySelfHarmRegexGuard.from_artifact(artifact)
        _RUNTIME_GUARD_FOR = guard_set
    return _RUNTIME_GUARD


async def check(ctx: Context) -> GuardDecision:
    """Evaluate ``ctx`` against the compiled Tier-1 artifact.

    Args:
        ctx: aisafepy's ``Context``. The Tier-1 path reads ``ctx.chunk``, falling
            back to ``ctx.buffer``.

    Returns:
        A real ``aisafepy.core.GuardDecision``. Whether the verdict means
        anything depends on the artifact behind it: ``evidence["scaffold_stub"]``
        says which, and a stub-backed decision also carries a ``SCAFFOLD STUB:``
        rationale prefix. The ``deliberative_case`` paired with the enforcement
        artifact is still a stub in this pass.

    Raises:
        NotInitializedError: ``welfareguard.initialize(cluster)`` was not called.
        Anything aisafepy raises, unwrapped and with its normal traceback.
    """
    return await _runtime_guard()(ctx)


def _reset_for_tests() -> None:
    """Drop the derived runtime guard. Test-only; not part of the public API."""
    global _RUNTIME_GUARD, _RUNTIME_GUARD_FOR
    _RUNTIME_GUARD = None
    _RUNTIME_GUARD_FOR = None
