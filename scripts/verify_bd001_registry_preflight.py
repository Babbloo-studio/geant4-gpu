#!/usr/bin/env python3
"""Verify the BD-geant4-001 optimization-registry preflight guard."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "benchmarks/harness/run.py"
REGISTRY = ROOT / "benchmarks/harness/optimization_registry.py"
REGISTRY_TEST = ROOT / "benchmarks/harness/tests/test_optimization_registry.py"
RUN_TEST = ROOT / "benchmarks/harness/tests/test_run.py"
CMAKE = ROOT / "CMakeLists.txt"
REPORT = ROOT / "docs/reports/bd_geant4_001_registry_preflight_20260512.md"
PYTHON = Path(sys.executable)


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _require_markers(path: Path, markers: tuple[str, ...]) -> None:
    text = _read(path)
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{path} missing markers: {missing}")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> str:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git command failed: {' '.join(args)}\n{proc.stdout}")
    return proc.stdout.strip()


def _bd001_review_fixture(tmp: Path) -> tuple[Path, str, Path]:
    branch = "lane/bd-geant4-001-moller-bhabha-inverse-sampler"
    repo = tmp / "bd001-source"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    target = repo / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
    target.parent.mkdir(parents=True)
    target.write_text(
        "#ifdef G4GPU_BD001_MOLLER_BHABHA\n"
        "// fixture optimized BD001 sampler hook\n"
        "#endif\n"
        "rndmEngine->flatArray(2, rndm);\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "bd001 fixture")
    _git(repo, "branch", branch)
    commit = _git(repo, "rev-parse", "HEAD")
    artifact = tmp / "bd001-review.md"
    artifact.write_text(f"BD-geant4-001 {branch} {commit} approved reviewer-a\n", encoding="utf-8")
    return repo, commit, artifact


def _exercise_registry_cli() -> None:
    with tempfile.TemporaryDirectory(prefix="bd001-registry-preflight-") as tmp_s:
        tmp = Path(tmp_s)
        source_repo, commit, artifact = _bd001_review_fixture(tmp)
        registry = tmp / "optimizations_registry.yaml"
        registry.write_text(
            f"""
BD-geant4-001:
  branch: lane/bd-geant4-001-moller-bhabha-inverse-sampler
  cmake_flags: "-DG4GPU_BD001_MOLLER_BHABHA=ON"
  description: "Moller/Bhabha inverse-sampler candidate"
  depends_on: []
  claim_level: L2
  notes: "registry preflight only"
  optimized_geant4_prefix: "/local/slurmtmp/bd001-optimized-geant4-prefix"
  review_status: approved
  reviewed_by: [reviewer-a]
  reviewed_commit: "{commit}"
  review_artifact: "{artifact}"
""".lstrip(),
            encoding="utf-8",
        )
        output = _run(
            [
                str(PYTHON),
                "-m",
                "benchmarks.harness.run",
                "--opt-id",
                "BD-geant4-001",
                "--require-registry",
                "--registry",
                str(registry),
                "--bd001-source-repo",
                str(source_repo),
                "--workload",
                "W1",
                "--physics-list",
                "PL2",
                "--hw",
                "H3",
                "--n-seeds",
                "1",
                "--repo-root",
                str(tmp / "repo"),
            ]
        )
        for marker in (
            "OPT_BRANCH=lane/bd-geant4-001-moller-bhabha-inverse-sampler",
            "OPT_CMAKE_FLAGS=-DG4GPU_BD001_MOLLER_BHABHA=ON",
            "CLAIM_LEVEL=L2",
            "NOTES='registry preflight only'",
        ):
            if marker not in output:
                raise AssertionError(f"registry dry-run output missing {marker!r}")
        missing = tmp / "missing.yaml"
        missing.write_text(
            """
BD-geant4-032:
  branch: lane/bd-geant4-032
  cmake_flags: ""
  description: "different optimization"
  depends_on: []
""".lstrip(),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                str(PYTHON),
                "-m",
                "benchmarks.harness.run",
                "--opt-id",
                "BD-geant4-001",
                "--require-registry",
                "--registry",
                str(missing),
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp / "repo"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if proc.returncode != 2 or "lacks required entry 'BD-geant4-001'" not in proc.stdout:
            raise AssertionError(f"missing registry row did not fail closed:\n{proc.stdout}")


def main() -> int:
    _require_markers(
        REGISTRY,
        (
            "OptimizationRegistryEntry",
            "OptimizationRegistryError",
            "DEFAULT_REGISTRY",
            "require_entry",
            "unknown fields are not allowed",
            "notes must be empty for L3",
        ),
    )
    print("REGISTRY_MODULE_MARKERS_OK")
    _require_markers(
        RUN,
        ("--require-registry", "_apply_registry_defaults", "OptimizationRegistryError", "conflicts with registry"),
    )
    print("RUN_REGISTRY_MARKERS_OK")
    _require_markers(
        REGISTRY_TEST,
        ("test_bd001_registry_row_shape_passes", "missing registry was accepted", "unknown fields"),
    )
    _require_markers(
        RUN_TEST,
        ("test_require_registry_prefills_bd001_metadata", "test_require_registry_missing_bd001_entry_fails_closed"),
    )
    print("TEST_REGISTRY_MARKERS_OK")
    _require_markers(CMAKE, ("g4gpu_benchmark_harness_optimization_registry", "test_optimization_registry.py"))
    print("CMAKE_REGISTRY_MARKERS_OK")
    _exercise_registry_cli()
    print("REGISTRY_DRY_RUN_FAIL_CLOSED_OK")
    _require_markers(
        REPORT,
        (
            "BD-geant4-001 registry preflight",
            "--require-registry",
            "BD001_REGISTRY_PREFLIGHT_OK",
            "No SLURM",
            "result row",
        ),
    )
    print("REPORT_REGISTRY_MARKERS_OK")
    print("BD001_REGISTRY_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
