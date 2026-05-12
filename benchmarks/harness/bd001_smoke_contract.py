#!/usr/bin/env python3
"""Fail-closed guarded-smoke contract for BD-geant4-001.

The contract is intentionally read-only.  It validates that a future BD-001
smoke/result-row attempt is pinned to the reviewed source ref, an existing
reference dataset manifest, a non-promotional result tag, and explicit
no-promotion checks before any SLURM/event/result-row work is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

if __package__ in (None, ""):
    from bd001_review_gate import BD001ReviewGateError, BD001ReviewGateResult, bd001_review_gate
    from schema import CLAIM_LEVELS, RESULT_TAGS
else:
    from .bd001_review_gate import BD001ReviewGateError, BD001ReviewGateResult, bd001_review_gate
    from .schema import CLAIM_LEVELS, RESULT_TAGS


REQUIRED_CONTRACT_FIELDS = (
    "opt_id",
    "source_ref",
    "reference_dataset",
    "result_tag",
    "no_promotion_checks",
)
OPTIONAL_CONTRACT_FIELDS = ("claim_level", "workloads", "physics_lists", "notes")
ALLOWED_CONTRACT_FIELDS = frozenset((*REQUIRED_CONTRACT_FIELDS, *OPTIONAL_CONTRACT_FIELDS))
REQUIRED_NO_PROMOTION_CHECKS = frozenset(
    {
        "result_tag_not_speedup",
        "claim_level_not_paper",
        "manual_promotion_required",
        "dry_run_no_results_append",
    }
)
MANIFEST_RE = re.compile(r"^[0-9a-f]{64}  (.+)$")


class BD001SmokeContractError(RuntimeError):
    """Raised when the BD-001 guarded-smoke contract is incomplete."""


@dataclass(frozen=True)
class BD001SmokeContractResult:
    opt_id: str
    source_ref: str
    reference_dataset: Path
    result_tag: str
    claim_level: str
    no_promotion_checks: tuple[str, ...]
    manifest_entries: tuple[str, ...]
    review_gate: BD001ReviewGateResult


def bd001_guarded_smoke_contract(
    contract: str | Path | Mapping[str, Any],
    *,
    registry: str | Path,
    source_repo: str | Path,
    opt_id: str = "BD-geant4-001",
    require_prefix_config: bool = False,
) -> BD001SmokeContractResult:
    """Validate a future BD-001 guarded-smoke/result-row contract."""

    if opt_id != "BD-geant4-001":
        raise BD001SmokeContractError("bd001_guarded_smoke_contract only accepts opt_id='BD-geant4-001'")
    raw = _load_contract(contract)
    unknown = sorted(set(raw) - ALLOWED_CONTRACT_FIELDS)
    if unknown:
        raise BD001SmokeContractError(f"{opt_id}: unknown contract fields are not allowed: {unknown}")
    missing = [field for field in REQUIRED_CONTRACT_FIELDS if field not in raw]
    if missing:
        raise BD001SmokeContractError(f"{opt_id}: missing contract fields: {missing}")
    if raw["opt_id"] != opt_id:
        raise BD001SmokeContractError(f"contract opt_id must be {opt_id!r}")

    try:
        review = bd001_review_gate(
            registry,
            source_repo=source_repo,
            opt_id=opt_id,
            require_prefix_config=require_prefix_config,
        )
    except BD001ReviewGateError as exc:
        raise BD001SmokeContractError(str(exc)) from exc

    expected_source_ref = f"{review.branch}@{review.commit}"
    source_ref = _non_empty_string(raw["source_ref"], "source_ref")
    if source_ref != expected_source_ref:
        raise BD001SmokeContractError(
            f"{opt_id}: source_ref must match reviewed implementation {expected_source_ref}"
        )

    reference_dataset = _reference_dataset(raw["reference_dataset"], opt_id)
    manifest_entries = _manifest_entries(reference_dataset, opt_id)
    workloads = _optional_string_list(raw.get("workloads"), "workloads")
    physics_lists = _optional_string_list(raw.get("physics_lists"), "physics_lists")
    _require_manifest_coverage(opt_id, manifest_entries, workloads, physics_lists)

    result_tag = _non_empty_string(raw["result_tag"], "result_tag")
    if result_tag not in RESULT_TAGS:
        raise BD001SmokeContractError(f"{opt_id}: result_tag must be one of {sorted(RESULT_TAGS)}")
    if result_tag == "SPEEDUP":
        raise BD001SmokeContractError(f"{opt_id}: guarded smoke may not contract a SPEEDUP result_tag")

    claim_level = _non_empty_string(raw.get("claim_level", "L2"), "claim_level")
    if claim_level not in CLAIM_LEVELS:
        raise BD001SmokeContractError(f"{opt_id}: claim_level must be one of {sorted(CLAIM_LEVELS)}")
    if claim_level in {"L3", "L4"}:
        raise BD001SmokeContractError(f"{opt_id}: guarded smoke may not promote to paper-ready claim_level")

    checks = _string_list(raw["no_promotion_checks"], "no_promotion_checks")
    missing_checks = sorted(REQUIRED_NO_PROMOTION_CHECKS - set(checks))
    if missing_checks:
        raise BD001SmokeContractError(f"{opt_id}: missing no_promotion_checks: {missing_checks}")

    return BD001SmokeContractResult(
        opt_id=opt_id,
        source_ref=source_ref,
        reference_dataset=reference_dataset,
        result_tag=result_tag,
        claim_level=claim_level,
        no_promotion_checks=checks,
        manifest_entries=manifest_entries,
        review_gate=review,
    )


def _load_contract(contract: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(contract, Mapping):
        raw: Any = dict(contract)
    else:
        path = Path(contract)
        if not path.is_file():
            raise BD001SmokeContractError(f"guarded-smoke contract missing: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise BD001SmokeContractError(f"cannot parse guarded-smoke contract: {exc}") from exc
    if not isinstance(raw, dict) or not raw:
        raise BD001SmokeContractError("guarded-smoke contract must be a non-empty mapping")
    return raw


def _reference_dataset(value: Any, opt_id: str) -> Path:
    dataset = Path(_non_empty_string(value, "reference_dataset"))
    if not dataset.is_absolute():
        raise BD001SmokeContractError(f"{opt_id}: reference_dataset must be an absolute path")
    if not dataset.is_dir():
        raise BD001SmokeContractError(f"{opt_id}: reference_dataset directory is missing: {dataset}")
    if not (dataset / "MANIFEST.sha256").is_file():
        raise BD001SmokeContractError(f"{opt_id}: reference_dataset must contain MANIFEST.sha256")
    return dataset


def _manifest_entries(dataset: Path, opt_id: str) -> tuple[str, ...]:
    entries: list[str] = []
    for line in (dataset / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = MANIFEST_RE.fullmatch(line)
        if not match:
            raise BD001SmokeContractError(f"{opt_id}: malformed reference manifest line: {line!r}")
        rel = match.group(1)
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise BD001SmokeContractError(f"{opt_id}: unsafe reference manifest path: {rel}")
        path = dataset / rel_path
        if not path.is_file():
            raise BD001SmokeContractError(f"{opt_id}: manifest entry missing from dataset: {rel}")
        if not rel.endswith(".parquet"):
            raise BD001SmokeContractError(f"{opt_id}: reference manifest entries must be parquet files: {rel}")
        entries.append(rel)
    if not entries:
        raise BD001SmokeContractError(f"{opt_id}: reference manifest contains no parquet entries")
    return tuple(entries)


def _require_manifest_coverage(
    opt_id: str,
    entries: tuple[str, ...],
    workloads: tuple[str, ...],
    physics_lists: tuple[str, ...],
) -> None:
    for workload in workloads:
        needle = f"{workload}/"
        if not any(needle in entry for entry in entries):
            raise BD001SmokeContractError(f"{opt_id}: reference_dataset lacks workload {workload!r}")
    for physics_list in physics_lists:
        needle = f"/{physics_list}/"
        if not any(needle in f"/{entry}" for entry in entries):
            raise BD001SmokeContractError(f"{opt_id}: reference_dataset lacks physics_list {physics_list!r}")


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BD001SmokeContractError(f"{field} must be a non-empty string")
    return value


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BD001SmokeContractError(f"{field} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise BD001SmokeContractError(f"{field} entries must be non-empty strings")
    return tuple(value)


def _optional_string_list(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    return _string_list(value, field)


__all__ = [
    "BD001SmokeContractError",
    "BD001SmokeContractResult",
    "REQUIRED_NO_PROMOTION_CHECKS",
    "bd001_guarded_smoke_contract",
]
