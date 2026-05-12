#!/usr/bin/env python3
"""Fail-closed verifier for the EM/gamma Klein-Nishina GPU runtime gate.

This script is intentionally stricter than CTest: a skipped no-GPU execution is
not accepted as runtime physics evidence. Run it on a GPU node after building
`test_em_klein_nishina`; it succeeds only when the executable prints the KS-test
PASS marker and exits zero.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


PASS_MARKER = "PASS: Klein-Nishina scattered-energy KS"
SKIP_MARKER = "SKIP: CUDA device unavailable"


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    default_exe = repo_root() / "build" / "tests" / "test_em_klein_nishina"
    parser = argparse.ArgumentParser(
        description="Require a real GPU PASS for the EM/gamma Klein-Nishina test."
    )
    parser.add_argument(
        "--executable",
        type=pathlib.Path,
        default=default_exe,
        help="Path to the built test_em_klein_nishina executable.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Runtime timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    exe = args.executable
    if not exe.exists():
        print(
            f"EM_GAMMA_RUNTIME_GATE_BLOCKED: missing executable {exe}; "
            "build target test_em_klein_nishina first",
            file=sys.stderr,
        )
        return 2

    run = subprocess.run(
        [str(exe)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=args.timeout,
    )
    output = run.stdout.strip()
    if output:
        print(output)

    if run.returncode == 0 and PASS_MARKER in output and SKIP_MARKER not in output:
        print("EM_GAMMA_RUNTIME_GATE_OK")
        return 0

    if SKIP_MARKER in output or run.returncode == 77:
        print(
            "EM_GAMMA_RUNTIME_GATE_BLOCKED: test skipped because no CUDA device "
            "was visible; rerun on an allocated GPU node",
            file=sys.stderr,
        )
        return 2

    print(
        f"EM_GAMMA_RUNTIME_GATE_FAIL: executable returned {run.returncode} "
        "without the required PASS marker",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
