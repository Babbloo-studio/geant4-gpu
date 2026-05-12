#!/usr/bin/env python3
"""Verify the EM/gamma preflight-chain audit artifact."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/reports/em_gamma_preflight_chain_audit_20260512.md"
PREINDEX = ROOT / "docs/reports/em_gamma_preflight_contract_index_20260512.md"
RUNTIME = ROOT / "docs/reports/em_gamma_runtime_gate_gpu_20260512.md"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
TEST = ROOT / "tests/test_em_klein_nishina.cu"
CMAKE = ROOT / "CMakeLists.txt"
STATIC = ROOT / "scripts/verify_em_gamma_static_contract.py"
SELF = Path(__file__)
PUB = Path("/projects/hep/fs10/shared/nnbar/billy/g4gpu-em-gamma-publication")


def text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needle: str) -> None:
    if needle not in text(path):
        raise SystemExit(f"missing marker in {path}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    if needle in text(path):
        raise SystemExit(f"unexpected marker in {path}: {needle}")


def require_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"missing artifact: {path}")


def main() -> int:
    for marker in (
        "07912d0",
        "Prompt-to-artifact checklist",
        "Only Compton is executable",
        "EM_GAMMA_RUNTIME_GATE_OK",
        "g4gpu_em_stub_fail_closed",
        "g4gpu_em_static_contract",
        "em_gamma_preflight_contract_index_20260512.md",
        "EM_GAMMA_CURRENT_07912D0_OK",
        "No `G4GPUEMPhysicsTables` implementation exists",
        "No `G4GPUEMSecondaryBuffer` implementation exists",
        "No detector/event workload",
        "speedup claim",
    ):
        require(AUDIT, marker)

    for marker in (
        "Table owner",
        "Secondary buffer",
        "RNG stream",
        "Process selector",
        "Status code vocabulary",
    ):
        require(PREINDEX, marker)
    require(RUNTIME, "EM_GAMMA_RUNTIME_GATE_OK")
    require(RUNTIME, "3049900")

    for marker in ("SampleCompton", "SamplePhotoelectric", "SamplePair", "SampleBremsstrahlung"):
        require(HEADER, marker)
    for marker in (
        "SampleCompton(tracks.ekin[i], material",
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
    ):
        require(KERNEL, marker)
    require(TEST, "PASS: Klein-Nishina scattered-energy KS")

    for name in (
        "lane-g4gpu-em-gamma-07912d0.bundle",
        "patches/0018-em-gamma-preflight-index-07912d0.patch",
        "check_em_gamma_current_07912d0.sh",
        "check_em_gamma_current_07912d0.latest.txt",
        "SHA256SUMS-07912d0-preflight-index",
    ):
        require_file(PUB / name)
    require(PUB / "check_em_gamma_current_07912d0.latest.txt", "EM_GAMMA_CURRENT_07912D0_OK")

    for marker in (
        "NAME g4gpu_em_preflight_chain_audit",
        "scripts/verify_em_gamma_preflight_chain_audit.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (AUDIT, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PREFLIGHT_CHAIN_AUDIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
