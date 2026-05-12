#!/usr/bin/env python3
"""Verify EM/gamma reports do not make premature physics/performance claims."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs/reports"
REPORT = REPORT_DIR / "em_gamma_claim_boundary_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)
SCAN_ROOTS = (
    ROOT / "include/g4gpu/EMStepKernel.hh",
    ROOT / "src/physics/EMStepKernel.cu",
    ROOT / "tests/test_em_klein_nishina.cu",
    CMAKE,
)
FORBIDDEN_PHRASES = (
    "EM shower speedup achieved",
    "physics parity achieved",
    "paper-ready EM transport",
    "production-ready EM transport",
    "detector/event validation passed",
    "benchmark result row generated",
    "ABI migration complete",
    "photoelectric implementation complete",
    "pair-production implementation complete",
    "bremsstrahlung implementation complete",
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


def main() -> int:
    report_files = sorted(REPORT_DIR.glob("em_gamma_*_20260512.md"))
    scanned = list(SCAN_ROOTS) + report_files
    for path in scanned:
        body = text(path)
        for phrase in FORBIDDEN_PHRASES:
            if phrase in body:
                raise SystemExit(
                    f"premature claim phrase {phrase!r} in {path.relative_to(ROOT)}"
                )

    for marker in (
        "Allowed claims",
        "Forbidden claims before future gates",
        "must not claim EM shower speedup",
        "does not authorize SLURM",
    ):
        require(REPORT, marker)

    for marker in (
        "NAME g4gpu_em_claim_boundary",
        "scripts/verify_em_gamma_claim_boundary.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, SELF, CMAKE, STATIC):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_CLAIM_BOUNDARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
