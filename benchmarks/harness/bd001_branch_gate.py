#!/usr/bin/env python3
"""Fail-closed implementation-branch gate for BD-geant4-001.

The gate is intentionally read-only: it validates that a future registry row can
be tied to a real Geant4 source ref and a distinct optimized install prefix
before any SLURM smoke or result-row work is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

if __package__ in (None, ""):
    from optimization_registry import OptimizationRegistryError, require_entry
else:
    from .optimization_registry import OptimizationRegistryError, require_entry

BD001_TARGET = "source/processes/electromagnetic/standard/src/G4MollerBhabhaModel.cc"
BD001_FALLBACK_TOKEN = "flatArray(2, rndm)"
DEFINE_RE = re.compile(r"(?:^|\s)-D([A-Za-z_][A-Za-z0-9_]*)(?:=(?:ON|1|TRUE|YES))?(?=\s|$)")


class BD001BranchGateError(RuntimeError):
    """Raised when BD-geant4-001 implementation evidence is incomplete."""


@dataclass(frozen=True)
class BD001BranchGateResult:
    opt_id: str
    branch: str
    commit: str
    source_repo: Path
    optimized_geant4_prefix: Path
    target_path: str = BD001_TARGET
    source_marker: str = ""


def bd001_branch_gate(
    registry: str | Path,
    *,
    source_repo: str | Path,
    opt_id: str = "BD-geant4-001",
    require_prefix_config: bool = False,
) -> BD001BranchGateResult:
    """Validate future BD-001 registry/source-prefix evidence without mutation."""

    if opt_id != "BD-geant4-001":
        raise BD001BranchGateError("bd001_branch_gate only accepts opt_id='BD-geant4-001'")
    try:
        entry = require_entry(opt_id, registry)
    except OptimizationRegistryError as exc:
        raise BD001BranchGateError(str(exc)) from exc
    if not entry.optimized_geant4_prefix:
        raise BD001BranchGateError("BD-geant4-001 registry row requires optimized_geant4_prefix")
    prefix = Path(entry.optimized_geant4_prefix)
    if require_prefix_config and not _geant4_config_exists(prefix):
        raise BD001BranchGateError(f"missing Geant4Config.cmake under optimized prefix: {prefix}")
    repo = Path(source_repo)
    if not (repo / ".git").exists():
        raise BD001BranchGateError(f"source_repo is not a git worktree: {repo}")
    commit = _git(repo, "rev-parse", f"{entry.branch}^{{commit}}")
    if not _git_ok(repo, "cat-file", "-e", f"{commit}:{BD001_TARGET}"):
        raise BD001BranchGateError(f"{entry.branch} does not contain {BD001_TARGET}")
    source_text = _git(repo, "show", f"{commit}:{BD001_TARGET}")
    marker = _required_source_marker(entry.cmake_flags)
    if marker not in source_text:
        raise BD001BranchGateError(
            f"{entry.branch}:{BD001_TARGET} does not contain CMake flag marker {marker!r}"
        )
    if BD001_FALLBACK_TOKEN not in source_text:
        raise BD001BranchGateError(
            f"{entry.branch}:{BD001_TARGET} does not preserve fallback rejection sampler token {BD001_FALLBACK_TOKEN!r}"
        )
    return BD001BranchGateResult(
        opt_id=opt_id,
        branch=entry.branch,
        commit=commit,
        source_repo=repo,
        optimized_geant4_prefix=prefix,
        source_marker=marker,
    )


def _required_source_marker(cmake_flags: str) -> str:
    markers = [match.group(1) for match in DEFINE_RE.finditer(cmake_flags)]
    bd001_markers = [marker for marker in markers if "BD001" in marker or "MOLLER" in marker or "BHABHA" in marker]
    if not bd001_markers:
        raise BD001BranchGateError(
            "BD-geant4-001 registry cmake_flags must define a BD001/Moller/Bhabha source marker"
        )
    return bd001_markers[0]


def _geant4_config_exists(prefix: Path) -> bool:
    return (prefix / "lib/cmake/Geant4/Geant4Config.cmake").is_file() or (prefix / "Geant4Config.cmake").is_file()


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BD001BranchGateError(proc.stdout.strip())
    return proc.stdout.strip()


def _git_ok(repo: Path, *args: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


__all__ = ["BD001BranchGateError", "BD001BranchGateResult", "bd001_branch_gate"]
