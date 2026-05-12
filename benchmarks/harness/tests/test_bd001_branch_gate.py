#!/usr/bin/env python3
"""Focused tests for the BD-geant4-001 implementation branch gate."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.harness.bd001_branch_gate import BD001BranchGateError, bd001_branch_gate  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL)


def _repo(tmp: Path, *, with_target: bool = True) -> Path:
    repo = tmp / "geant4-src"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    if with_target:
        target = repo / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
        target.parent.mkdir(parents=True)
        target.write_text(
            "#ifdef G4GPU_BD001\n"
            "// fixture optimized sampler hook\n"
            "#endif\n"
            "rndmEngine->flatArray(2, rndm);\n",
            encoding="utf-8",
        )
    else:
        (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    _git(repo, "branch", "lane/bd001")
    return repo


def _registry(path: Path, *, prefix: str | None = "/abs/optimized-geant4") -> Path:
    extra = f'  optimized_geant4_prefix: "{prefix}"\n' if prefix is not None else ""
    text = (
        "BD-geant4-001:\n"
        "  branch: lane/bd001\n"
        "  cmake_flags: \"-DG4GPU_BD001=ON\"\n"
        "  description: \"fixture\"\n"
        "  depends_on: []\n"
        f"{extra}"
    )
    path.write_text(text, encoding="utf-8")
    return path


def test_bd001_branch_gate_accepts_fixture_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result = bd001_branch_gate(_registry(tmp_path / "registry.yaml"), source_repo=repo)
    assert result.opt_id == "BD-geant4-001"
    assert result.branch == "lane/bd001"
    assert len(result.commit) == 40
    assert result.target_path.endswith("G4MollerBhabhaModel.cc")
    assert result.source_marker == "G4GPU_BD001"


def test_bd001_branch_gate_fails_closed_on_missing_prefix_or_target(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        bd001_branch_gate(_registry(tmp_path / "missing-prefix.yaml", prefix=None), source_repo=repo)
    except BD001BranchGateError as exc:
        assert "optimized_geant4_prefix" in str(exc)
    else:
        raise AssertionError("gate accepted a BD001 row without optimized_geant4_prefix")

    repo_without_target = _repo(tmp_path / "other", with_target=False)
    try:
        bd001_branch_gate(_registry(tmp_path / "registry.yaml"), source_repo=repo_without_target)
    except BD001BranchGateError as exc:
        assert "G4MollerBhabhaModel.cc" in str(exc)
    else:
        raise AssertionError("gate accepted a branch without the BD001 source target")

    vanilla_like = _repo(tmp_path / "vanilla-like")
    target = vanilla_like / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
    target.write_text("rndmEngine->flatArray(2, rndm);\n", encoding="utf-8")
    _git(vanilla_like, "add", ".")
    _git(vanilla_like, "commit", "-m", "remove source marker")
    _git(vanilla_like, "branch", "-f", "lane/bd001")
    try:
        bd001_branch_gate(_registry(tmp_path / "marker.yaml"), source_repo=vanilla_like)
    except BD001BranchGateError as exc:
        assert "CMake flag marker" in str(exc)
    else:
        raise AssertionError("gate accepted a BD001 branch without source marker")

    no_fallback = _repo(tmp_path / "no-fallback")
    target = no_fallback / "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
    target.write_text("#ifdef G4GPU_BD001\n#endif\n", encoding="utf-8")
    _git(no_fallback, "add", ".")
    _git(no_fallback, "commit", "-m", "remove fallback")
    _git(no_fallback, "branch", "-f", "lane/bd001")
    try:
        bd001_branch_gate(_registry(tmp_path / "fallback.yaml"), source_repo=no_fallback)
    except BD001BranchGateError as exc:
        assert "fallback rejection sampler" in str(exc)
    else:
        raise AssertionError("gate accepted a BD001 branch without fallback sampler")


def test_bd001_branch_gate_checks_prefix_config_when_requested(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    prefix = tmp_path / "opt-prefix"
    try:
        bd001_branch_gate(_registry(tmp_path / "registry.yaml", prefix=str(prefix)), source_repo=repo, require_prefix_config=True)
    except BD001BranchGateError as exc:
        assert "Geant4Config.cmake" in str(exc)
    else:
        raise AssertionError("gate accepted missing optimized Geant4Config.cmake")
    (prefix / "lib/cmake/Geant4").mkdir(parents=True)
    (prefix / "lib/cmake/Geant4/Geant4Config.cmake").write_text("# fixture\n", encoding="utf-8")
    assert bd001_branch_gate(
        _registry(tmp_path / "registry-ok.yaml", prefix=str(prefix)),
        source_repo=repo,
        require_prefix_config=True,
    ).optimized_geant4_prefix == prefix


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        test_bd001_branch_gate_accepts_fixture_branch(tmp / "accept")
        test_bd001_branch_gate_fails_closed_on_missing_prefix_or_target(tmp / "fail")
        test_bd001_branch_gate_checks_prefix_config_when_requested(tmp / "prefix")
    print("benchmark_harness_bd001_branch_gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
