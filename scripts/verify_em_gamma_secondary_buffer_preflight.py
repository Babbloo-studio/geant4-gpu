#!/usr/bin/env python3
"""Verify the EM/gamma secondary-buffer preflight stays fail-closed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_secondary_buffer_preflight_20260512.md"
ROADMAP = ROOT / "docs/reports/em_gamma_implementation_roadmap_20260512.md"
TABLE = ROOT / "docs/reports/em_gamma_table_owner_preflight_20260512.md"
TRACKS = ROOT / "include/g4gpu/G4GPUTrackBuffer.hh"
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
        "G4GPUEMSecondaryBuffer",
        "off-by-default",
        "TrackSOA ABI",
        "no `TrackSOA` field is changed",
        "Capacity contract",
        "Atomic reservation contract",
        "Conservation contract",
        "Missing-buffer gate",
        "labelled fail-closed status code",
        "does not mutate primary tracks",
        "overflow is deterministic",
        "exactly one e-/e+ pair",
        "one emitted gamma",
        "physics-parity claims",
        "speedup claims",
    ):
        require(REPORT, marker)

    for marker in (
        "G4GPUEMPhysicsTables",
        "Missing-table gate",
        "do not mutate tracks",
    ):
        require(TABLE, marker)

    for marker in (
        "Shared EM table owner",
        "Owned secondary buffer",
        "Process-selection contract",
        "capacity, overflow, and conservation tests",
    ):
        require(ROADMAP, marker)
    require_order(ROADMAP, "Shared EM table owner", "Owned secondary buffer")
    require_order(ROADMAP, "Owned secondary buffer", "Process-selection contract")

    for marker in ("struct TrackSOA", "int size", "int capacity"):
        require(TRACKS, marker)
    for forbidden in (
        "G4GPUEMSecondaryBuffer",
        "EMSecondaryBuffer",
        "secondary_buffer",
    ):
        require_absent(TRACKS, forbidden)
        require_absent(HEADER, forbidden)
        require_absent(KERNEL, forbidden)

    for marker in ("SamplePair", "SampleBremsstrahlung", "must not mutate"):
        if marker == "must not mutate":
            require(REPORT, "does not mutate primary tracks")
        else:
            require(STUB, marker)

    for marker in (
        "NAME g4gpu_em_secondary_buffer_preflight",
        "scripts/verify_em_gamma_secondary_buffer_preflight.py",
    ):
        require(CMAKE, marker)
        require(STATIC, marker)

    for path in (REPORT, ROADMAP, TABLE, TRACKS, HEADER, KERNEL, CMAKE, STATIC, SELF):
        for forbidden in ("NN" "BAR" + "_Detector", "nnbar" + "_reconstruction"):
            require_absent(path, forbidden)

    print("EM_GAMMA_SECONDARY_BUFFER_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
