#!/usr/bin/env python3
"""Focused tests for the BD-geant4-001 guarded-smoke contract."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_smoke_contract import (  # noqa: E402
    BD001SmokeContractError,
    REQUIRED_NO_PROMOTION_CHECKS,
    bd001_guarded_smoke_contract,
)


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


def _registry(tmp: Path, commit: str, artifact: Path) -> Path:
    path = tmp / "registry.yaml"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    path.write_text(
        "BD-geant4-001:\n"
        "  branch: lane/bd001\n"
        "  cmake_flags: \"-DG4GPU_BD001=ON\"\n"
        "  description: \"fixture\"\n"
        "  depends_on: []\n"
        "  optimized_geant4_prefix: \"/abs/optimized-geant4\"\n"
        "  review_status: approved\n"
        "  reviewed_by: [reviewer-a]\n"
        f"  reviewed_commit: \"{commit}\"\n"
        f"  review_artifact: \"{artifact}\"\n"
        f"  review_artifact_sha256: \"{digest}\"\n",
        encoding="utf-8",
    )
    return path


def _artifact(path: Path, commit: str) -> Path:
    path.write_text(
        "BD-geant4-001 lane/bd001 approved reviewer-a\n"
        f"reviewed_commit {commit} supersedes source 4ac150b handoff 782d84c\n"
        "branch proof source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc G4GPU_BD001\n",
        encoding="utf-8",
    )
    return path


def _reference_dataset(tmp: Path) -> Path:
    root = tmp / "reference"
    rels = ["W1/PL1/seed_1001.parquet", "W2/PL1/seed_1001.parquet"]
    for rel in rels:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    root.joinpath("MANIFEST.sha256").write_text("".join(f"{'a' * 64}  {rel}\n" for rel in rels), encoding="utf-8")
    return root


def _contract(tmp: Path, commit: str, reference: Path, *, result_tag: str = "NEUTRAL") -> Path:
    path = tmp / "contract.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    checks = "\n".join(f"    - {item}" for item in sorted(REQUIRED_NO_PROMOTION_CHECKS))
    path.write_text(
        "opt_id: BD-geant4-001\n"
        f"source_ref: lane/bd001@{commit}\n"
        f"reference_dataset: \"{reference}\"\n"
        f"result_tag: {result_tag}\n"
        "claim_level: L2\n"
        "workloads: [W1, W2]\n"
        "physics_lists: [PL1]\n"
        "no_promotion_checks:\n"
        f"{checks}\n",
        encoding="utf-8",
    )
    return path


def test_bd001_smoke_contract_accepts_guarded_fixture(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _artifact(tmp_path / "review.md", commit)
    reference = _reference_dataset(tmp_path)
    result = bd001_guarded_smoke_contract(
        _contract(tmp_path, commit, reference),
        registry=_registry(tmp_path, commit, artifact),
        source_repo=repo,
    )
    assert result.source_ref == f"lane/bd001@{commit}"
    assert result.reference_dataset == reference
    assert result.result_tag == "NEUTRAL"
    assert result.claim_level == "L2"
    assert set(result.no_promotion_checks) == REQUIRED_NO_PROMOTION_CHECKS
    assert len(result.manifest_entries) == 2


def test_bd001_smoke_contract_checks_reviewed_source_ref(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _artifact(tmp_path / "review.md", commit)
    reference = _reference_dataset(tmp_path)
    path = _contract(tmp_path, commit, reference)
    path.write_text(path.read_text(encoding="utf-8").replace(commit, "0" * 40, 1), encoding="utf-8")
    try:
        bd001_guarded_smoke_contract(path, registry=_registry(tmp_path, commit, artifact), source_repo=repo)
    except BD001SmokeContractError as exc:
        assert "source_ref" in str(exc)
    else:
        raise AssertionError("guarded-smoke contract accepted mismatched source_ref")


def test_bd001_smoke_contract_requires_reference_manifest_coverage(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _artifact(tmp_path / "review.md", commit)
    reference = _reference_dataset(tmp_path)
    (reference / "MANIFEST.sha256").write_text(f"{'b' * 64}  W1/PL1/seed_1001.parquet\n", encoding="utf-8")
    try:
        bd001_guarded_smoke_contract(
            _contract(tmp_path, commit, reference),
            registry=_registry(tmp_path, commit, artifact),
            source_repo=repo,
        )
    except BD001SmokeContractError as exc:
        assert "W2" in str(exc)
    else:
        raise AssertionError("guarded-smoke contract accepted incomplete reference coverage")


def test_bd001_smoke_contract_blocks_promotion_contracts(tmp_path: Path) -> None:
    repo, commit = _repo(tmp_path)
    artifact = _artifact(tmp_path / "review.md", commit)
    reference = _reference_dataset(tmp_path)
    try:
        bd001_guarded_smoke_contract(
            _contract(tmp_path, commit, reference, result_tag="SPEEDUP"),
            registry=_registry(tmp_path, commit, artifact),
            source_repo=repo,
        )
    except BD001SmokeContractError as exc:
        assert "SPEEDUP" in str(exc)
    else:
        raise AssertionError("guarded-smoke contract accepted SPEEDUP result_tag")

    path = _contract(tmp_path / "checks", commit, reference)
    path.write_text(path.read_text(encoding="utf-8").replace("    - manual_promotion_required\n", ""), encoding="utf-8")
    try:
        bd001_guarded_smoke_contract(path, registry=_registry(tmp_path, commit, artifact), source_repo=repo)
    except BD001SmokeContractError as exc:
        assert "no_promotion_checks" in str(exc)
    else:
        raise AssertionError("guarded-smoke contract accepted missing no-promotion checks")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="g4gpu-bd001-smoke-contract-") as tmp_dir:
        tmp = Path(tmp_dir)
        test_bd001_smoke_contract_accepts_guarded_fixture(tmp / "accept")
        test_bd001_smoke_contract_checks_reviewed_source_ref(tmp / "source")
        test_bd001_smoke_contract_requires_reference_manifest_coverage(tmp / "reference")
        test_bd001_smoke_contract_blocks_promotion_contracts(tmp / "promotion")
    print("benchmark_harness_bd001_smoke_contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
