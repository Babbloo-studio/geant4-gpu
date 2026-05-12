"""Small helper routines for benchmark-harness run.py.

Kept separate so the CLI module stays below the 500-line compact-file cap while
preserving fail-closed registry and workload-name behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    from bd001_review_gate import BD001ReviewGateError, bd001_review_gate
    from optimization_registry import DEFAULT_REGISTRY, require_entry
else:
    from .bd001_review_gate import BD001ReviewGateError, bd001_review_gate
    from .optimization_registry import DEFAULT_REGISTRY, require_entry

DEFAULT_BD001_SOURCE_REPO = Path(
    os.environ.get("G4GPU_BD001_SOURCE_REPO", "/projects/hep/fs10/shared/nnbar/billy/geant4-fork")
)

WORKLOAD_EVENT_NAMES = {
    "W1": "gamma_100mev",
    "W2": "muon_10gev",
    "W3": "nbar_carbon",
    "W4": "cosmic_shower",
    "gamma_100mev": "gamma_100mev",
    "muon_10gev": "muon_10gev",
    "nbar_carbon": "nbar_carbon",
    "cosmic_shower": "cosmic_shower",
    "optical_scintillator": "optical_scintillator",
    "beam_neutron": "beam_neutron",
}


def apply_registry_defaults(args) -> None:
    """Validate and apply optimization-registry metadata when requested."""

    if not args.require_registry:
        return
    if args.generate_reference:
        raise ValueError("--require-registry is only valid for optimized result runs, not reference generation")
    if not args.opt_id:
        raise ValueError("--require-registry requires --opt-id")
    entry = require_entry(args.opt_id, args.registry)
    if args.opt_id == "BD-geant4-001":
        _require_bd001_reviewed_registry(args)
    if args.opt_branch and args.opt_branch != entry.branch:
        raise ValueError(f"--opt-branch {args.opt_branch!r} conflicts with registry branch {entry.branch!r}")
    if args.opt_cmake_flags and args.opt_cmake_flags != entry.cmake_flags:
        raise ValueError("--opt-cmake-flags conflicts with registry cmake_flags")
    if entry.claim_level and args.claim_level != "L0" and args.claim_level != entry.claim_level:
        raise ValueError(f"--claim-level {args.claim_level!r} conflicts with registry claim_level {entry.claim_level!r}")
    if entry.notes and args.notes and args.notes != entry.notes:
        raise ValueError("--notes conflicts with registry notes")
    if entry.optimized_geant4_prefix is not None:
        registry_prefix = Path(entry.optimized_geant4_prefix)
        if args.optimized_geant4_prefix and args.optimized_geant4_prefix != registry_prefix:
            raise ValueError("--optimized-geant4-prefix conflicts with registry optimized_geant4_prefix")
        args.optimized_geant4_prefix = registry_prefix
    args.opt_branch = args.opt_branch or entry.branch
    args.opt_cmake_flags = args.opt_cmake_flags or entry.cmake_flags
    args.claim_level = entry.claim_level or args.claim_level
    args.notes = args.notes or entry.notes


def _require_bd001_reviewed_registry(args) -> None:
    """Require BD001 production registry rows to pass the source-backed review gate."""

    try:
        bd001_review_gate(args.registry, source_repo=args.bd001_source_repo)
    except BD001ReviewGateError as exc:
        raise ValueError(f"BD-geant4-001 reviewed-registry gate failed: {exc}") from exc


def event_name_for(workload_id: str) -> str:
    """Resolve the required event_name column value for a workload."""

    if workload_id in WORKLOAD_EVENT_NAMES:
        return WORKLOAD_EVENT_NAMES[workload_id]
    if workload_id.startswith("benchmark_"):
        return workload_id.removeprefix("benchmark_")
    raise ValueError(f"no event-name mapping for workload {workload_id!r}")


def print_scripts(planned: Sequence) -> None:
    """Print one or more planned sbatch scripts with deterministic separators."""

    if len(planned) == 1:
        print(planned[0].script)
        return
    for index, item in enumerate(planned):
        if index:
            print()
        print(f"# --- BEGIN {item.label} ---")
        print(item.script)
        print(f"# --- END {item.label} ---")
