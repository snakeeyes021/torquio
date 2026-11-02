#!/usr/bin/env python3
"""Compare Torquio before and after a change: python3 tests/parity/run.py [--base REF] [--show] [NAME...]

Runs every scenario in scenarios.py (or the named ones) in a copy of REF (default: develop) and in a copy
of the current working tree, and prints any difference. Exit code 0 when everything matches. See
harness.py for how the runs are isolated.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="develop", help="git ref to compare against (default: develop)")
    parser.add_argument("--show", action="store_true", help="print each scenario's output (after)")
    parser.add_argument("--keep", action="store_true", help="keep the scratch directory")
    parser.add_argument("names", nargs="*", help="scenarios to run (default: all)")
    args = parser.parse_args()

    scenarios = [s for s in SCENARIOS if not args.names or s["name"] in args.names]
    unknown = set(args.names) - {s["name"] for s in SCENARIOS}
    if unknown:
        parser.error(f"unknown scenario(s): {', '.join(sorted(unknown))}")

    failed = []
    with harness.Copies(REPO, args.base, keep=args.keep) as copies:
        for scenario in scenarios:
            before = harness.run_scenario(scenario, copies.base, copies.tmp)
            after = harness.run_scenario(scenario, copies.new, copies.tmp)
            lines = harness.diff(before, after, scenario["name"])
            print(f"{'ok  ' if not lines else 'DIFF'} {scenario['name']} (exit code {after['exit code']})")
            if args.show:
                print(after["output"])
            if lines:
                failed.append(scenario["name"])
                sys.stdout.writelines(lines)
                print()
    print(f"\n{len(scenarios) - len(failed)} of {len(scenarios)} scenarios match {args.base}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
