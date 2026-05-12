#!/usr/bin/env python3
"""Fail-closed reviewed-registry gate for BD-geant4-001.

This gate is intentionally read-only.  It is the last cheap prerequisite before
allowing a real BD-001 registry row to drive build/smoke work: the row must be
approved against the exact implementation commit proven by the branch gate, and
must point to an existing local review artifact that names the same evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    from bd001_branch_gate import BD001BranchGateError, BD001BranchGateResult, bd001_branch_gate
    from optimization_registry import OptimizationRegistryError, require_entry
else:
    from .bd001_branch_gate import BD001BranchGateError, BD001BranchGateResult, bd001_branch_gate
    from .optimization_registry import OptimizationRegistryError, require_entry


class BD001ReviewGateError(RuntimeError):
    """Raised when BD-geant4-001 registry review evidence is incomplete."""


@dataclass(frozen=True)
class BD001ReviewGateResult:
    opt_id: str
    branch: str
    commit: str
    reviewed_by: tuple[str, ...]
    review_artifact: Path
    branch_gate: BD001BranchGateResult


def bd001_review_gate(
    registry: str | Path,
    *,
    source_repo: str | Path,
    opt_id: str = "BD-geant4-001",
    require_prefix_config: bool = False,
) -> BD001ReviewGateResult:
    """Require reviewed BD-001 registry metadata tied to branch-gate evidence."""

    if opt_id != "BD-geant4-001":
        raise BD001ReviewGateError("bd001_review_gate only accepts opt_id='BD-geant4-001'")
    try:
        branch_result = bd001_branch_gate(
            registry,
            source_repo=source_repo,
            opt_id=opt_id,
            require_prefix_config=require_prefix_config,
        )
        entry = require_entry(opt_id, registry)
    except (BD001BranchGateError, OptimizationRegistryError) as exc:
        raise BD001ReviewGateError(str(exc)) from exc

    if entry.review_status != "approved":
        raise BD001ReviewGateError(f"{opt_id}: review_status must be 'approved' before BD001 registry use")
    if not entry.reviewed_by:
        raise BD001ReviewGateError(f"{opt_id}: reviewed_by must list at least one reviewer")
    if entry.reviewed_commit != branch_result.commit:
        raise BD001ReviewGateError(
            f"{opt_id}: reviewed_commit must match implementation commit {branch_result.commit}"
        )
    if not entry.review_artifact:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact is required for approved registry rows")

    artifact = Path(entry.review_artifact)
    if not artifact.is_file():
        raise BD001ReviewGateError(f"{opt_id}: review_artifact does not exist: {artifact}")
    text = artifact.read_text(encoding="utf-8", errors="replace")
    _require_artifact_token(opt_id, text, opt_id)
    _require_artifact_token(opt_id, text, branch_result.branch)
    _require_artifact_token(opt_id, text, branch_result.commit)
    _require_artifact_token(opt_id, text.lower(), "approved")
    for reviewer in entry.reviewed_by:
        _require_artifact_token(opt_id, text, reviewer)

    return BD001ReviewGateResult(
        opt_id=opt_id,
        branch=branch_result.branch,
        commit=branch_result.commit,
        reviewed_by=entry.reviewed_by,
        review_artifact=artifact,
        branch_gate=branch_result,
    )


def _require_artifact_token(opt_id: str, text: str, token: str) -> None:
    if token not in text:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact does not mention {token!r}")


__all__ = ["BD001ReviewGateError", "BD001ReviewGateResult", "bd001_review_gate"]
