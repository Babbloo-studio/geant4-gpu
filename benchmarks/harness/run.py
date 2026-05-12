#!/usr/bin/env python3
"""CLI wiring and collection for the G4GPU benchmark harness.

The CLI expands workload/physics-list/hardware matrices into fail-closed SLURM
scripts rendered by :mod:`benchmarks.harness.runner`.  Omitting ``--submit`` is
always a dry run: scripts are printed and no ``sbatch`` command is invoked.
Compute-node collection is implemented here: it validates raw per-seed Parquet
outputs, applies the KS parity gate for optimized runs, writes append-only result
rows, and writes a reference manifest for vanilla reference generation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import statistics
import sys
import tempfile
from typing import Sequence

import pyarrow as pa
import pyarrow.parquet as pq

if __package__ in (None, ""):
    from builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, BuildError, resolve_workload
    from optimization_registry import OptimizationRegistryError
    from parity import parity_gate
    from run_helpers import DEFAULT_BD001_SOURCE_REPO, DEFAULT_REGISTRY, apply_registry_defaults, event_name_for, print_scripts
    from runner import DEFAULT_ACCOUNT, DEFAULT_CPUS, DEFAULT_PARTITION, DEFAULT_TIME
    from runner import RunnerError, RunnerSpec, render_sbatch, submit_sbatch, write_sbatch
    from schema import CLAIM_LEVELS, BenchmarkResultRow, read_rows, result_tag_for, utc_timestamp, write_rows
else:
    from .builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, BuildError, resolve_workload
    from .optimization_registry import OptimizationRegistryError
    from .parity import parity_gate
    from .run_helpers import DEFAULT_BD001_SOURCE_REPO, DEFAULT_REGISTRY, apply_registry_defaults, event_name_for, print_scripts
    from .runner import DEFAULT_ACCOUNT, DEFAULT_CPUS, DEFAULT_PARTITION, DEFAULT_TIME
    from .runner import RunnerError, RunnerSpec, render_sbatch, submit_sbatch, write_sbatch
    from .schema import CLAIM_LEVELS, BenchmarkResultRow, read_rows, result_tag_for, utc_timestamp, write_rows


DEFAULT_N_SEEDS = 20
DEFAULT_N_EVENTS = 1000
DEFAULT_SEED_START = 1001
DEFAULT_BUILD_ROOT = REPO_ROOT / "benchmarks/builds"
DEFAULT_GEANT4_VERSION = "v11.2.2"
SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.-]+")
class RunError(RuntimeError):
    """Raised when the run CLI would perform unsafe or incomplete work."""


@dataclass(frozen=True)
class PlannedScript:
    label: str
    spec: RunnerSpec
    script: str
    path: Path


@dataclass(frozen=True)
class RawMetrics:
    path: Path
    table: pa.Table
    wall_s: float
    steps_per_event: float


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        apply_registry_defaults(args)
        if args.collect:
            return _collect(args)
        planned = _plan_scripts(args)
        if args.generate_reference and (not args.submit or args.dry_run):
            print("# REFERENCE_GENERATION_DRY_RUN: scripts only; no sbatch submission or event execution.")
        if not args.submit or args.dry_run:
            print_scripts(planned)
            if args.script_dir:
                for item in planned:
                    write_sbatch(item.spec, item.path)
            return 0
        for item in planned:
            write_sbatch(item.spec, item.path)
            job_id = submit_sbatch(item.path, sbatch=args.sbatch)
            print(f"{item.label} {job_id}")
        return 0
    except (BuildError, OptimizationRegistryError, RunnerError, RunError, ValueError) as exc:
        print(f"run error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opt-id", help="optimization identifier, e.g. BD-geant4-032 or vanilla")
    parser.add_argument("--opt-branch", help="optimized branch/commit; defaults to opt-id for vanilla references")
    parser.add_argument("--opt-cmake-flags", default="", help="CMake flags recorded in result rows")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="optimization registry YAML path")
    parser.add_argument(
        "--bd001-source-repo",
        type=Path,
        default=DEFAULT_BD001_SOURCE_REPO,
        help="Geant4 source repo used to review-gate BD-geant4-001 registry rows",
    )
    parser.add_argument(
        "--require-registry",
        action="store_true",
        help="fail closed unless --opt-id has a validated registry entry; fill omitted metadata from that row",
    )
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
    parser.add_argument("--optimized-geant4-prefix", type=Path, help="optimized Geant4 install prefix for source-level Geant4 changes")
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
    parser.add_argument("--generate-reference", action="store_true", help="collect vanilla reference outputs")
    parser.add_argument("--collect", action="store_true", help="collect compute-node raw outputs")
    parser.add_argument("--collect-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--slurm-job-id", default="")
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--claim-level", default="L0")
    parser.add_argument("--geant4-version", default=DEFAULT_GEANT4_VERSION)
    parser.add_argument("--notes", default="")
    return parser


def _collect(args: argparse.Namespace) -> int:
    if args.collect_check:
        print("COLLECT_READY")
        return 0
    workload = resolve_workload(_single(args.workload, "workload"))
    physics_list = _single(args.physics_list, "physics-list")
    hw_id = _single(args.hw, "hw")
    seeds = _seeds(args)
    raw_dir = args.raw_dir
    if raw_dir is None:
        raise RunError("--collect requires --raw-dir")
    if args.n_events <= 0:
        raise RunError("--n-events must be positive")
    expected_event = event_name_for(workload.workload_id)
    if args.generate_reference:
        manifest = _collect_reference(args.repo_root, raw_dir, workload.workload_id, expected_event, seeds, args.n_events)
        print(
            "REFERENCE_COLLECTED "
            f"workload={workload.workload_id} physics={physics_list} hw={hw_id} "
            f"seeds={len(seeds)} manifest={manifest}"
        )
        return 0
    if not args.slurm_job_id:
        raise RunError("--collect requires --slurm-job-id")
    row = _collect_result_row(args, raw_dir, workload.workload_id, expected_event, physics_list, hw_id, seeds)
    _append_result(args.results, row)
    print(
        "RESULT_COLLECTED "
        f"opt_id={row.opt_id} workload={row.workload_id} physics={row.physics_list} "
        f"hw={row.hw_id} speedup={row.speedup_mean:.6g} parity={row.parity_pass} "
        f"results={args.results}"
    )
    return 0


def _collect_result_row(
    args: argparse.Namespace,
    raw_dir: Path,
    workload_id: str,
    expected_event: str,
    physics_list: str,
    hw_id: str,
    seeds: tuple[int, ...],
) -> BenchmarkResultRow:
    vanilla = [
        _read_raw_metrics(raw_dir / f"vanilla_seed_{seed}.parquet", expected_event, args.n_events)
        for seed in seeds
    ]
    optimized = [
        _read_raw_metrics(raw_dir / f"optimized_seed_{seed}.parquet", expected_event, args.n_events)
        for seed in seeds
    ]
    with tempfile.TemporaryDirectory(prefix="g4gpu-harness-collect-") as tmp_dir:
        vanilla_path = Path(tmp_dir) / "vanilla.parquet"
        optimized_path = Path(tmp_dir) / "optimized.parquet"
        pq.write_table(_concat_tables([item.table for item in vanilla]), vanilla_path)
        pq.write_table(_concat_tables([item.table for item in optimized]), optimized_path)
        try:
            parity = parity_gate(vanilla_path, optimized_path)
        except Exception as exc:  # noqa: BLE001 - surface parity details as fail-closed RunError
            raise RunError(f"parity/reference input validation failed: {exc}") from exc
    wall_v = [item.wall_s for item in vanilla]
    wall_o = [item.wall_s for item in optimized]
    speedups = [v / o for v, o in zip(wall_v, wall_o, strict=True)]
    speedup_mean = _mean(wall_v) / _mean(wall_o)
    lo, hi = _ci95(speedups)
    parity_pass = bool(parity.passed)
    return BenchmarkResultRow(
        opt_id=args.opt_id or "unknown",
        opt_branch=args.opt_branch or args.opt_id or "unknown",
        opt_cmake_flags=args.opt_cmake_flags,
        workload_id=workload_id,
        physics_list=physics_list,
        hw_id=hw_id,
        slurm_job_id=args.slurm_job_id,
        geant4_version=args.geant4_version,
        n_events=args.n_events,
        n_seeds=len(seeds),
        seeds=list(seeds),
        wall_s_vanilla=_mean(wall_v),
        wall_s_opt=_mean(wall_o),
        wall_s_vanilla_std=_std(wall_v),
        wall_s_opt_std=_std(wall_o),
        speedup_mean=speedup_mean,
        speedup_ci95_lo=lo,
        speedup_ci95_hi=hi,
        steps_per_event_vanilla=_mean([item.steps_per_event for item in vanilla]),
        steps_per_event_opt=_mean([item.steps_per_event for item in optimized]),
        ks_edep_p=_required_pvalue(parity.ks_stats, "edep_total"),
        ks_stepcount_p=_required_pvalue(parity.ks_stats, "step_count"),
        ks_secondary_p=_required_pvalue(parity.ks_stats, "secondary_multiplicity"),
        ks_firststepl_p=_required_pvalue(parity.ks_stats, "first_step_length"),
        ks_neutron_p=parity.ks_stats.get("neutron_capture_rate"),
        parity_pass=parity_pass,
        claim_level=args.claim_level,
        result_tag=result_tag_for(lo, parity_pass),
        perf_instructions=None,
        perf_cache_misses=None,
        notes=args.notes,
        timestamp=utc_timestamp(),
    )


def _collect_reference(
    repo_root: Path,
    raw_dir: Path,
    workload_id: str,
    expected_event: str,
    seeds: tuple[int, ...],
    n_events: int,
) -> Path:
    raw_dir = Path(raw_dir)
    reference_root = Path(repo_root) / "benchmarks/reference"
    try:
        raw_dir.relative_to(reference_root)
    except ValueError as exc:
        raise RunError(f"reference raw directory must be under {reference_root}: {raw_dir}") from exc
    for seed in seeds:
        _read_raw_metrics(raw_dir / f"seed_{seed}.parquet", expected_event, n_events)
    manifest = reference_root / "MANIFEST.sha256"
    entries: list[str] = []
    for path in sorted(reference_root.rglob("*.parquet")):
        rel = path.relative_to(reference_root).as_posix()
        entries.append(f"{_sha256(path)}  {rel}\n")
    if not entries:
        raise RunError(f"no reference Parquet files found under {reference_root}")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("".join(entries), encoding="utf-8")
    # Fail closed if the requested workload directory was not represented.
    needle = f"{workload_id}/"
    if not any(needle in entry for entry in entries):
        raise RunError(f"manifest did not include requested workload {workload_id}")
    return manifest


def _read_raw_metrics(path: Path, expected_event: str, n_events: int) -> RawMetrics:
    if not path.is_file():
        raise RunError(f"missing raw file: {path}")
    try:
        table = pq.read_table(path)
    except Exception as exc:  # noqa: BLE001
        raise RunError(f"malformed raw Parquet {path}: {exc}") from exc
    if table.num_rows != n_events:
        raise RunError(f"{path} has {table.num_rows} rows, expected --n-events {n_events}")
    for column in ("event_name", "total_wall_time_ns", "per_step_time_ns", "step_count"):
        if column not in table.column_names:
            raise RunError(f"{path} missing required metric column {column!r}")
    names = {str(value) for value in table["event_name"].combine_chunks().to_pylist() if value is not None}
    if names != {expected_event}:
        raise RunError(f"{path} event_name mismatch: expected {expected_event!r}, got {sorted(names)!r}")
    wall_values = _finite_values(table, "total_wall_time_ns", path)
    unique_wall = {int(value) for value in wall_values}
    if len(unique_wall) != 1:
        raise RunError(f"{path} total_wall_time_ns must be constant within one seed")
    wall_ns = next(iter(unique_wall))
    if wall_ns <= 0:
        raise RunError(f"{path} total_wall_time_ns must be positive")
    steps = _finite_values(table, "step_count", path)
    if any(value <= 0 for value in steps):
        raise RunError(f"{path} step_count values must be positive")
    per_step = _finite_values(table, "per_step_time_ns", path)
    if any(value <= 0 for value in per_step):
        raise RunError(f"{path} per_step_time_ns values must be positive")
    return RawMetrics(path=path, table=table, wall_s=wall_ns / 1.0e9, steps_per_event=_mean(steps))


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
                    opt_cmake_flags=args.opt_cmake_flags,
                    workload=workload_spec.workload_id,
                    physics_list=physics_list,
                    hw_id=hw_id,
                    seeds=seeds,
                    n_events=args.n_events,
                    vanilla_build=_vanilla_build(args, workload_spec.workload_id),
                    optimized_build=_optimized_build(args, opt_id, workload_spec.workload_id),
                    repo_root=args.repo_root,
                    geant4_prefix=args.geant4_prefix,
                    optimized_geant4_prefix=args.optimized_geant4_prefix,
                    python=args.python,
                    account=args.account,
                    partition=args.partition,
                    time_limit=args.time,
                    cpus_per_task=args.cpus_per_task,
                    raw_root=_raw_root(args, opt_id, workload_spec.workload_id, physics_list),
                    results_path=args.results,
                    reference_mode=args.generate_reference,
                    claim_level=args.claim_level,
                    geant4_version=args.geant4_version,
                    notes=args.notes,
                )
                script = render_sbatch(spec)
                planned.append(PlannedScript(label, spec, script, _script_path(args, opt_id, label)))
    return planned


def _validate_run_args(args: argparse.Namespace) -> None:
    missing = [name for name in ("workload", "physics_list", "hw") if not getattr(args, name)]
    if missing:
        raise RunError(f"missing required arguments: {', '.join('--' + item.replace('_', '-') for item in missing)}")
    if not args.generate_reference and not args.opt_id:
        raise RunError("missing required argument: --opt-id")
    if args.n_events <= 0:
        raise RunError("--n-events must be positive")
    if args.n_seeds <= 0:
        raise RunError("--n-seeds must be positive")
    if args.seed and args.seeds:
        raise RunError("use either repeated --seed or --seeds, not both")
    if args.claim_level not in CLAIM_LEVELS:
        raise RunError(f"--claim-level must be one of {sorted(CLAIM_LEVELS)}")
    if args.claim_level == "L3" and args.notes:
        raise RunError("--notes must be empty for L3 rows")
    if not str(args.geant4_version).strip():
        raise RunError("--geant4-version must be non-empty")
    if not args.generate_reference and args.opt_id == "BD-geant4-001":
        if args.optimized_geant4_prefix is None:
            raise RunError("BD-geant4-001 requires --optimized-geant4-prefix for Geant4-source optimization selection")
        if args.optimized_geant4_prefix == args.geant4_prefix:
            raise RunError("BD-geant4-001 --optimized-geant4-prefix must differ from --geant4-prefix")


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


def _single(values: Sequence[str] | None, label: str) -> str:
    if not values:
        raise RunError(f"--collect requires --{label}")
    if len(values) != 1:
        raise RunError(f"--collect accepts exactly one --{label} value")
    return values[0]


def _finite_values(table: pa.Table, column: str, path: Path) -> list[float]:
    values: list[float] = []
    for value in table[column].combine_chunks().to_pylist():
        if value is None:
            continue
        number = float(value)
        if math.isfinite(number):
            values.append(number)
    if len(values) != table.num_rows:
        raise RunError(f"{path} column {column!r} contains null or non-finite values")
    return values


def _concat_tables(tables: Sequence[pa.Table]) -> pa.Table:
    if not tables:
        raise RunError("cannot concatenate an empty table list")
    return pa.concat_tables(list(tables), promote_options="default")


def _append_result(path: Path, row: BenchmarkResultRow) -> None:
    rows = read_rows(path) if Path(path).is_file() else []
    write_rows(Path(path), [*rows, row])


def _required_pvalue(stats: dict[str, float | None], name: str) -> float:
    value = stats.get(name)
    if value is None:
        raise RunError(f"parity gate did not produce required p-value {name}")
    return float(value)


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise RunError("cannot compute a mean from no values")
    return float(statistics.fmean(values))


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(statistics.stdev(values))


def _ci95(values: Sequence[float]) -> tuple[float, float]:
    center = _mean(values)
    if len(values) < 2:
        return center, center
    half_width = 1.96 * _std(values) / math.sqrt(len(values))
    return center - half_width, center + half_width


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitize(value: str) -> str:
    return SAFE_TOKEN.sub("-", str(value)).strip("-") or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
