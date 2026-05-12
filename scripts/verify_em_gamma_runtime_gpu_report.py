#!/usr/bin/env python3
"""Verify the archived EM/gamma GPU runtime-gate evidence."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_runtime_gate_gpu_20260512.md"
CTEST = ROOT / "docs/reports/em_gamma_runtime_gate_gpu_3049900_ctest.txt"
GATE = ROOT / "docs/reports/em_gamma_runtime_gate_gpu_3049900_gate.txt"
SACCT = ROOT / "docs/reports/em_gamma_runtime_gate_gpu_3049900_sacct.txt"
CMAKE = ROOT / "CMakeLists.txt"
SELF = Path(__file__)


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text()


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(
            f"unexpected marker in {path.relative_to(ROOT)}: {needle}"
        )


def main() -> int:
    for marker in (
        "job 3049900",
        "c4ab69d3566f6003f3e1f86817ece1ba6b488545",
        "gpua40i",
        "cg15",
        "COMPLETED",
        "exit code `0:0`",
        "PASS: Klein-Nishina scattered-energy KS p=0.166506",
        "EM_GAMMA_RUNTIME_GATE_OK",
        "does not implement or\nvalidate photoelectric, pair-production, or bremsstrahlung",
        "does not claim\nphysics parity or speedup",
    ):
        require(REPORT, marker)

    for marker in (
        "g4gpu_em_klein_nishina",
        "Passed",
        "PASS: Klein-Nishina scattered-energy KS p=0.166506",
        "100% tests passed",
    ):
        require(CTEST, marker)

    for marker in (
        "PASS: Klein-Nishina scattered-energy KS p=0.166506",
        "EM_GAMMA_RUNTIME_GATE_OK",
    ):
        require(GATE, marker)

    for marker in (
        "3049900|g4gpu-em-rtgate|COMPLETED|0:0|00:00:27|cg15",
        "gres/gpu=1",
    ):
        require(SACCT, marker)

    for marker in (
        "NAME g4gpu_em_runtime_gpu_report",
        "scripts/verify_em_gamma_runtime_gpu_report.py",
    ):
        require(CMAKE, marker)

    for path in (REPORT, CTEST, GATE, SACCT, CMAKE, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_RUNTIME_GPU_REPORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
