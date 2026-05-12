#!/usr/bin/env python3
"""CLI wiring for the G4GPU benchmark harness.

The CLI expands workload/physics-list/hardware matrices into fail-closed SLURM
scripts rendered by :mod:`benchmarks.harness.runner`.  Omitting ``--submit`` is
always a dry run: scripts are printed and no ``sbatch`` command is invoked.
Result collection and reference generation are present only as explicit stubs in
this compact task; future reference-generation work must replace the stubs
before any compute-node benchmark events are run for publication.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Sequence

if __package__ in (None, ""):
    from builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, BuildError, resolve_workload
    from runner import DEFAULT_ACCOUNT, DEFAULT_CPUS, DEFAULT_PARTITION, DEFAULT_TIME
    from runner import RunnerError, RunnerSpec, render_sbatch, submit_sbatch, write_sbatch
else:
    from .builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, BuildError, resolve_workload
    from .runner import DEFAULT_ACCOUNT, DEFAULT_CPUS, DEFAULT_PARTITION, DEFAULT_TIME
    from .runner import RunnerError, RunnerSpec, render_sbatch, submit_sbatch, write_sbatch


DEFAULT_N_SEEDS = 20
DEFAULT_N_EVENTS = 1000
DEFAULT_SEED_START = 1001
DEFAULT_BUILD_ROOT = REPO_ROOT / "benchmarks/builds"
SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.-]+")


class RunError(RuntimeError):
    """Raised when the run CLI would perform unsafe or incomplete work."""


@dataclass(frozen=True)
class PlannedScript:
    label: str
    spec: RunnerSpec
    script: str
    path: Path


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.collect:
            return _collect_stub(args)
        planned = _plan_scripts(args)
        if args.generate_reference:
            print("REFERENCE_GENERATION_STUB: dry-run script only; no reference Parquet will be generated.")
        if not args.submit or args.dry_run:
            _print_scripts(planned)
            if args.script_dir:
                for item in planned:
                    write_sbatch(item.spec, item.path)
            return 0
        if args.generate_reference:
            raise RunError("--generate-reference --submit is deferred to task 7; run without --submit for dry-run only")
        for item in planned:
            write_sbatch(item.spec, item.path)
            job_id = submit_sbatch(item.path, sbatch=args.sbatch)
            print(f"{item.label} {job_id}")
        return 0
    except (BuildError, RunnerError, RunError) as exc:
        print(f"run error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opt-id", help="optimization identifier, e.g. BD-geant4-032 or vanilla")
    parser.add_argument("--opt-branch", help="optimized branch/commit; defaults to opt-id for vanilla references")
    parser.add_argument("--opt-cmake-flags", default="", help="record-only flags for future collection metadata")
    parser.add_argument("--workload", nargs="+", help="one or more workload IDs such as W1 or gamma_100mev")
    parser.add_argument("--physics-list", nargs="+", help="one or more physics-list IDs such as PL1")
    parser.add_argument("--hw", nargs="+", help="one or more hardware IDs such as H3")
    parser.add_argument("--n-seeds", type=int, default=DEFAULT_N_SEEDS)
    parser.add_argument("--seed", action="append", type=int, help="explicit seed; may be repeated")
    parser.add_argument("--seeds", nargs="+", type=int, help="explicit seed list, used by --collect and dry runs")
    parser.add_argument("--n-events", type=int, default=DEFAULT_N_EVENTS)
    parser.add_argument("--vanilla-build", type=Path)
    parser.add_argument("--optimized-build", type=Path)
    parser.add_argument("--vanilla-build-root", type=Path, default=DEFAULT_BUILD_ROOT / "vanilla")
    parser.add_argument("--optimized-build-root", type=Path, default=DEFAULT_BUILD_ROOT / "optimized")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--geant4-prefix", type=Path, default=DEFAULT_GEANT4_PREFIX)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--partition", default=DEFAULT_PARTITION)
    parser.add_argument("--time", default=DEFAULT_TIME)
    parser.add_argument("--cpus-per-task", type=int, default=DEFAULT_CPUS)
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "benchmarks/results/results.parquet")
    parser.add_argument("--script-dir", type=Path, help="write one sbatch script per matrix point here")
    parser.add_argument("--submit", action="store_true", help="call sbatch after writing scripts")
    parser.add_argument("--dry-run", action="store_true", help="print scripts and do not call sbatch")
    parser.add_argument("--sbatch", default="sbatch")
    parser.add_argument("--generate-reference", action="store_true", help="stub for future vanilla reference generation")
    parser.add_argument("--collect", action="store_true", help="stub for compute-node raw-output collection")
    parser.add_argument("--collect-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--slurm-job-id", default="")
    parser.add_argument("--raw-dir", type=Path)
    return parser


def _collect_stub(args: argparse.Namespace) -> int:
    if args.dry_run:
        print("COLLECT_STUB: raw-output collection is not implemented in this compact task.")
        return 0
    message = "COLLECT_NOT_IMPLEMENTED: benchmarks.harness.run --collect is a fail-closed stub"
    if args.collect_check:
        print(message)
    else:
        print(message, file=sys.stderr)
    return 2


def _plan_scripts(args: argparse.Namespace) -> list[PlannedScript]:
    _validate_run_args(args)
    opt_id = args.opt_id or "vanilla"
    opt_branch = args.opt_branch or opt_id
    seeds = _seeds(args)
    planned: list[PlannedScript] = []
    for workload in args.workload:
        workload_spec = resolve_workload(workload)
        for physics_list in args.physics_list:
            for hw_id in args.hw:
                label = f"{workload_spec.workload_id}/{physics_list}/{hw_id}"
                spec = RunnerSpec(
                    opt_id=opt_id,
                    opt_branch=opt_branch,
                    workload=workload_spec.workload_id,
                    physics_list=physics_list,
                    hw_id=hw_id,
                    seeds=seeds,
                    n_events=args.n_events,
                    vanilla_build=_vanilla_build(args, workload_spec.workload_id),
                    optimized_build=_optimized_build(args, opt_id, workload_spec.workload_id),
                    repo_root=args.repo_root,
                    geant4_prefix=args.geant4_prefix,
                    python=args.python,
                    account=args.account,
                    partition=args.partition,
                    time_limit=args.time,
                    cpus_per_task=args.cpus_per_task,
                    raw_root=_raw_root(args, opt_id, workload_spec.workload_id, physics_list),
                    results_path=args.results,
                )
                script = render_sbatch(spec)
                planned.append(PlannedScript(label, spec, script, _script_path(args, opt_id, label)))
    return planned


def _validate_run_args(args: argparse.Namespace) -> None:
    missing = [name for name in ("opt_id", "workload", "physics_list", "hw") if not getattr(args, name)]
    if missing and not args.generate_reference:
        raise RunError(f"missing required arguments: {', '.join('--' + item.replace('_', '-') for item in missing)}")
    if args.generate_reference:
        for name in ("workload", "physics_list", "hw"):
            if not getattr(args, name):
                raise RunError(f"--generate-reference requires --{name.replace('_', '-')}")
    if args.n_events <= 0:
        raise RunError("--n-events must be positive")
    if args.n_seeds <= 0:
        raise RunError("--n-seeds must be positive")
    if args.seed and args.seeds:
        raise RunError("use either repeated --seed or --seeds, not both")
    if args.submit and args.dry_run and not args.script_dir:
        # Still safe, but make the no-side-effect behavior explicit in stdout.
        pass


def _seeds(args: argparse.Namespace) -> tuple[int, ...]:
    explicit = args.seeds if args.seeds is not None else args.seed
    if explicit is not None:
        values = tuple(int(seed) for seed in explicit)
    else:
        values = tuple(range(DEFAULT_SEED_START, DEFAULT_SEED_START + args.n_seeds))
    if not values:
        raise RunError("at least one seed is required")
    if any(seed < 0 for seed in values):
        raise RunError("seeds must be non-negative integers")
    return values


def _vanilla_build(args: argparse.Namespace, workload: str) -> Path:
    return args.vanilla_build or args.vanilla_build_root / _sanitize(workload)


def _optimized_build(args: argparse.Namespace, opt_id: str, workload: str) -> Path:
    return args.optimized_build or args.optimized_build_root / _sanitize(opt_id) / _sanitize(workload)


def _raw_root(args: argparse.Namespace, opt_id: str, workload: str, physics_list: str) -> Path | None:
    if args.generate_reference:
        return args.repo_root / "benchmarks/reference" / _sanitize(workload) / _sanitize(physics_list)
    return args.repo_root / "benchmarks/raw" / _sanitize(opt_id) / _sanitize(workload) / _sanitize(physics_list)


def _script_path(args: argparse.Namespace, opt_id: str, label: str) -> Path:
    filename = f"run_{_sanitize(label)}.sbatch"
    root = args.script_dir or args.repo_root / "benchmarks/raw" / _sanitize(opt_id)
    return root / filename


def _print_scripts(planned: Sequence[PlannedScript]) -> None:
    if len(planned) == 1:
        print(planned[0].script)
        return
    for index, item in enumerate(planned):
        if index:
            print()
        print(f"# --- BEGIN {item.label} ---")
        print(item.script)
        print(f"# --- END {item.label} ---")


def _sanitize(value: str) -> str:
    return SAFE_TOKEN.sub("-", str(value)).strip("-") or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
