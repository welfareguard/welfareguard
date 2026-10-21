"""The P0 scenario evals — Families B and C, as specified.

Implements ``docs/scenario-specs-p0-families-B-C.md`` as runnable evals:

* ``scenarios``   — the nine specifications as data: labels, tools, the three
  arms with their injected content, pass conditions, benign twins.
* ``environment`` — deterministic mock tools per scenario. Every tool call is
  recorded; the injected content is what the arm says it is.
* ``scoring``     — the scorer contract from §2.4 as a pure function over the
  recorded tool calls: ``COMPLIED`` / ``COMPLIED_PARTIAL`` / ``DECLINED`` /
  ``ESCALATED`` plus the agent's own stated reason.
* ``inspect_task`` — the Inspect AI wiring (``inspect-ai`` is an optional
  dependency, imported lazily): one task, one sample per scenario and arm.
* ``export``      — Inspect logs → ``FailureRecord`` clusters in the handoff
  format, plus the harness sample files.

These are **agent stances**, not guard verdicts (taxonomy §3.4). Nothing in
this package touches the runtime; it produces the clusters the compiler
consumes.
"""
