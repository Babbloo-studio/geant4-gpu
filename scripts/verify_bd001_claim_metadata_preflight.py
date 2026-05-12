#!/usr/bin/env python3
"""Verify BD-geant4-001 claim-level metadata preflight is fail-closed."""
from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.harness.run import main as run_main

RUN = ROOT / "benchmarks/harness/run.py"
RUN_TEST = ROOT / "benchmarks/harness/tests/test_run.py"
REPORT = ROOT / "docs/reports/bd_geant4_001_claim_metadata_preflight_20260512.md"


def _run(args: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = run_main(args)
    return rc, out.getvalue(), err.getvalue()


def main() -> int:
    source = RUN.read_text(encoding="utf-8")
    for marker in (
        "from .schema import CLAIM_LEVELS",
        "claim_level=args.claim_level",
        "geant4_version=args.geant4_version",
        "notes=args.notes",
        "--claim-level must be one of",
        "--notes must be empty for L3 rows",
        "--geant4-version must be non-empty",
    ):
        if marker not in source:
            raise SystemExit(f"RUN_MARKER_MISSING {marker}")
    print("RUN_METADATA_MARKERS_OK")

    test_source = RUN_TEST.read_text(encoding="utf-8")
    for marker in (
        "test_dry_run_propagates_claim_metadata_to_sbatch",
        "BD-geant4-001",
        "CLAIM_LEVEL=L2",
        "GEANT4_VERSION=v11.2.2-bd001-preflight",
        "test_invalid_claim_metadata_fails_closed",
    ):
        if marker not in test_source:
            raise SystemExit(f"TEST_MARKER_MISSING {marker}")
    print("TEST_METADATA_MARKERS_OK")

    with tempfile.TemporaryDirectory(prefix="bd001-claim-preflight-") as tmp:
        rc, out, err = _run([
            "--opt-id", "BD-geant4-001",
            "--opt-branch", "lane/bd-geant4-001-moller-bhabha-inverse-sampler",
            "--opt-cmake-flags=-DG4GPU_BD001=ON",
            "--workload", "W1",
            "--physics-list", "PL2",
            "--hw", "H3",
            "--n-seeds", "1",
            "--repo-root", str(Path(tmp) / "repo"),
            "--claim-level", "L2",
            "--geant4-version", "v11.2.2-bd001-preflight",
            "--notes", "bd001 metadata preflight",
            "--dry-run",
        ])
    if rc != 0:
        raise SystemExit(f"DRY_RUN_RC_FAIL rc={rc} stderr={err}")
    for marker in (
        "CLAIM_LEVEL=L2",
        "GEANT4_VERSION=v11.2.2-bd001-preflight",
        "NOTES='bd001 metadata preflight'",
        '--claim-level "${CLAIM_LEVEL}"',
        '--geant4-version "${GEANT4_VERSION}"',
        '--notes "${NOTES}"',
    ):
        if marker not in out:
            raise SystemExit(f"DRY_RUN_MARKER_MISSING {marker}")
    if "Submitted batch job" in out or "sbatch" in err:
        raise SystemExit("UNEXPECTED_SUBMISSION_MARKER")
    print("DRY_RUN_METADATA_OK")

    rc, _out, err = _run([
        "--opt-id", "BD-geant4-001",
        "--opt-branch", "lane/bd001",
        "--workload", "W1",
        "--physics-list", "PL1",
        "--hw", "H3",
        "--claim-level", "L9",
    ])
    if rc != 2 or "--claim-level must be one of" not in err:
        raise SystemExit("INVALID_CLAIM_LEVEL_NOT_REJECTED")

    rc, _out, err = _run([
        "--opt-id", "BD-geant4-001",
        "--opt-branch", "lane/bd001",
        "--workload", "W1",
        "--physics-list", "PL1",
        "--hw", "H3",
        "--claim-level", "L3",
        "--notes", "not paper ready",
    ])
    if rc != 2 or "--notes must be empty for L3 rows" not in err:
        raise SystemExit("L3_NOTES_NOT_REJECTED")
    print("FAIL_CLOSED_METADATA_OK")

    if not REPORT.exists():
        raise SystemExit(f"MISSING_REPORT {REPORT}")
    report = REPORT.read_text(encoding="utf-8")
    for marker in (
        "BD-geant4-001",
        "Claim-level and metadata propagation",
        "PHYSICS_LIST",
        "unblock a measurement",
        "No SLURM",
    ):
        if marker not in report:
            raise SystemExit(f"REPORT_MARKER_MISSING {marker}")
    print("REPORT_MARKERS_OK")
    print("BD001_CLAIM_METADATA_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
