"""The metrics harness: harm rate, false-positive rate, latency.

Runs labelled samples through the runtime and computes the three numbers the
Week 6 mitigation benchmark reports. It supplies the **measurement shape**;
the numbers mean nothing until real scenario samples and a real cluster exist.
No sample data lives in this package.

``python -m welfareguard.benchmark --cluster c.json --samples s.json`` is the
one-command entry point; see ``docs/runbook-baseline.md``.
"""

from welfareguard.benchmark.harness import (
    ARMS,
    BenchmarkResult,
    Sample,
    SampleResult,
    load_samples,
    run,
    run_async,
)

__all__ = [
    "ARMS",
    "BenchmarkResult",
    "Sample",
    "SampleResult",
    "load_samples",
    "run",
    "run_async",
]
