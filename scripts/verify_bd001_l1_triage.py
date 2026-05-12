#!/usr/bin/env python3
"""Verify BD-geant4-001 L1-to-harness triage remains fail-closed."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/bd_geant4_001_l1_harness_triage_20260512.md"
G4 = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
SOURCE = G4 / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
REQUIRED = [
    "BD-geant4-001",
    "G4MollerBhabhaModel::SampleSecondaries",
    "lines 266--350",
    "flatArray(2, rndm)",
    "implementation branch and registry metadata",
    "benchmarks/optimizations_registry.yaml",
    "lane/bd-geant4-001-moller-bhabha-inverse-sampler",
    "--workload W1",
    "--physics-list PL1 PL2 PL3 PL4",
    "--dry-run",
    "No SLURM",
    "parity claim",
]
FORBIDDEN = [
    "SPEEDUP:",
    "RESULT_COLLECTED",
    "Submitted batch job",
]


def run(cmd: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.STDOUT)


def main() -> int:
    if not REPORT.exists():
        raise SystemExit(f"MISSING_REPORT {REPORT}")
    text = REPORT.read_text(encoding="utf-8")
    for marker in REQUIRED:
        if marker not in text:
            raise SystemExit(f"MISSING_MARKER {marker}")
    for marker in FORBIDDEN:
        if marker in text:
            raise SystemExit(f"FORBIDDEN_MARKER {marker}")
    lines = len(text.splitlines())
    if lines > 500:
        raise SystemExit(f"LINE_CAP_FAIL report {lines}")
    print(f"REPORT_MARKERS_OK lines={lines}")

    if not SOURCE.exists():
        raise SystemExit(f"MISSING_GEANT4_SOURCE {SOURCE}")
    src = SOURCE.read_text(encoding="utf-8")
    for marker in ("G4MollerBhabhaModel::SampleSecondaries", "flatArray(2, rndm)", "while(grej * rndm[1] > z)"):
        if marker not in src:
            raise SystemExit(f"SOURCE_MARKER_MISSING {marker}")
    head = run(["git", "rev-parse", "HEAD"], cwd=G4).strip()
    if head != "f840b5da3a70c2c7be836fdb72a781eab12e0af6":
        raise SystemExit(f"GEANT4_HEAD_MISMATCH {head}")
    print("GEANT4_SOURCE_ANCHOR_OK")

    refs = run(["git", "show-ref"], cwd=ROOT)
    lowered = refs.lower()
    for needle in ("moller", "bhabha", "bd-geant4-001", "inverse-sampler"):
        if needle in lowered:
            raise SystemExit(f"UNEXPECTED_IMPLEMENTATION_REF {needle}")
    if (ROOT / "benchmarks/optimizations_registry.yaml").exists():
        raise SystemExit("UNEXPECTED_OPTIMIZATION_REGISTRY_PRESENT")
    print("IMPLEMENTATION_BRANCH_AND_REGISTRY_ABSENT_OK")
    print("BD001_L1_TRIAGE_FAIL_CLOSED_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
