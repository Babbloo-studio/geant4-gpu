#!/usr/bin/env python3
"""Verify benchmark-harness files stay below the compact 500-line cap."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 500
REPORT = ROOT / "docs/reports/benchmark_harness_line_cap_guard_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"
SCRIPT = ROOT / "scripts/verify_benchmark_harness_line_caps.py"
WATCH_ROOTS = [ROOT / "benchmarks/harness"]
SUFFIXES = {".py", ".md", ".yaml", ".yml", ".txt"}


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def iter_watched_files() -> list[Path]:
    files: list[Path] = []
    for root in WATCH_ROOTS:
        for path in sorted(root.rglob("*")):
            if "__pycache__" in path.parts or not path.is_file():
                continue
            if path.suffix in SUFFIXES:
                files.append(path)
    return files


def require(path: Path, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"missing marker in {path}: {marker}")


def main() -> int:
    offenders = [(path, line_count(path)) for path in iter_watched_files() if line_count(path) > CAP]
    if offenders:
        details = "\n".join(f"{count:4d} {path.relative_to(ROOT)}" for path, count in offenders)
        raise SystemExit(f"benchmark harness line-cap violation(s):\n{details}")

    for marker in (
        "g4gpu_benchmark_harness_line_caps",
        "scripts/verify_benchmark_harness_line_caps.py",
    ):
        require(CMAKE, marker)
        require(REPORT, marker)

    for marker in ("7f13adf", "benchmarks/harness/run_helpers.py", "test_run_bd001_registry.py"):
        require(REPORT, marker)

    print("BENCHMARK_HARNESS_LINE_CAPS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
