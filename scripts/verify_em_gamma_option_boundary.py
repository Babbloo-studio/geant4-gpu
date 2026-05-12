#!/usr/bin/env python3
"""Verify EM/gamma CMake wiring stays inside the G4GPU_WITH_EM option."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
CTEST_BOUNDARY = ROOT / "scripts/verify_em_gamma_ctest_execution_boundary.py"
REPORT_COVERAGE = ROOT / "scripts/verify_em_gamma_report_coverage.py"
REPORT = ROOT / "docs/reports/em_gamma_option_boundary_20260512.md"
SELF = Path(__file__)

EM_SCOPE_MARKERS = (
    "G4GPU_WITH_EM=1",
    "src/physics/EMStepKernel.cu",
    "test_em_klein_nishina",
    "g4gpu_em_",
    "scripts/verify_em_gamma_",
)
REQUIRED_CMAKE_MARKERS = (
    "option(G4GPU_WITH_EM",
    "if(G4GPU_WITH_EM)",
    "target_sources(G4GPU PRIVATE src/physics/EMStepKernel.cu)",
    "add_test(NAME g4gpu_em_klein_nishina",
    "NAME g4gpu_em_option_boundary",
    "scripts/verify_em_gamma_option_boundary.py",
)


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="replace")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path.relative_to(ROOT)}: {needle}")


def em_guarded_lines(cmake_text: str) -> list[tuple[int, str]]:
    guarded: list[tuple[int, str]] = []
    stack: list[str] = []
    for lineno, raw in enumerate(cmake_text.splitlines(), start=1):
        line = raw.strip()
        if match := re.match(r"if\(([^)]+)\)", line, re.I):
            stack.append(match.group(1).strip())
        elif re.match(r"elseif\(", line, re.I):
            if stack:
                stack.pop()
            stack.append(line[7:-1].strip())
        elif re.match(r"else\(", line, re.I) or line.lower() == "else()":
            if stack:
                stack[-1] = f"NOT({stack[-1]})"
        elif re.match(r"endif\(", line, re.I) or line.lower() == "endif()":
            if stack:
                stack.pop()

        if any(marker in raw for marker in EM_SCOPE_MARKERS):
            if "option(G4GPU_WITH_EM" in raw:
                continue
            if "G4GPU_WITH_EM" not in stack:
                guarded.append((lineno, raw.rstrip()))
    return guarded


def main() -> int:
    cmake_body = text(CMAKE)
    for marker in REQUIRED_CMAKE_MARKERS:
        require(CMAKE, marker)

    leaked = em_guarded_lines(cmake_body)
    if leaked:
        details = "; ".join(f"{lineno}:{line}" for lineno, line in leaked)
        raise SystemExit(f"EM/gamma CMake marker outside G4GPU_WITH_EM scope: {details}")

    require(STATIC, "NAME g4gpu_em_option_boundary")
    require(STATIC, "scripts/verify_em_gamma_option_boundary.py")
    require(CTEST_BOUNDARY, "g4gpu_em_option_boundary")
    require(CTEST_BOUNDARY, "scripts/verify_em_gamma_option_boundary.py")
    require(REPORT_COVERAGE, "em_gamma_option_boundary_20260512.md")
    require(REPORT_COVERAGE, "scripts/verify_em_gamma_option_boundary.py")

    for marker in (
        "build-option boundary",
        "unreachable when `G4GPU_WITH_EM=OFF`",
        "does not authorize SLURM submission",
        "does not make speedup, parity, or\nproduction-readiness claims",
    ):
        require(REPORT, marker)

    for path in (REPORT, SELF, CMAKE, STATIC, CTEST_BOUNDARY, REPORT_COVERAGE):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_OPTION_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
