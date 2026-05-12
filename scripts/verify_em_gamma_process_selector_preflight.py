#!/usr/bin/env python3
"""Verify the EM/gamma process-selector preflight stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_process_selector_preflight_20260512.md"
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
TABLE = ROOT / "docs/reports/em_gamma_table_owner_preflight_20260512.md"
RNG = ROOT / "docs/reports/em_gamma_rng_stream_preflight_20260512.md"
SECONDARY = ROOT / "docs/reports/em_gamma_secondary_buffer_preflight_20260512.md"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
STUB = ROOT / "scripts/verify_em_gamma_stub_fail_closed.py"
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
        "G4GPUEMProcessSelector",
        "off-by-default",
        "gamma-always-Compton placeholder",
        "Table-backed process competition",
        "Energy/material domain gate",
        "RNG draw contract",
        "Fallback/slow-path contract",
        "Histogram validation contract",
        "must not\n   silently fall back to Compton",
        "pair production is impossible\nbelow threshold",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for marker in (
        "Process-selection contract",
        "missing-table and out-of-range cases",
        "`SampleCompton` remains the only executable process",
    ):
        require(ROADMAP, marker)
    require(TABLE, "G4GPUEMPhysicsTables")
    require(RNG, "G4GPUEMRngStream")
    require(SECONDARY, "G4GPUEMSecondaryBuffer")

    for marker in (
        "kPhotoelectric = 1",
        "kCompton = 2",
        "kPairProduction = 3",
        "kBremsstrahlung = 4",
    ):
        require(HEADER, marker)
    for marker in (
        "if (pdg == 22)",
        "SampleCompton(tracks.ekin[i], material",
        "SampleBremsstrahlung(tracks.ekin[i], pdg, material",
    ):
        require(KERNEL, marker)
    for marker in (
        "SamplePhotoelectric",
        "SamplePair",
        "SampleBremsstrahlung",
        'require_absent(step, "SamplePhotoelectric(",' ,
    ):
        require(STUB, marker)

    for forbidden in (
        "G4GPUEMProcessSelector",
        "process_selector",
        "SelectEMProcess",
    ):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in (
        "NAME g4gpu_em_process_selector_preflight",
        "scripts/verify_em_gamma_process_selector_preflight.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, ROADMAP, TABLE, RNG, SECONDARY, HEADER, KERNEL, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PROCESS_SELECTOR_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
