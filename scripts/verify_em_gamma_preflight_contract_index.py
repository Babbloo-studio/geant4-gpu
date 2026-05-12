#!/usr/bin/env python3
"""Verify the EM/gamma shared preflight contract index."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/reports/em_gamma_preflight_contract_index_20260512.md"
REPORTS = {
    "table_owner": ROOT / "docs/reports/em_gamma_table_owner_preflight_20260512.md",
    "secondary_buffer": ROOT / "docs/reports/em_gamma_secondary_buffer_preflight_20260512.md",
    "rng_stream": ROOT / "docs/reports/em_gamma_rng_stream_preflight_20260512.md",
    "process_selector": ROOT / "docs/reports/em_gamma_process_selector_preflight_20260512.md",
    "status_code": ROOT / "docs/reports/em_gamma_status_code_preflight_20260512.md",
}
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


def require_order(path: Path, first: str, second: str) -> None:
    body = text(path)
    i = body.find(first)
    j = body.find(second)
    if i < 0 or j < 0 or i >= j:
        raise SystemExit(f"expected {first!r} before {second!r} in {path.relative_to(ROOT)}")


def main() -> int:
    for marker in (
        "Table owner",
        "Secondary buffer",
        "RNG stream",
        "Process selector",
        "Status code vocabulary",
        "SampleCompton` remains the only executable EM process",
        "fail-closed stubs",
        "Python verifier",
        "CTest target",
        "static\n  contract coverage",
        "does not imply Geant4 parity",
        "speedup claims",
    ):
        require(INDEX, marker)
    for first, second in (
        ("Table owner", "Secondary buffer"),
        ("Secondary buffer", "RNG stream"),
        ("RNG stream", "Process selector"),
        ("Process selector", "Status code vocabulary"),
    ):
        require_order(INDEX, first, second)

    expected = {
        "table_owner": ("G4GPUEMPhysicsTables", "g4gpu_em_table_owner_preflight"),
        "secondary_buffer": ("G4GPUEMSecondaryBuffer", "g4gpu_em_secondary_buffer_preflight"),
        "rng_stream": ("G4GPUEMRngStream", "g4gpu_em_rng_stream_preflight"),
        "process_selector": ("G4GPUEMProcessSelector", "g4gpu_em_process_selector_preflight"),
        "status_code": ("G4GPUEMStatusCode", "g4gpu_em_status_code_preflight"),
    }
    for key, (report_marker, ctest_name) in expected.items():
        require(REPORTS[key], report_marker)
        require(CMAKE, f"NAME {ctest_name}")
        require(STATIC, f"NAME {ctest_name}")

    for marker in (
        "SampleCompton(tracks.ekin[i], material",
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
    ):
        require(KERNEL, marker)
    for marker in ("SamplePhotoelectric", "SamplePair", "SampleBremsstrahlung"):
        require(STUB, marker)

    for marker in (
        "NAME g4gpu_em_preflight_contract_index",
        "scripts/verify_em_gamma_preflight_contract_index.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (INDEX, CMAKE, STATIC, SELF, *REPORTS.values()):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_PREFLIGHT_CONTRACT_INDEX_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
