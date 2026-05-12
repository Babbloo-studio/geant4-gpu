#!/usr/bin/env python3
"""BD001 registry/default tests for benchmark-harness run.py."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.run import main as run_main  # noqa: E402

def _write_registry(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "optimizations_registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout.strip()


def _bd001_source_repo(tmp_path: Path, branch: str = "lane/bd-geant4-001-moller-bhabha-inverse-sampler") -> tuple[Path, str]:
    repo = tmp_path / "bd001-source"
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
    return repo, _git(repo, "rev-parse", "HEAD")


def _bd001_review_artifact(tmp_path: Path, *, branch: str, commit: str, reviewer: str = "reviewer-a") -> Path:
    artifact = tmp_path / "bd001-review.md"
    artifact.write_text(
        f"BD-geant4-001 {branch} approved {reviewer}\n"
        f"reviewed_commit {commit} supersedes source 4ac150b handoff 782d84c\n"
        "branch proof source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc "
        "G4GPU_BD001_MOLLER_BHABHA\n",
        encoding="utf-8",
    )
    return artifact
def test_dry_run_propagates_claim_metadata_to_sbatch(tmp_path: Path) -> None:
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--opt-branch",
                "lane/bd-geant4-001-moller-bhabha-inverse-sampler",
                "--opt-cmake-flags=-DG4GPU_BD001=ON",
                "--workload",
                "W1",
                "--physics-list",
                "PL2",
                "--hw",
                "H3",
                "--n-seeds",
                "1",
                "--repo-root",
                str(tmp_path / "repo"),
                "--geant4-prefix",
                str(tmp_path / "vanilla-geant4"),
                "--optimized-geant4-prefix",
                str(tmp_path / "optimized-geant4"),
                "--claim-level",
                "L2",
                "--geant4-version",
                "v11.2.2-bd001-preflight",
                "--notes",
                "bd001 metadata preflight",
            ]
        )
    text = output.getvalue()
    assert rc == 0
    assert "CLAIM_LEVEL=L2" in text
    assert "GEANT4_VERSION=v11.2.2-bd001-preflight" in text
    assert "NOTES='bd001 metadata preflight'" in text
    assert f"VANILLA_GEANT4_PREFIX={tmp_path / 'vanilla-geant4'}" in text
    assert f"OPTIMIZED_GEANT4_PREFIX={tmp_path / 'optimized-geant4'}" in text
    assert 'run_one optimized "${OPTIMIZED_BIN}" "${seed}" "${OPTIMIZED_GEANT4_PREFIX}"' in text
    assert '--claim-level "${CLAIM_LEVEL}"' in text
    assert '--geant4-version "${GEANT4_VERSION}"' in text
    assert '--notes "${NOTES}"' in text


def test_invalid_claim_metadata_fails_closed(tmp_path: Path) -> None:
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--opt-branch",
                "lane/bd001",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
                "--optimized-geant4-prefix",
                str(tmp_path / "optimized-geant4"),
                "--claim-level",
                "L9",
            ]
        )
    assert rc == 2
    assert "--claim-level must be one of" in err.getvalue()

    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--opt-branch",
                "lane/bd001",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
                "--optimized-geant4-prefix",
                str(tmp_path / "optimized-geant4"),
                "--claim-level",
                "L3",
                "--notes",
                "not paper ready",
            ]
        )
    assert rc == 2
    assert "--notes must be empty for L3 rows" in err.getvalue()


def test_require_registry_prefills_bd001_metadata(tmp_path: Path) -> None:
    branch = "lane/bd-geant4-001-moller-bhabha-inverse-sampler"
    source_repo, commit = _bd001_source_repo(tmp_path, branch)
    review_artifact = _bd001_review_artifact(tmp_path, branch=branch, commit=commit)
    review_digest = hashlib.sha256(review_artifact.read_bytes()).hexdigest()
    registry = _write_registry(
        tmp_path,
        f"""
BD-geant4-001:
  branch: {branch}
  cmake_flags: "-DG4GPU_BD001_MOLLER_BHABHA=ON"
  description: "Moller/Bhabha inverse-sampler candidate"
  depends_on: []
  claim_level: L2
  notes: "registry preflight only"
  optimized_geant4_prefix: "/local/slurmtmp/bd001-optimized-geant4-prefix"
  review_status: approved
  reviewed_by: [reviewer-a]
  reviewed_commit: "{commit}"
  review_artifact: "{review_artifact}"
  review_artifact_sha256: "{review_digest}"
