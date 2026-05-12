#!/usr/bin/env python3
"""Verify the EM/gamma deferred implementation roadmap."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
INDEX = ROOT / "docs/reports/em_gamma_deferred_contract_index_20260512.md"
REPORTS = (
    ROOT / "docs/reports/em_gamma_photoelectric_contract_20260512.md",
    ROOT / "docs/reports/em_gamma_pair_contract_20260512.md",
    ROOT / "docs/reports/em_gamma_bremsstrahlung_contract_20260512.md",
)
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
MATERIAL = ROOT / "include/g4gpu/MaterialData.hh"
TRACKS = ROOT / "include/g4gpu/G4GPUTrackBuffer.hh"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
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
        "Shared EM table owner",
        "Owned secondary buffer",
        "Process-selection contract",
        "Per-process implementations",
        "GPU validation and publication",
        "G4GPUEMPhysicsTables",
        "missing tables are detected",
        "capacity, overflow, and conservation tests",
        "gamma-always-Compton",
        "photoelectric first",
        "pair production",
        "bremsstrahlung",
        "archived logs",
        "sacct",
        "No NNBAR source",
        "physics-parity claim",
        "speedup claim",
    ):
        require(ROADMAP, marker)

    for marker in (
        "g4gpu_em_photoelectric_contract",
        "g4gpu_em_pair_contract",
        "g4gpu_em_bremsstrahlung_contract",
        "g4gpu_em_deferred_contract_index",
    ):
        require(INDEX, marker if marker != "g4gpu_em_deferred_contract_index" else "contract index")
        require(CMAKE, marker)

    for report in REPORTS:
        require(report, "Required implementation contract")
        require(report, "Validation gate")
        require(report, "Current fail-closed evidence")

    for marker in (
        "SampleCompton(tracks.ekin[i], material",
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
    ):
        require(KERNEL, marker)

    for forbidden in (
        "G4GPUEMPhysicsTables",
        "EMSecondaryBuffer",
        "secondary_buffer",
    ):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in ("Z_over_A", "I", "density", "X0", "name"):
        require(MATERIAL, marker)
    require(TRACKS, "struct TrackSOA")
    require_absent(TRACKS, "secondary")

    for marker in (
        "NAME g4gpu_em_implementation_roadmap",
        "scripts/verify_em_gamma_implementation_roadmap.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (ROADMAP, INDEX, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_IMPLEMENTATION_ROADMAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
