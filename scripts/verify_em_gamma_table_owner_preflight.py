#!/usr/bin/env python3
"""Verify the EM/gamma shared table-owner preflight stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_table_owner_preflight_20260512.md"
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
MATERIAL = ROOT / "include/g4gpu/MaterialData.hh"
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


def require_order(path: Path, first: str, second: str) -> None:
    body = text(path)
    i = body.find(first)
    j = body.find(second)
    if i < 0 or j < 0 or i >= j:
        raise SystemExit(
            f"expected {first!r} before {second!r} in {path.relative_to(ROOT)}"
        )


def main() -> int:
    for marker in (
        "G4GPUEMPhysicsTables",
        "off-by-default",
        "MaterialData ABI",
        "no `MaterialData` ABI field is changed",
        "Device pointer bundle",
        "host-side preflight",
        "photoelectric attenuation/shell accounting",
        "pair-production conversion and energy-share tables",
        "bremsstrahlung radiative-loss/emitted-photon tables",
        "Energy/material domain checks",
        "Missing-table gate",
        "labelled fail-closed status code",
        "do not mutate tracks",
        "explicit opt-in flag is required",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for marker in (
        "Shared EM table owner",
        "G4GPUEMPhysicsTables",
        "missing tables are detected",
        "Owned secondary buffer",
    ):
        require(ROADMAP, marker)
    require_order(ROADMAP, "Shared EM table owner", "Owned secondary buffer")

    for marker in ("Z_over_A", "I", "density", "X0", "name"):
        require(MATERIAL, marker)
    for forbidden in (
        "G4GPUEMPhysicsTables",
        "photoelectric_table",
        "pair_table",
        "bremsstrahlung_table",
    ):
        require_absent(MATERIAL, forbidden)

    for forbidden in ("G4GPUEMPhysicsTables", "EMPhysicsTableView"):
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in (
        "SamplePhotoelectric",
        "SamplePair",
        "SampleBremsstrahlung",
    ):
        require(STUB, marker)

    for marker in (
        "NAME g4gpu_em_table_owner_preflight",
        "scripts/verify_em_gamma_table_owner_preflight.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, ROADMAP, MATERIAL, HEADER, KERNEL, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_TABLE_OWNER_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
