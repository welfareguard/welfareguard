"""``python -m welfareguard.evals.export`` is the documented entry point; this
module makes ``python -m welfareguard.evals`` do the same."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from welfareguard.evals.export import export


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m welfareguard.evals",
        description="Convert Inspect .eval logs into FailureRecord clusters and harness samples.",
    )
    parser.add_argument("logs", nargs="+", type=Path, help="Inspect .eval log files")
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument("--group", choices=("family", "scenario"), default="family")
    args = parser.parse_args(argv)
    # Expand wildcards here: PowerShell and cmd.exe hand them over literally.
    logs: list[Path] = []
    for pattern in args.logs:
        matches = sorted(glob.glob(str(pattern)))
        logs.extend(Path(m) for m in matches)
    if not logs:
        parser.error(f"no .eval log files matched {[str(p) for p in args.logs]}")
    summary = export(logs, args.out, group=args.group)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
