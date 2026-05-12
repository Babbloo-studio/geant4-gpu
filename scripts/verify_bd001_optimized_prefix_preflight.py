#!/usr/bin/env python3
"""Verify BD001 optimized-prefix evidence remains concrete and fail-closed."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
PREFIX = Path("/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4")
WRAPPER = ROOT / "scripts/prepare_bd001_optimized_prefix.sh"
REPORT = ROOT / "docs/reports/bd_geant4_001_result_readiness_20260513.md"
SOURCE_COMMIT = "4ac150b"
HANDOFF_HEAD = "782d84c"
CMAKE_FLAG = "-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON"
TARGET = "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
BUILD_SETTINGS = "cmake/Modules/G4BuildSettings.cmake"


def _run(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if check and proc.returncode != 0:
        raise AssertionError(proc.stdout.strip())
    return proc


def _require_text(path: Path, markers: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} missing markers: {missing}")
    return text


def _geant4_config_paths() -> list[Path]:
    candidates = (
        PREFIX / "lib/cmake/Geant4/Geant4Config.cmake",
        PREFIX / "Geant4Config.cmake",
    )
    return [path for path in candidates if path.is_file()]


def main() -> int:
    if not (SOURCE_REPO / ".git").is_dir():
        raise AssertionError(f"missing Geant4 source worktree: {SOURCE_REPO}")
    handoff = _run(["git", "-C", str(SOURCE_REPO), "rev-parse", "--short=7", f"{HANDOFF_HEAD}^{{commit}}"]).stdout.strip()
    source = _run(["git", "-C", str(SOURCE_REPO), "rev-parse", "--short=7", f"{SOURCE_COMMIT}^{{commit}}"]).stdout.strip()
    _run(["git", "-C", str(SOURCE_REPO), "merge-base", "--is-ancestor", SOURCE_COMMIT, HANDOFF_HEAD])
    print(f"BD001_OPTIMIZED_PREFIX_SOURCE_REFS_OK source={source} handoff={handoff}")

    build_settings = _run(["git", "-C", str(SOURCE_REPO), "show", f"{HANDOFF_HEAD}:{BUILD_SETTINGS}"]).stdout
    target = _run(["git", "-C", str(SOURCE_REPO), "show", f"{HANDOFF_HEAD}:{TARGET}"]).stdout
    for marker in ("option(G4EM_MOLLER_BHABHA_INVERSE_SAMPLER", "add_compile_definitions", "geant4_add_feature"):
        if marker not in build_settings:
            raise AssertionError(f"BD001 handoff build settings missing {marker!r}")
    if "G4EM_MOLLER_BHABHA_INVERSE_SAMPLER" not in target or "flatArray(2, rndm)" not in target:
        raise AssertionError("BD001 handoff target lacks sampler flag marker or fallback sampler")
    print("BD001_OPTIMIZED_PREFIX_SOURCE_FLAG_OK")

    configs = _geant4_config_paths()
    if configs:
        raise AssertionError(
            "optimized prefix now has Geant4Config.cmake; replace blocker with digest-pinned evidence: "
            + ",".join(str(path) for path in configs)
        )
    print(f"BD001_OPTIMIZED_PREFIX_CONFIG_MISSING_OK path={PREFIX}/lib/cmake/Geant4/Geant4Config.cmake")

    wrapper = _require_text(
        WRAPPER,
        (
            "BD001_OPTIMIZED_PREFIX_BUILD_APPROVED",
            str(PREFIX),
            SOURCE_COMMIT,
            HANDOFF_HEAD,
            CMAKE_FLAG,
            "BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED",
        ),
    )
    if "sbatch" in wrapper or "benchmarks/results/results.parquet" in wrapper:
        raise AssertionError("optimized-prefix wrapper must not submit SLURM or write harness results")
    _run(["bash", "-n", str(WRAPPER)])
    blocked = _run(["bash", str(WRAPPER)], check=False)
    if blocked.returncode != 2 or "BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED" not in blocked.stdout:
        raise AssertionError(f"wrapper did not fail closed as expected: rc={blocked.returncode} out={blocked.stdout}")
    print("BD001_OPTIMIZED_PREFIX_WRAPPER_GUARD_OK")

    _require_text(
        REPORT,
        (
            "OPEN: optimized_prefix_config_missing",
            str(PREFIX),
            SOURCE_COMMIT,
            HANDOFF_HEAD,
            CMAKE_FLAG,
            "scripts/prepare_bd001_optimized_prefix.sh",
            "No SLURM",
        ),
    )
    print("BD001_OPTIMIZED_PREFIX_REPORT_OK")
    print("BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
