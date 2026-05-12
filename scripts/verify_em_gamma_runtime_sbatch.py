#!/usr/bin/env python3
"""Static verifier for the guarded EM/gamma GPU runtime sbatch wrapper."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SBATCH = ROOT / "slurm/em_gamma_runtime_gate.sbatch"
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
        "#SBATCH --job-name=g4gpu-em-rtgate",
        "#SBATCH --partition=gpua40i",
        "#SBATCH --gres=gpu:1",
        "EM_GAMMA_RUNTIME_APPROVED",
        "exit 2",
        "scripts/verify_em_gamma_runtime_gate.py",
        "ctest --test-dir",
        "g4gpu_em_klein_nishina",
        "cmake --build",
        "EM_GAMMA_RUNTIME_SLURM_OK",
    ):
        require(SBATCH, marker)

    for marker in (
        "NAME g4gpu_em_runtime_sbatch_contract",
        "scripts/verify_em_gamma_runtime_sbatch.py",
    ):
        require(CMAKE, marker)

    for path in (SBATCH, CMAKE, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_RUNTIME_SBATCH_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
