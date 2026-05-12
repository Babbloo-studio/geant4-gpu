#!/usr/bin/env python3
"""Verify the fail-closed bremsstrahlung implementation contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_bremsstrahlung_contract_20260512.md"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
MATERIAL = ROOT / "include/g4gpu/MaterialData.hh"
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
        "TODO Phase 2.EM-bremsstrahlung",
        "G4GPUBremsstrahlungTable",
        "per-material monotonic lepton-energy grids",
        "differential photon-energy cumulative distribution functions",
        "configured photon-production cut",
        "EMInteractionResult.process = kBremsstrahlung",
        "keep charge and PDG\n   identity unchanged",
        "exactly one gamma",
        "EM secondary\n   buffer",
        "Silent photon dropping or\n   negative lepton energy is forbidden",
        "p > 0.05",
        "10,000 samples",
        "No `G4GPUBremsstrahlungTable` or EM secondary buffer exists",
    ):
        require(REPORT, marker)

    for marker in (
        "SampleBremsstrahlung",
        "TODO Phase 2.EM-bremsstrahlung",
        "out = {};",
        "return;",
    ):
        require(KERNEL, marker)

    for marker in (
        "SampleBremsstrahlung",
        "kBremsstrahlung",
        "secondary_pdg",
        "status",
    ):
        require(HEADER, marker)

    for marker in ("Z_over_A", "I", "density", "X0", "name"):
        require(MATERIAL, marker)

    for marker in (
        "NAME g4gpu_em_bremsstrahlung_contract",
        "scripts/verify_em_gamma_bremsstrahlung_contract.py",
    ):
        require(CMAKE, marker)

    for forbidden in ("G4GPUBremsstrahlungTable", "EMSecondaryBuffer"):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for path in (REPORT, KERNEL, HEADER, MATERIAL, CMAKE, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_BREMSSTRAHLUNG_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
