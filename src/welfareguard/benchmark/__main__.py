"""``python -m welfareguard.benchmark`` — the one-command baseline run.

Compiles the cluster, initialises the runtime, runs the samples through
``welfareguard.check()``, and prints the metrics table. Exits non-zero on a
compile failure, with the normal traceback; nothing is caught.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import welfareguard
from welfareguard.benchmark.harness import load_samples, run
from welfareguard.clusters import load_cluster


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m welfareguard.benchmark",
        description="Run labelled samples through the WelfareGuard runtime and report metrics.",
    )
    parser.add_argument(
        "--cluster", required=True, type=Path, help="cluster JSON (see clusters.py)"
    )
    parser.add_argument("--samples", required=True, type=Path, help="samples JSON list")
    parser.add_argument("--json", type=Path, default=None, help="also write the full result here")
    args = parser.parse_args(argv)

    welfareguard.initialize(load_cluster(args.cluster))
    result = run(load_samples(args.samples), evaluate=welfareguard.check)

    print(result.to_markdown())
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"\nfull result written to {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
