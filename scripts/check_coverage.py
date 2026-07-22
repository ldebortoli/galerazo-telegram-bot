from __future__ import annotations

import argparse
import json
from pathlib import Path


MINIMUM_STATEMENT_PERCENT = 62.0
MINIMUM_BRANCH_PERCENT = 36.0


def coverage_failures(totals: dict[str, object]) -> list[str]:
    statement_percent = float(totals["percent_statements_covered"])
    branch_percent = float(totals["percent_branches_covered"])
    failures: list[str] = []
    if statement_percent < MINIMUM_STATEMENT_PERCENT:
        failures.append(
            f"Statement coverage {statement_percent:.2f}% is below "
            f"{MINIMUM_STATEMENT_PERCENT:.2f}%"
        )
    if branch_percent < MINIMUM_BRANCH_PERCENT:
        failures.append(
            f"Branch coverage {branch_percent:.2f}% is below "
            f"{MINIMUM_BRANCH_PERCENT:.2f}%"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce statement and branch coverage thresholds."
    )
    parser.add_argument("report", nargs="?", default="coverage-report.json")
    args = parser.parse_args()

    report_path = Path(args.report)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    totals = report["totals"]
    failures = coverage_failures(totals)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print(
        "Coverage passed: "
        f"statements={float(totals['percent_statements_covered']):.2f}% "
        f"branches={float(totals['percent_branches_covered']):.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
