#!/usr/bin/env python3
"""Fixture-only preflight checks for future NNBAR W5/W6 adapters.

This module validates evidence that must exist before canonical W5/W6 aliases can
be enabled.  It deliberately performs no detector execution, no SLURM
submission, and no reference generation.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Mapping, Sequence

import pyarrow.parquet as pq

EXPECTED_EVENTS = {"W5": 1000, "W6": 500}
EXPECTED_WORKLOAD_NAMES = {"W5": "nnbar_signal_full_event", "W6": "nnbar_cosmic_mu_full_event"}
REQUIRED_COLUMNS = frozenset(
    {
        "event_name",
        "total_deposited_energy_mev",
        "step_count",
        "particle_multiplicity",
        "first_step_length_mm",
        "total_wall_time_ns",
        "per_step_time_ns",
    }
)
SEED_HOOK_PATTERNS = ("{seed}", "${G4GPU_SEED}", "$G4GPU_SEED", "/random/setSeeds")
ISOLATION_RE = re.compile(
    r"#\s*include\s*[<\"].*(NNBAR_Detector|nnbar)|"
    r"target_link_libraries\s*\([^\)]*(NNBAR|nnbar)|"
    r"add_subdirectory\s*\([^\)]*(NNBAR|nnbar)",
    re.IGNORECASE,
)
SOURCE_SUFFIXES = {".cc", ".cu", ".cxx", ".cpp", ".hh", ".hpp", ".h", ".cmake", ".txt"}


@dataclass(frozen=True)
class AdapterEvidence:
    workload_id: str
    executable: Path
    macro: Path
    schema_sample: Path
    n_events: int
    seeds: tuple[int, ...]
    g4gpu_repo: Path


@dataclass(frozen=True)
class PreflightReport:
    workload_id: str
    ok: bool
    blockers: tuple[str, ...]

    def require_ok(self) -> None:
        if not self.ok:
            raise PreflightError("; ".join(self.blockers))


class PreflightError(RuntimeError):
    """Raised when fixture evidence is insufficient for W5/W6 enablement."""


def check_adapter_preflight(evidence: AdapterEvidence) -> PreflightReport:
    """Return fail-closed preflight status for one future W5/W6 adapter."""

    workload = evidence.workload_id.upper()
    blockers: list[str] = []
    if workload not in EXPECTED_EVENTS:
        blockers.append(f"NNBAR_WORKLOAD: unsupported workload {evidence.workload_id!r}")
    blockers.extend(_check_executable(evidence.executable, evidence.g4gpu_repo))
    blockers.extend(_check_macro(evidence.macro, workload))
    blockers.extend(_check_schema(evidence.schema_sample, workload))
    blockers.extend(_check_event_count(evidence.n_events, workload))
    blockers.extend(_check_seeds(evidence.seeds, evidence.macro))
    blockers.extend(_check_isolation(evidence.g4gpu_repo))
    return PreflightReport(workload, not blockers, tuple(blockers))


def check_w5_w6_preflight(items: Mapping[str, AdapterEvidence]) -> tuple[PreflightReport, ...]:
    """Check both canonical W5/W6 adapters without enabling their aliases."""

    reports = []
    for workload in ("W5", "W6"):
        evidence = items.get(workload)
        if evidence is None:
            reports.append(PreflightReport(workload, False, (f"NNBAR_{workload}: missing evidence",)))
            continue
        reports.append(check_adapter_preflight(evidence))
    return tuple(reports)


def _check_executable(executable: Path, repo: Path) -> list[str]:
    blockers: list[str] = []
    path = executable.resolve(strict=False)
    repo_path = repo.resolve(strict=False)
    if not path.exists():
        blockers.append(f"NNBAR_EXECUTABLE: missing {executable}")
    elif not path.is_file() or not os.access(path, os.X_OK):
        blockers.append(f"NNBAR_EXECUTABLE: not executable {executable}")
    try:
        path.relative_to(repo_path)
    except ValueError:
        pass
    else:
        blockers.append("NNBAR_EXECUTABLE: executable must be outside the G4GPU repo")
    return blockers


def _check_macro(macro: Path, workload: str) -> list[str]:
    if not macro.exists():
        return [f"NNBAR_MACRO_{workload}: missing {macro}"]
    text = macro.read_text(encoding="utf-8", errors="replace")
    blockers = []
    if "FTFP_BERT" not in text:
        blockers.append(f"NNBAR_MACRO_{workload}: macro does not pin FTFP_BERT")
    expected_name = EXPECTED_WORKLOAD_NAMES.get(workload, "")
    if expected_name and expected_name not in text:
        blockers.append(f"NNBAR_MACRO_{workload}: missing adapter label {expected_name}")
    return blockers


def _check_schema(sample: Path, workload: str) -> list[str]:
    if not sample.exists():
        return [f"NNBAR_OUTPUT_SCHEMA_{workload}: missing {sample}"]
    try:
        schema = pq.read_schema(sample)
    except Exception as exc:  # noqa: BLE001 - surface PyArrow detail in blocker
        return [f"NNBAR_OUTPUT_SCHEMA_{workload}: unreadable schema: {exc}"]
    missing = sorted(REQUIRED_COLUMNS.difference(schema.names))
    if missing:
        return [f"NNBAR_OUTPUT_SCHEMA_{workload}: missing columns {','.join(missing)}"]
    return []


def _check_event_count(n_events: int, workload: str) -> list[str]:
    expected = EXPECTED_EVENTS.get(workload)
    if expected is None:
        return []
    if n_events != expected:
        return [f"NNBAR_EVENT_COUNT_{workload}: expected {expected}, got {n_events}"]
    return []


def _check_seeds(seeds: Sequence[int], macro: Path) -> list[str]:
    if tuple(seeds) != tuple(range(1001, 1021)):
        return ["NNBAR_SEEDS: expected harness seed set 1001--1020"]
    if not macro.exists():
        return []
    text = macro.read_text(encoding="utf-8", errors="replace")
    if not any(pattern in text for pattern in SEED_HOOK_PATTERNS):
        return ["NNBAR_SEEDS: macro has no deterministic seed hook"]
    return []


def _check_isolation(repo: Path) -> list[str]:
    if not repo.exists():
        return [f"NNBAR_ISOLATION_OK: missing G4GPU repo {repo}"]
    hits = []
    for path in _source_paths(repo):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in ISOLATION_RE.finditer(text):
            hits.append(f"{path.relative_to(repo)}:{text[:match.start()].count(chr(10)) + 1}")
    if hits:
        return ["NNBAR_ISOLATION_OK: forbidden include/link references " + ",".join(hits)]
    return []


def _source_paths(repo: Path) -> list[Path]:
    roots = [repo / "CMakeLists.txt", repo / "include", repo / "src", repo / "benchmarks" / "events"]
    paths: list[Path] = []
    for root in roots:
        if root.is_file():
            paths.append(root)
        elif root.is_dir():
            paths.extend(p for p in root.rglob("*") if p.is_file() and p.suffix in SOURCE_SUFFIXES)
    return paths
