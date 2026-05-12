#!/usr/bin/env python3
"""Verify generated benchmark harness artifacts stay out of the git worktree."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"
CMAKE = ROOT / "CMakeLists.txt"
REPORT = ROOT / "docs/reports/benchmark_generated_artifact_ignore_guard_20260512.md"

REQUIRED_PATTERNS = (
    "benchmarks/reference/",
    "benchmarks/raw/",
    "benchmarks/hardware_evidence/",
    "benchmarks/build_logs/",
    "benchmarks/results/",
)

SAMPLE_GENERATED_PATHS = (
    "benchmarks/reference/W1/PL1/seed_1001.parquet",
    "benchmarks/reference/MANIFEST.sha256",
    "benchmarks/raw/BD-geant4-001/W1/seed_1001.txt",
    "benchmarks/hardware_evidence/3048003.txt",
    "benchmarks/build_logs/BD-geant4-001_H3.txt",
    "benchmarks/results/results.parquet",
)

TRACKED_GENERATED_GLOBS = (
    "benchmarks/reference/*",
    "benchmarks/raw/*",
    "benchmarks/hardware_evidence/*",
    "benchmarks/build_logs/*",
    "benchmarks/results/*",
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_text(path: Path, marker: str) -> None:
    if marker not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {marker}")


def main() -> int:
    for pattern in REQUIRED_PATTERNS:
        require_text(GITIGNORE, pattern)

    for sample in SAMPLE_GENERATED_PATHS:
        result = git("check-ignore", "-q", sample, check=False)
        if result.returncode != 0:
            raise SystemExit(f"generated artifact is not ignored: {sample}")

    tracked = git("ls-files", *TRACKED_GENERATED_GLOBS).stdout.strip().splitlines()
    if tracked:
        details = "\n".join(tracked)
        raise SystemExit(f"generated benchmark artifact(s) unexpectedly tracked:\n{details}")

    for marker in (
        "g4gpu_benchmark_generated_artifact_ignores",
        "scripts/verify_benchmark_generated_artifact_ignores.py",
    ):
        require_text(CMAKE, marker)
        require_text(REPORT, marker)

    for marker in ("benchmarks/reference/", "benchmarks/raw/", "benchmarks/results/results.parquet"):
        require_text(REPORT, marker)

    print("BENCHMARK_GENERATED_ARTIFACT_IGNORES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
