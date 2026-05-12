#!/usr/bin/env python3
"""Verify the BD-geant4-001 reviewed-registry handoff is fail-closed.

This verifier is static/read-only. It does not configure, build, submit SLURM,
run events, regenerate references, append result rows, or make parity/speedup
claims.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_branch_gate import bd001_branch_gate  # noqa: E402
from benchmarks.harness.bd001_review_gate import BD001ReviewGateError, bd001_review_gate  # noqa: E402
from benchmarks.harness.optimization_registry import DEFAULT_REGISTRY, require_entry  # noqa: E402

SOURCE_REPO = Path("/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
BRANCH = "lane/bd-geant4-001-moller-bhabha-inverse-sampler"
SOURCE_COMMIT = "4ac150bf453fe4dd0e384065c6b8d14cbf0fbc5e"
HANDOFF_HEAD = "782d84cb598f7ca4faa9a67092271dfc2e86d811"
FLAG = "G4EM_MOLLER_BHABHA_INVERSE_SAMPLER"
REPORT = ROOT / "docs/reports/bd_geant4_001_review_registry_handoff_blocker_20260512.md"


def _read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _require_markers(path: Path, markers: tuple[str, ...]) -> None:
    text = _read(path)
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise AssertionError(f"{path} missing markers: {missing}")


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


def _run_expect_rc(cmd: list[str], rc: int) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    if proc.returncode != rc:
        raise AssertionError(f"expected rc={rc}, got {proc.returncode}: {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


def _write_registry(path: Path, *, status: str, reviewed_commit: str, artifact: Path) -> None:
    path.write_text(
        f"""
BD-geant4-001:
  branch: {BRANCH}
  cmake_flags: "-D{FLAG}=ON"
  description: "review handoff fixture"
  depends_on: []
  claim_level: L2
  notes: "review handoff fixture only"
  optimized_geant4_prefix: "/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4"
  review_status: {status}
  reviewed_by: [reviewer-a]
  reviewed_commit: "{reviewed_commit}"
  review_artifact: "{artifact}"
""".lstrip(),
        encoding="utf-8",
    )


def _exercise_real_source_gates() -> None:
    if not (SOURCE_REPO / ".git").is_dir():
        raise AssertionError(f"missing source repo: {SOURCE_REPO}")
    if _git(SOURCE_REPO, "rev-parse", "HEAD") != HANDOFF_HEAD:
        raise AssertionError("source repo HEAD is not the expected handoff head")
    if _git(SOURCE_REPO, "branch", "--show-current") != BRANCH:
        raise AssertionError("source repo is not on the expected BD001 branch")
    _git(SOURCE_REPO, "merge-base", "--is-ancestor", SOURCE_COMMIT, HANDOFF_HEAD)

    branch_result = bd001_branch_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO)
    if branch_result.commit != HANDOFF_HEAD or branch_result.source_marker != FLAG:
        raise AssertionError(f"unexpected default branch-gate result: {branch_result}")
    try:
        bd001_review_gate(DEFAULT_REGISTRY, source_repo=SOURCE_REPO)
    except BD001ReviewGateError as exc:
        if "review_status must be 'approved'" not in str(exc):
            raise AssertionError(f"default blocked registry failed for wrong reason: {exc}") from exc
    else:
        raise AssertionError("default blocked BD001 registry row passed the review gate")


def _exercise_cli_fail_closed() -> None:
    output = _run_expect_rc(
        [
            sys.executable,
            "-m",
            "benchmarks.harness.run",
            "--opt-id",
            "BD-geant4-001",
            "--require-registry",
            "--bd001-source-repo",
            str(SOURCE_REPO),
            "--workload",
            "W1",
            "--physics-list",
            "PL2",
            "--hw",
            "H3",
            "--n-seeds",
            "1",
        ],
        2,
    )
    for marker in ("reviewed-registry gate failed", "review_status must be 'approved'"):
        if marker not in output:
            raise AssertionError(f"blocked default registry CLI output missing {marker!r}:\n{output}")


def _exercise_stale_review_rejection() -> None:
    with tempfile.TemporaryDirectory(prefix="bd001-review-handoff-") as tmp_s:
        tmp = Path(tmp_s)
        artifact = tmp / "review.md"
        artifact.write_text(
            f"BD-geant4-001 {BRANCH} {SOURCE_COMMIT} approved reviewer-a\n",
            encoding="utf-8",
        )
        stale = tmp / "stale-source-commit.yaml"
        _write_registry(stale, status="approved", reviewed_commit=SOURCE_COMMIT, artifact=artifact)
        try:
            bd001_review_gate(stale, source_repo=SOURCE_REPO)
        except BD001ReviewGateError as exc:
            if "reviewed_commit must match implementation commit" not in str(exc):
                raise AssertionError(f"stale source commit rejected for wrong reason: {exc}") from exc
        else:
            raise AssertionError("review gate accepted source commit where handoff head was required")


def main() -> int:
    entry = require_entry("BD-geant4-001", DEFAULT_REGISTRY)
    if entry.review_status != "blocked":
        raise AssertionError("default BD001 registry handoff must remain blocked")
    if entry.branch != BRANCH or entry.cmake_flags != f"-D{FLAG}=ON":
        raise AssertionError(f"unexpected default BD001 registry row: {entry}")
    print("BD001_DEFAULT_BLOCKED_REGISTRY_ROW_OK")
    _exercise_real_source_gates()
    print("BD001_REAL_SOURCE_REVIEW_GATE_BLOCKED_OK")
    _exercise_cli_fail_closed()
    print("BD001_RUN_REQUIRE_REGISTRY_FAIL_CLOSED_OK")
    _exercise_stale_review_rejection()
    print("BD001_STALE_SOURCE_COMMIT_REJECTED_OK")
    _require_markers(
        REPORT,
        (
            "BD-geant4-001 reviewed production-registry handoff blocker",
            SOURCE_COMMIT,
            HANDOFF_HEAD,
            "review_status: blocked",
            "No SLURM",
            "BD001_REVIEW_REGISTRY_HANDOFF_BLOCKED_782D84C_OK",
        ),
    )
    print("BD001_REVIEW_REGISTRY_HANDOFF_REPORT_OK")
    print("BD001_REVIEW_REGISTRY_HANDOFF_BLOCKED_782D84C_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
