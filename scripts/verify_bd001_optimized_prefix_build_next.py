#!/usr/bin/env python3
"""Verify BD001 optimized-prefix build-next remains fail-closed."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
PREFIX = Path("/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4")
CONFIG = PREFIX / "lib/cmake/Geant4/Geant4Config.cmake"
WRAPPER = ROOT / "scripts/prepare_bd001_optimized_prefix.sh"
REPORT = ROOT / "docs/reports/bd_geant4_001_optimized_prefix_build_next_20260513.md"
RESULTS = ROOT / "benchmarks/results/results.parquet"
SOURCE_COMMIT = "4ac150b"
HANDOFF_HEAD = "782d84c"
CMAKE_FLAG = "-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON"
TARGET = "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
BUILD_SETTINGS = "cmake/Modules/G4BuildSettings.cmake"


def _run(
    args: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(args, cwd=cwd, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and proc.returncode != 0:
        raise AssertionError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}")
    return proc


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def _require(label: str, text: str, markers: tuple[str, ...]) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{label} missing markers: {missing}")


def _require_source_refs() -> None:
    if not (SOURCE_REPO / ".git").is_dir():
        raise AssertionError(f"missing source repo: {SOURCE_REPO}")
    head = _run(["git", "-C", str(SOURCE_REPO), "rev-parse", "--short=7", "HEAD"]).stdout.strip()
    if head != HANDOFF_HEAD:
        raise AssertionError(f"wrong source head: expected {HANDOFF_HEAD}, got {head}")
    source = _run(["git", "-C", str(SOURCE_REPO), "rev-parse", "--short=7", f"{SOURCE_COMMIT}^{{commit}}"]).stdout.strip()
    _run(["git", "-C", str(SOURCE_REPO), "merge-base", "--is-ancestor", SOURCE_COMMIT, HANDOFF_HEAD])
    build_settings = _run(["git", "-C", str(SOURCE_REPO), "show", f"{HANDOFF_HEAD}:{BUILD_SETTINGS}"]).stdout
    target = _run(["git", "-C", str(SOURCE_REPO), "show", f"{HANDOFF_HEAD}:{TARGET}"]).stdout
    _require("build settings", build_settings, ("option(G4EM_MOLLER_BHABHA_INVERSE_SAMPLER", "geant4_add_feature"))
    _require("target", target, ("G4EM_MOLLER_BHABHA_INVERSE_SAMPLER", "flatArray(2, rndm)"))
    print(f"BD001_OPTIMIZED_PREFIX_BUILD_NEXT_SOURCE_OK source={source} handoff={head}")


def _require_wrapper_guards() -> None:
    wrapper = _read(WRAPPER)
    _require(
        "wrapper",
        wrapper,
        (
            "BD001_OPTIMIZED_PREFIX_BUILD_APPROVED",
            "BD001_ALLOW_NON_SLURM_PREFIX_BUILD",
            "SLURM_JOB_ID",
            "BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED",
            "BD001_OPTIMIZED_PREFIX_COMPUTE_GUARD",
            "BD001_OPTIMIZED_PREFIX_NONEMPTY",
            "BD001_OPTIMIZED_PREFIX_BUILD_OK",
            SOURCE_COMMIT,
            HANDOFF_HEAD,
            CMAKE_FLAG,
            str(PREFIX),
        ),
    )
    if "sbatch" in wrapper or "benchmarks/results/results.parquet" in wrapper:
        raise AssertionError("wrapper must not submit SLURM or write results")
    _run(["bash", "-n", str(WRAPPER)])
    blocked = _run(["bash", str(WRAPPER)], check=False)
    if blocked.returncode != 2 or "BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED" not in blocked.stdout:
        raise AssertionError(f"wrapper approval guard drifted: rc={blocked.returncode}\n{blocked.stdout}")
    guarded = _run(
        ["bash", str(WRAPPER)],
        env={"BD001_OPTIMIZED_PREFIX_BUILD_APPROVED": "YES", "SLURM_JOB_ID": ""},
        check=False,
    )
    if guarded.returncode != 2 or "BD001_OPTIMIZED_PREFIX_COMPUTE_GUARD" not in guarded.stdout:
        raise AssertionError(f"wrapper compute guard drifted: rc={guarded.returncode}\n{guarded.stdout}")
    print("BD001_OPTIMIZED_PREFIX_BUILD_NEXT_WRAPPER_GUARD_OK")


def _require_blockers() -> None:
    if CONFIG.exists() or (PREFIX / "Geant4Config.cmake").exists():
        raise AssertionError(f"optimized prefix config exists; replace blocker with digest evidence: {CONFIG}")
    if RESULTS.exists():
        raise AssertionError(f"canonical results file exists unexpectedly: {RESULTS}")
    report = _read(REPORT)
    _require(
        "report",
        report,
        (
            "BD-geant4-001 optimized-prefix build-next blocker",
            "OPEN: optimized_prefix_build_compute_resource_missing",
            "OPEN: optimized_prefix_config_missing",
            "BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED_OK",
            "BD001_RESULT_READINESS_OPTIMIZED_PREFIX_BLOCKED_OK",
            "BD001_RESULT_READINESS_RESULTS_ROW_BLOCKED_OK",
            "BD001_OPTIMIZED_PREFIX_BUILD_NEXT_BLOCKED_OK",
            "BD001_OPTIMIZED_PREFIX_BUILD_APPROVED=YES",
            "BD001_OPTIMIZED_PREFIX_COMPUTE_GUARD",
            str(CONFIG),
            SOURCE_COMMIT,
            HANDOFF_HEAD,
            CMAKE_FLAG,
            "No SLURM submit/cancel/requeue/resubmit/dry-run/allocation",
            "No benchmark events",
            "No benchmark events, result rows, reference mutations, NNBAR",
            "parity claims, or speedup claims",
        ),
    )
    if len(report.splitlines()) > 100:
        raise AssertionError("build-next report exceeds 100 lines")
    print(f"BD001_OPTIMIZED_PREFIX_BUILD_NEXT_PREFIX_BLOCKED_OK path={CONFIG}")


def main() -> int:
    _require_source_refs()
    _require_wrapper_guards()
    _require_blockers()
    print("BD001_OPTIMIZED_PREFIX_BUILD_NEXT_BLOCKED_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