""",
    )
    output = io.StringIO()
    with redirect_stdout(output):
        rc = run_main(
            [
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
                str(tmp_path / "repo"),
                "--geant4-prefix",
                "/tmp/g4gpu-bd001-vanilla-prefix",
            ]
        )
    text = output.getvalue()
    assert rc == 0
    assert "OPT_BRANCH=lane/bd-geant4-001-moller-bhabha-inverse-sampler" in text
    assert "OPT_CMAKE_FLAGS=-DG4GPU_BD001_MOLLER_BHABHA=ON" in text
    assert "CLAIM_LEVEL=L2" in text
    assert "NOTES='registry preflight only'" in text
    assert "OPTIMIZED_GEANT4_PREFIX=/local/slurmtmp/bd001-optimized-geant4-prefix" in text


def test_require_registry_bd001_blocked_status_fails_closed(tmp_path: Path) -> None:
    branch = "lane/bd-geant4-001-moller-bhabha-inverse-sampler"
    source_repo, commit = _bd001_source_repo(tmp_path, branch)
    review_artifact = _bd001_review_artifact(tmp_path, branch=branch, commit=commit)
    registry = _write_registry(
        tmp_path,
        f"""
BD-geant4-001:
  branch: {branch}
  cmake_flags: "-DG4GPU_BD001_MOLLER_BHABHA=ON"
  description: "blocked Moller/Bhabha inverse-sampler candidate"
  depends_on: []
  claim_level: L2
  notes: "blocked registry preflight only"
  optimized_geant4_prefix: "/local/slurmtmp/bd001-optimized-geant4-prefix"
  review_status: blocked
  reviewed_by: [reviewer-a]
  reviewed_commit: "{commit}"
  review_artifact: "{review_artifact}"
""",
    )
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
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
                str(tmp_path / "repo"),
            ]
        )
    assert rc == 2
    assert "reviewed-registry gate failed" in err.getvalue()
    assert "review_status must be 'approved'" in err.getvalue()


def test_bd001_requires_distinct_optimized_geant4_prefix(tmp_path: Path) -> None:
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--opt-branch",
                "lane/bd001",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
            ]
        )
    assert rc == 2
    assert "requires --optimized-geant4-prefix" in err.getvalue()

    same = tmp_path / "same-prefix"
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--opt-branch",
                "lane/bd001",
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
                "--geant4-prefix",
                str(same),
                "--optimized-geant4-prefix",
                str(same),
            ]
        )
    assert rc == 2
    assert "must differ" in err.getvalue()


def test_require_registry_missing_bd001_entry_fails_closed(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path,
        """
BD-geant4-032:
  branch: lane/bd-geant4-032
  cmake_flags: ""
  description: "different optimization"
  depends_on: []
""",
    )
    err = io.StringIO()
    with redirect_stderr(err):
        rc = run_main(
            [
                "--opt-id",
                "BD-geant4-001",
                "--require-registry",
                "--registry",
                str(registry),
                "--workload",
                "W1",
                "--physics-list",
                "PL1",
                "--hw",
                "H3",
                "--repo-root",
                str(tmp_path / "repo"),
            ]
        )
    assert rc == 2
    assert "lacks required entry 'BD-geant4-001'" in err.getvalue()


def run_bd001_registry_selftest(tmp_path: Path) -> None:
    """Run moved BD001 registry tests for the direct CTest entrypoint."""

    test_dry_run_propagates_claim_metadata_to_sbatch(tmp_path)
    test_invalid_claim_metadata_fails_closed(tmp_path)
    test_require_registry_prefills_bd001_metadata(tmp_path / "registry-prefill")
    test_require_registry_bd001_blocked_status_fails_closed(tmp_path / "registry-blocked")
    test_require_registry_missing_bd001_entry_fails_closed(tmp_path / "registry-missing")
    test_bd001_requires_distinct_optimized_geant4_prefix(tmp_path)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_bd001_registry_selftest(Path(tmp_dir))
    print("benchmark_harness_run_bd001_registry: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
