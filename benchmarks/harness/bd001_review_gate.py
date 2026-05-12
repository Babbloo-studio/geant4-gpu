#!/usr/bin/env python3
"""Fail-closed reviewed-registry gate for BD-geant4-001.

This gate is intentionally read-only.  It is the last cheap prerequisite before
allowing a real BD-001 registry row to drive build/smoke work: the row must be
approved against the exact implementation commit proven by the branch gate, and
must point to an existing local review artifact that names the same evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

if __package__ in (None, ""):
    from bd001_branch_gate import BD001BranchGateError, BD001BranchGateResult, bd001_branch_gate
    from optimization_registry import OptimizationRegistryError, require_entry
else:
    from .bd001_branch_gate import BD001BranchGateError, BD001BranchGateResult, bd001_branch_gate
    from .optimization_registry import OptimizationRegistryError, require_entry


class BD001ReviewGateError(RuntimeError):
    """Raised when BD-geant4-001 registry review evidence is incomplete."""


BD001_SOURCE_COMMIT = "4ac150b"
BD001_HANDOFF_COMMIT = "782d84c"
PLACEHOLDER_OR_NEGATED_REVIEW_TOKENS = (
    "placeholder",
    "tbd",
    "todo",
    "template_only",
    "template-only",
    "not approved",
    "not-approved",
    "revoked",
    "conditional",
    "blocked",
    "pending",
)


@dataclass(frozen=True)
class BD001ReviewGateResult:
    opt_id: str
    branch: str
    commit: str
    reviewed_by: tuple[str, ...]
    review_artifact: Path
    review_artifact_sha256: str
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
    _reject_placeholder_or_negated(opt_id, "review_status", entry.review_status)
    for reviewer in entry.reviewed_by:
        _reject_placeholder_or_negated(opt_id, "reviewed_by", reviewer)
    if entry.reviewed_commit != branch_result.commit:
        raise BD001ReviewGateError(
            f"{opt_id}: reviewed_commit must match implementation commit {branch_result.commit}"
        )
    if not entry.review_artifact:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact is required for approved registry rows")
    if not entry.review_artifact_sha256:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact_sha256 is required for approved registry rows")

    artifact = Path(entry.review_artifact)
    if not artifact.is_file():
        raise BD001ReviewGateError(f"{opt_id}: review_artifact does not exist: {artifact}")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != entry.review_artifact_sha256:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact_sha256 mismatch for {artifact}")
    text = artifact.read_text(encoding="utf-8", errors="replace")
    _reject_placeholder_or_negated(opt_id, "review_artifact", text)
    _require_artifact_token(opt_id, text, opt_id)
    _require_artifact_token(opt_id, text, branch_result.branch)
    _require_artifact_token(opt_id, text, branch_result.commit)
    _require_artifact_token(opt_id, text, BD001_SOURCE_COMMIT)
    _require_artifact_token(opt_id, text, BD001_HANDOFF_COMMIT)
    _require_artifact_token(opt_id, text, branch_result.target_path)
    _require_artifact_token(opt_id, text, branch_result.source_marker)
    _require_artifact_token(opt_id, text.lower(), "approved")
    for reviewer in entry.reviewed_by:
        _require_artifact_token(opt_id, text, reviewer)

    return BD001ReviewGateResult(
        opt_id=opt_id,
        branch=branch_result.branch,
        commit=branch_result.commit,
        reviewed_by=entry.reviewed_by,
        review_artifact=artifact,
        review_artifact_sha256=digest,
        branch_gate=branch_result,
    )


def _require_artifact_token(opt_id: str, text: str, token: str) -> None:
    if token not in text:
        raise BD001ReviewGateError(f"{opt_id}: review_artifact does not mention {token!r}")


def _reject_placeholder_or_negated(opt_id: str, field: str, text: str) -> None:
    lowered = text.lower().replace(" ", "_")
    for token in PLACEHOLDER_OR_NEGATED_REVIEW_TOKENS:
        normalized = token.lower().replace(" ", "_")
        if normalized in lowered:
            raise BD001ReviewGateError(f"{opt_id}: {field} contains placeholder/negated review token {token!r}")


__all__ = ["BD001ReviewGateError", "BD001ReviewGateResult", "bd001_review_gate"]
