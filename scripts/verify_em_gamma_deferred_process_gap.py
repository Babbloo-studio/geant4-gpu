#!/usr/bin/env python3
"""Verify the EM/gamma deferred-process gap audit is source-backed."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/em_gamma_deferred_process_gap_audit_20260512.md"
KERNEL = ROOT / "src/physics/EMStepKernel.cu"
HEADER = ROOT / "include/g4gpu/EMStepKernel.hh"
MATERIAL = ROOT / "include/g4gpu/MaterialData.hh"
TRACKS = ROOT / "include/g4gpu/G4GPUTrackBuffer.hh"
VALIDATION = ROOT / "docs/VALIDATION.md"


def require(path: Path, needle: str) -> None:
    text = path.read_text()
    if needle not in text:
        raise SystemExit(f"missing marker in {path.relative_to(ROOT)}: {needle}")


def require_absent(path: Path, needle: str) -> None:
    text = path.read_text()
    if needle in text:
        raise SystemExit(
            f"unexpected marker in {path.relative_to(ROOT)}: {needle}"
        )


def main() -> int:
    for path in (REPORT, KERNEL, HEADER, MATERIAL, TRACKS, VALIDATION):
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")

    for marker in (
        "TODO Phase 2.EM-photoelectric",
        "TODO Phase 2.EM-pair",
        "TODO Phase 2.EM-bremsstrahlung",
        "SampleCompton(tracks.ekin[i], material",
    ):
        require(KERNEL, marker)

    for symbol in (
        "SamplePhotoelectric",
        "SampleCompton",
        "SamplePair",
        "SampleBremsstrahlung",
        "LaunchEMStepKernel",
    ):
        require(HEADER, symbol)
        require(REPORT, symbol if symbol != "LaunchEMStepKernel" else "EMStep")

    for marker in (
        "Photoelectric absorption",
        "Pair production",
        "Bremsstrahlung",
        "Physics-table schema",
        "Secondary emission",
        "Process selection",
        "runtime gate",
    ):
        require(REPORT, marker)

    for scalar in ("Z_over_A", "I", "density", "X0"):
        require(MATERIAL, scalar)

    # Current TrackSOA has no secondary queue; this is the blocker that keeps
    # pair production and bremsstrahlung fail-closed.
    require(TRACKS, "struct TrackSOA")
    require_absent(TRACKS, "secondary")
    require_absent(TRACKS, "Secondaries")

    require(VALIDATION, "Kolmogorov-Smirnov test")
    require(VALIDATION, "N_events ≥ 10,000")

    for forbidden in ("NNBAR" + "_Detector", "nnbar" + "_reconstruction"):
        require_absent(REPORT, forbidden)

    print("EM_GAMMA_DEFERRED_PROCESS_GAP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
