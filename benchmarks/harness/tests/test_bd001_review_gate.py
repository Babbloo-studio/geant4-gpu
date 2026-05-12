#!/usr/bin/env python3
"""Focused tests for the BD-geant4-001 reviewed-registry gate."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_review_gate import BD001ReviewGateError, bd001_review_gate  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE, text=True)
    return proc.stdout.strip()


def _repo(tmp: Path) -> tuple[Path, str]:
    repo = tmp / "geant4-src"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    target = repo / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
    target.parent.mkdir(parents=True)
    target.write_text("// G4GPU_BD001 fixture preserves flatArray(2, rndm) fallback\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    _git(repo, "branch", "lane/bd001")
    return repo, _git(repo, "rev-parse", "HEAD")


def _write_registry(tmp: Path, commit: str, artifact: Path, *, status: str = "approved") -> Path:
    path = tmp / "registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "BD-geant4-001:\n"
        "  branch: lane/bd001\n"
        "  cmake_flags: \"-DG4GPU_BD001=ON\"\n"
        "  description: \"fixture\"\n"
        "  depends_on: []\n"
        "  optimized_geant4_prefix: \"/abs/optimized-geant4\"\n"
        f"  review_status: {status}\n"
        "  reviewed_by: [reviewer-a]\n"
        f"  reviewed_commit: \"{commit}\"\n"
        f"  review_artifact: \"{artifact}\"\n",
        encoding="utf-8",
    )
    return path


def _write_artifact(path: Path, commit: str) -> Path:
    path.write_text(
        f"BD-geant4-001 lane/bd001 {commit} approved reviewer-a\n",
        encoding="utf-8",
    )
    return path


def test_bd001_review_gate_accepts_approved_fixture(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _write_artifact(tmp_path / "review.md", commit)
    result = bd001_review_gate(_write_registry(tmp_path, commit, artifact), source_repo=repo)
    assert result.opt_id == "BD-geant4-001"
    assert result.commit == commit
    assert result.reviewed_by == ("reviewer-a",)
    assert result.review_artifact == artifact


def test_bd001_review_gate_fails_closed_until_approved(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _write_artifact(tmp_path / "review.md", commit)
    for status in ("pending", "blocked"):
        try:
            bd001_review_gate(_write_registry(tmp_path / status, commit, artifact, status=status), source_repo=repo)
        except BD001ReviewGateError as exc:
            assert "review_status" in str(exc)
        else:
            raise AssertionError(f"review gate accepted status={status}")


def test_bd001_review_gate_checks_commit_and_artifact_tokens(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _write_artifact(tmp_path / "review.md", commit)
    wrong_commit = "0" * 40
    try:
        bd001_review_gate(_write_registry(tmp_path / "wrong", wrong_commit, artifact), source_repo=repo)
    except BD001ReviewGateError as exc:
        assert "reviewed_commit must match" in str(exc)
    else:
        raise AssertionError("review gate accepted mismatched reviewed_commit")

    incomplete = tmp_path / "incomplete.md"
    incomplete.write_text(f"BD-geant4-001 lane/bd001 {commit} reviewer-a\n", encoding="utf-8")
    try:
        bd001_review_gate(_write_registry(tmp_path / "incomplete", commit, incomplete), source_repo=repo)
    except BD001ReviewGateError as exc:
        assert "approved" in str(exc)
    else:
        raise AssertionError("review gate accepted incomplete review artifact")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="g4gpu-bd001-review-gate-") as tmp_dir:
        tmp = Path(tmp_dir)
        test_bd001_review_gate_accepts_approved_fixture(tmp / "accept")
        test_bd001_review_gate_fails_closed_until_approved(tmp / "status")
        test_bd001_review_gate_checks_commit_and_artifact_tokens(tmp / "tokens")
    print("benchmark_harness_bd001_review_gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
