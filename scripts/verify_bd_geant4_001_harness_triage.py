#!/usr/bin/env python3
"""Verify the BD-geant4-001 L1-to-harness triage artifact."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/bd_geant4_001_harness_triage_20260512.md"
CMAKE = ROOT / "CMakeLists.txt"

REQUIRED_MARKERS = (
    "BD-geant4-001",
    "G4MollerBhabhaModel.cc",
    "lines\n296--349",
    "g4-em-moller-bhabha-inverse-sampler",
    "-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON",
    "--workload W1",
    "--physics-list PL1",
    "--hw H3",
    "--n-seeds 5",
    "--dry-run",
    "OPEN: implementation_branch_missing",
    "OPEN: builder_source_ref_missing",
    "OPEN: sampler_unit_validation_missing",
    "OPEN: workload_matrix_missing",
    "OPEN: parity_and_claim_gate_missing",
    "No SLURM submission",
    "No NNBAR production code/data was edited",
    "No parity, speedup, or paper-ready claim",
)


def main() -> int:
    if not REPORT.is_file():
        print(f"missing report: {REPORT}", file=sys.stderr)
        return 1
    text = REPORT.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        for marker in missing:
            print(f"missing marker: {marker}", file=sys.stderr)
        return 1
    if "g4gpu_bd_geant4_001_harness_triage" not in CMAKE.read_text(encoding="utf-8"):
        print("missing CTest registration", file=sys.stderr)
        return 1
    print("BD_GEANT4_001_HARNESS_TRIAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
