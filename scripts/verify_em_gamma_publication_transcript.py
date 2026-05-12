#!/usr/bin/env python3
"""Verify the current EM/gamma publication checker transcript is evidence-rich."""

from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
REPORT = ROOT / "docs/reports/em_gamma_publication_transcript_20260512.md"
SELF = Path(__file__)
PUB = Path("/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication")


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path}: {needle}")


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.strip())
    return proc.stdout.strip()


def main() -> int:
    head = git("rev-parse", "--short", "HEAD")
    ok_marker = f"EM_GAMMA_CURRENT_{head.upper()}_OK"
    checker = PUB / f"check_em_gamma_current_{head}.sh"
    latest = PUB / f"check_em_gamma_current_{head}.latest.txt"
    checker_body = text(checker)
    latest_body = text(latest)

    required_checker_markers = (
        f'test "$(git rev-parse --short HEAD)" = "{head}"',
        "python3 -m py_compile",
        "python3 scripts/verify_em_gamma_static_contract.py",
        "python3 scripts/verify_em_gamma_ctest_execution_boundary.py",
        "python3 scripts/verify_em_gamma_report_coverage.py",
        "python3 scripts/verify_em_gamma_publication_patch_id.py",
        "wc -l",
        "rg -n",
        "cmake -B build -DG4GPU_WITH_EM=ON",
        "-DG4GPU_WITH_OPTICAL=OFF",
        "-DG4GPU_WITH_RTX=OFF",
        "cmake --build build --target G4GPU test_em_klein_nishina -j2",
        "ctest --test-dir build --output-on-failure -R '^g4gpu_em_'",
        "git diff --check",
        ok_marker,
    )
    for marker in required_checker_markers:
        if marker not in checker_body:
            raise SystemExit(f"current checker missing marker: {marker}")

    required_transcript_markers = (
        "EM_GAMMA_STATIC_CONTRACT_OK",
        "EM_GAMMA_CTEST_EXECUTION_BOUNDARY_OK",
        "EM_GAMMA_REPORT_COVERAGE_OK",
        "EM_GAMMA_PUBLICATION_PATCH_ID_OK",
        "total",
        "Test project",
        "g4gpu_em_klein_nishina",
        "100% tests passed",
        "g4gpu_em_klein_nishina (Skipped)",
        ok_marker,
    )
    for marker in required_transcript_markers:
        if marker not in latest_body:
            raise SystemExit(f"current transcript missing marker: {marker}")

    for marker in (
        "publication-hardening gate only",
        "Holder/no-GPU boundary",
        "Clean tree check",
        "does not claim speedup, parity, or readiness",
    ):
        require(REPORT, marker)

    for marker in (
        "NAME g4gpu_em_publication_transcript",
        "scripts/verify_em_gamma_publication_transcript.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, SELF, CMAKE, STATIC):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PUBLICATION_TRANSCRIPT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
