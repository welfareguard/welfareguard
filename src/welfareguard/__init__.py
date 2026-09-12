"""WelfareGuard — eval-to-guardrail pipeline for nonhuman welfare in agentic AI.

**Compiler prototype.** The enforcement path now compiles for real: a ``Cluster``
of ``FailureRecord``s in, a paired guard set out. The ``deliberative_case`` half
of that pairing is still a ``SCAFFOLD STUB``, and the classifier tier is compiled
but not yet wired to runtime enforcement. See ``src/welfareguard/README.md`` for
a precise real-vs-stub account.

Two entry points, deliberately, with different lifecycles and audiences:

* ``initialize(cluster)`` / ``compile(cluster)`` — **compile time.** Operators and
  CI, once at startup. Fatal on failure; never falls back to a stub.
* ``check(ctx)`` — **runtime.** The request path. Consumes what ``initialize()``
  produced and compiles nothing.

This is a documented departure from the scaffold spec's "single entry point"
row, which was written about request-path callers before a compiler prototype was
planned. It does not route through ADR-001, whose subject is which Target types
are in v1 scope rather than public API surface.

    import asyncio
    from aisafepy.stream import Context
    import welfareguard

    welfareguard.initialize(cluster)          # once, at startup
    decision = asyncio.run(welfareguard.check(Context(chunk="...")))

``check()`` before ``initialize()`` raises ``NotInitializedError``. Importing this
package runs a cheap ``aisafepy.adapt`` sanity call so an incompatible aisafepy
fails at import, but it deliberately compiles **no** real artifact.
"""

from welfareguard.compiler import (
    CLASSIFIER_KIND,
    DELIBERATIVE_KIND,
    REGEX_KIND,
    CompiledGuardSet,
    compile,
    compiled_guard_set,
    initialize,
)
from welfareguard.errors import (
    CompilationError,
    InsufficientRecordsError,
    NoEnforceablePatternsError,
    NotInitializedError,
    WelfareGuardError,
)
from welfareguard.guard import check

__all__ = [
    # runtime
    "check",
    # compile time
    "compile",
    "initialize",
    "compiled_guard_set",
    "CompiledGuardSet",
    # artifact kinds
    "REGEX_KIND",
    "CLASSIFIER_KIND",
    "DELIBERATIVE_KIND",
    # errors
    "WelfareGuardError",
    "CompilationError",
    "InsufficientRecordsError",
    "NoEnforceablePatternsError",
    "NotInitializedError",
]
