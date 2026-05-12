#!/usr/bin/env python3
"""Verify the EM/gamma deferred-process contract index."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/reports/em_gamma_deferred_contract_index_20260512.md"
REPORTS = {
    "photoelectric": ROOT / "docs/reports/em_gamma_photoelectric_contract_20260512.md",
    "pair": ROOT / "docs/reports/em_gamma_pair_contract_20260512.md",
    "bremsstrahlung": ROOT / "docs/reports/em_gamma_bremsstrahlung_contract_20260512.md",
}
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
STUB = ROOT / "scripts/verify_em_gamma_stub_fail_closed.py"
GAP = ROOT / "scripts/verify_em_gamma_deferred_process_gap.py"
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
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
        "g4gpu_em_photoelectric_contract",
        "g4gpu_em_pair_contract",
        "g4gpu_em_bremsstrahlung_contract",
        "No `G4GPUEMPhysicsTable`",
        "No `G4GPUPairProductionTable`",
        "No `G4GPUBremsstrahlungTable`",
        "not a detector/event run",
        "physics-parity claim",
        "speedup claim",
    ):
        require(INDEX, marker)

    for name, report in REPORTS.items():
        require(INDEX, str(report.relative_to(ROOT)))
        require(report, "Required implementation contract")
        require(report, "Current fail-closed evidence")
        require(report, "Follow-up sequence")
        require(report, "p > 0.05")
        if name == "photoelectric":
            require(report, "G4GPUEMPhysicsTable")
        elif name == "pair":
            require(report, "G4GPUPairProductionTable")
        else:
            require(report, "G4GPUBremsstrahlungTable")

    for marker in (
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
        "out = {};",
        "return;",
    ):
        require(KERNEL, marker)

    for forbidden in (
        "G4GPUEMPhysicsTable",
        "G4GPUPairProductionTable",
        "G4GPUBremsstrahlungTable",
        "EMSecondaryBuffer",
    ):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in (
        "NAME g4gpu_em_deferred_contract_index",
        "scripts/verify_em_gamma_deferred_contract_index.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for marker in (
        "NAME g4gpu_em_photoelectric_contract",
        "NAME g4gpu_em_pair_contract",
        "NAME g4gpu_em_bremsstrahlung_contract",
    ):
        require(CMAKE, marker)

    for marker in ("verify_stub", "SamplePhotoelectric", "SamplePair", "SampleBremsstrahlung"):
        require(STUB, marker)
    require(GAP, "require_absent(TRACKS, \"secondary\")")

    for path in (INDEX, CMAKE, STATIC, STUB, GAP, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_DEFERRED_CONTRACT_INDEX_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
