#!/usr/bin/env python3
"""Fail-closed optimization-registry validation for benchmark-harness rows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

if __package__ in (None, ""):
    from builder import REPO_ROOT
    from schema import CLAIM_LEVELS
else:
    from .builder import REPO_ROOT
    from .schema import CLAIM_LEVELS


DEFAULT_REGISTRY = REPO_ROOT / "benchmarks/optimizations_registry.yaml"
REQUIRED_FIELDS = ("branch", "cmake_flags", "description", "depends_on")
OPTIONAL_FIELDS = (
    "claim_level",
    "notes",
    "optimized_geant4_prefix",
    "review_status",
    "reviewed_by",
    "reviewed_commit",
    "review_artifact",
    "review_artifact_sha256",
)
ALLOWED_FIELDS = frozenset((*REQUIRED_FIELDS, *OPTIONAL_FIELDS))


class OptimizationRegistryError(RuntimeError):
    """Raised when registry metadata is absent or unsafe to trust."""


@dataclass(frozen=True)
class OptimizationRegistryEntry:
    """Validated metadata for one optimization candidate."""

    opt_id: str
    branch: str
    cmake_flags: str
    description: str
    depends_on: tuple[str, ...]
    claim_level: str | None = None
    notes: str = ""
    optimized_geant4_prefix: str | None = None
    review_status: str | None = None
    reviewed_by: tuple[str, ...] = ()
    reviewed_commit: str | None = None
    review_artifact: str | None = None
    review_artifact_sha256: str | None = None


def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict[str, OptimizationRegistryEntry]:
    """Load and validate every entry in ``path``."""

    registry_path = Path(path)
    if not registry_path.is_file():
        raise OptimizationRegistryError(f"optimization registry missing: {registry_path}")
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OptimizationRegistryError(f"cannot parse optimization registry: {exc}") from exc
    if not isinstance(raw, dict) or not raw:
        raise OptimizationRegistryError("optimization registry must be a non-empty mapping")
    return {str(opt_id): validate_entry(str(opt_id), value) for opt_id, value in raw.items()}


def require_entry(
    opt_id: str,
    path: str | Path = DEFAULT_REGISTRY,
) -> OptimizationRegistryEntry:
    """Return one registry entry or fail closed with an actionable message."""

    entries = load_registry(path)
    try:
        return entries[opt_id]
    except KeyError as exc:
        raise OptimizationRegistryError(f"optimization registry lacks required entry {opt_id!r}") from exc


def validate_entry(opt_id: str, value: Any) -> OptimizationRegistryEntry:
    """Validate one raw YAML entry and return typed metadata."""

    if not opt_id.strip():
        raise OptimizationRegistryError("optimization id must be non-empty")
    if not isinstance(value, dict):
        raise OptimizationRegistryError(f"{opt_id}: entry must be a mapping")
    unknown = sorted(set(value) - ALLOWED_FIELDS)
    if unknown:
        raise OptimizationRegistryError(f"{opt_id}: unknown fields are not allowed: {unknown}")
    missing = [field for field in REQUIRED_FIELDS if field not in value]
    if missing:
        raise OptimizationRegistryError(f"{opt_id}: missing required fields: {missing}")
    branch = _non_empty_string(opt_id, value["branch"], "branch")
    cmake_flags = _string(opt_id, value["cmake_flags"], "cmake_flags")
    description = _non_empty_string(opt_id, value["description"], "description")
    depends_on = _string_list(opt_id, value["depends_on"], "depends_on")
    claim_level = value.get("claim_level")
    if claim_level is not None:
        claim_level = _non_empty_string(opt_id, claim_level, "claim_level")
        if claim_level not in CLAIM_LEVELS:
            raise OptimizationRegistryError(f"{opt_id}: claim_level must be one of {sorted(CLAIM_LEVELS)}")
    notes = _string(opt_id, value.get("notes", ""), "notes")
    optimized_geant4_prefix = value.get("optimized_geant4_prefix")
    if optimized_geant4_prefix is not None:
        optimized_geant4_prefix = _non_empty_string(opt_id, optimized_geant4_prefix, "optimized_geant4_prefix")
        if not Path(optimized_geant4_prefix).is_absolute():
            raise OptimizationRegistryError(f"{opt_id}: optimized_geant4_prefix must be an absolute path")
    review_status = value.get("review_status")
    if review_status is not None:
        review_status = _non_empty_string(opt_id, review_status, "review_status")
        if review_status not in {"approved", "blocked", "pending"}:
            raise OptimizationRegistryError(f"{opt_id}: review_status must be approved, blocked, or pending")
    reviewed_by = ()
    if "reviewed_by" in value:
        reviewed_by = _string_list(opt_id, value["reviewed_by"], "reviewed_by")
        if not reviewed_by:
            raise OptimizationRegistryError(f"{opt_id}: reviewed_by must contain at least one reviewer")
    reviewed_commit = value.get("reviewed_commit")
    if reviewed_commit is not None:
        reviewed_commit = _non_empty_string(opt_id, reviewed_commit, "reviewed_commit")
        if not re.fullmatch(r"[0-9a-f]{40}", reviewed_commit):
            raise OptimizationRegistryError(f"{opt_id}: reviewed_commit must be a 40-character lowercase git sha")
    review_artifact = value.get("review_artifact")
    if review_artifact is not None:
        review_artifact = _non_empty_string(opt_id, review_artifact, "review_artifact")
        if not Path(review_artifact).is_absolute():
            raise OptimizationRegistryError(f"{opt_id}: review_artifact must be an absolute path")
    review_artifact_sha256 = value.get("review_artifact_sha256")
    if review_artifact_sha256 is not None:
        review_artifact_sha256 = _non_empty_string(opt_id, review_artifact_sha256, "review_artifact_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", review_artifact_sha256):
            raise OptimizationRegistryError(f"{opt_id}: review_artifact_sha256 must be a 64-character sha256")
    if claim_level == "L3" and notes:
        raise OptimizationRegistryError(f"{opt_id}: notes must be empty for L3 registry rows")
    return OptimizationRegistryEntry(
        opt_id=opt_id,
        branch=branch,
        cmake_flags=cmake_flags,
        description=description,
        depends_on=depends_on,
        claim_level=claim_level,
        notes=notes,
        optimized_geant4_prefix=optimized_geant4_prefix,
        review_status=review_status,
        reviewed_by=reviewed_by,
        reviewed_commit=reviewed_commit,
        review_artifact=review_artifact,
        review_artifact_sha256=review_artifact_sha256,
    )


def _non_empty_string(opt_id: str, value: Any, field: str) -> str:
    text = _string(opt_id, value, field)
    if not text.strip():
        raise OptimizationRegistryError(f"{opt_id}: {field} must be non-empty")
    return text


def _string(opt_id: str, value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise OptimizationRegistryError(f"{opt_id}: {field} must be a string")
    return value


def _string_list(opt_id: str, value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise OptimizationRegistryError(f"{opt_id}: {field} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise OptimizationRegistryError(f"{opt_id}: {field} entries must be non-empty strings")
    return tuple(value)
