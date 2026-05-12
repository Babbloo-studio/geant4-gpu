#!/usr/bin/env python3
"""Fail-closed SLURM runner for the benchmark harness.

This module only writes and optionally submits an ``sbatch`` script.  It never
executes a Geant4 benchmark binary directly on the LUNARC holder node.  The
generated script performs the compute-node work and then calls the future
``benchmarks.harness.run --collect`` entry point to append the Parquet result
row.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Sequence

if __package__ in (None, ""):
    from builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, resolve_workload
else:
    from .builder import DEFAULT_GEANT4_PREFIX, DEFAULT_PYTHON, REPO_ROOT, resolve_workload


DEFAULT_ACCOUNT = "lu2026-2-51"
DEFAULT_PARTITION = "lu48"
DEFAULT_TIME = "01:00:00"
DEFAULT_CPUS = 2
SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.-]+")


class RunnerError(RuntimeError):
    """Raised when the runner would produce unsafe or incomplete evidence."""


@dataclass(frozen=True)
class RunnerSpec:
    """Inputs required to generate one benchmark-harness SLURM script."""

    opt_id: str
    opt_branch: str
    workload: str
    physics_list: str
    hw_id: str
    seeds: tuple[int, ...]
    n_events: int
    vanilla_build: Path
    optimized_build: Path
    repo_root: Path = REPO_ROOT
    geant4_prefix: Path = DEFAULT_GEANT4_PREFIX
    python: Path = DEFAULT_PYTHON
    account: str = DEFAULT_ACCOUNT
    partition: str = DEFAULT_PARTITION
    time_limit: str = DEFAULT_TIME
    cpus_per_task: int = DEFAULT_CPUS
    raw_root: Path | None = None
    results_path: Path | None = None


def render_sbatch(spec: RunnerSpec) -> str:
    """Return a bash- and ``sbatch``-valid script for ``spec``."""

    _validate_spec(spec)
    workload = resolve_workload(spec.workload)
    raw_root = spec.raw_root or (
        spec.repo_root / "benchmarks/raw" / _sanitize(spec.opt_id) / workload.workload_id
    )
    results_path = spec.results_path or spec.repo_root / "benchmarks/results/results.parquet"
    vanilla_bin = _binary_path(spec.vanilla_build, workload.binary_rel)
    opt_bin = _binary_path(spec.optimized_build, workload.binary_rel)
    output_dir = raw_root / "%x-%j"
    job_name = _sanitize(f"g4gpu-{spec.opt_id}-{workload.workload_id}")[:48]
    seed_words = " ".join(str(seed) for seed in spec.seeds)

    lines = [
        "#!/usr/bin/env bash",
        f"#SBATCH --job-name={job_name}",
        f"#SBATCH --account={spec.account}",
        f"#SBATCH --partition={spec.partition}",
        f"#SBATCH --time={spec.time_limit}",
        f"#SBATCH --cpus-per-task={spec.cpus_per_task}",
        f"#SBATCH --output={output_dir}.out",
        f"#SBATCH --error={output_dir}.err",
        "",
        "set -euo pipefail",
        "",
        'if [[ -z "${SLURM_JOB_ID:-}" ]]; then',
        '  echo "ERROR: benchmark runner scripts must be launched with sbatch, not run on the holder node" >&2',
        "  exit 2",
        "fi",
        "",
        "module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \\",
        "  module load GCC/13.2.0 CUDA/12.8.0",
        "",
        f"REPO_ROOT={_quote(spec.repo_root)}",
        f"GEANT4_PREFIX={_quote(spec.geant4_prefix)}",
        f"PYTHON_BIN={_quote(spec.python)}",
        f"VANILLA_BIN={_quote(vanilla_bin)}",
        f"OPTIMIZED_BIN={_quote(opt_bin)}",
        f"RAW_ROOT={_quote(raw_root)}",
        f"RESULTS_PATH={_quote(results_path)}",
        f"OPT_ID={_quote(spec.opt_id)}",
        f"OPT_BRANCH={_quote(spec.opt_branch)}",
        f"WORKLOAD_ID={_quote(workload.workload_id)}",
        f"PHYSICS_LIST={_quote(spec.physics_list)}",
        f"HW_ID={_quote(spec.hw_id)}",
        f"N_EVENTS={int(spec.n_events)}",
        f"SEEDS=({seed_words})",
        "",
        'export GEANT4_PREFIX="${GEANT4_PREFIX}"',
        'export CMAKE_PREFIX_PATH="${GEANT4_PREFIX}:${GEANT4_PREFIX}/lib/CLHEP-2.4.6.2:${CMAKE_PREFIX_PATH:-}"',
        'export LD_LIBRARY_PATH="${GEANT4_PREFIX}/lib:${LD_LIBRARY_PATH:-}"',
        'export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"',
        'GEANT4_DATA="${GEANT4_PREFIX}/share/Geant4/data"',
        'export G4NEUTRONHPDATA="${GEANT4_DATA}/NDL4.7.1"',
        'export G4LEDATA="${GEANT4_DATA}/EMLOW8.5"',
        'export G4LEVELGAMMADATA="${GEANT4_DATA}/PhotonEvaporation5.7"',
        'export G4RADIOACTIVEDATA="${GEANT4_DATA}/RadioactiveDecay5.6"',
        'export G4PARTICLEXSDATA="${GEANT4_DATA}/PARTICLEXS4.0"',
        'export G4PIIDATA="${GEANT4_DATA}/PII1.3"',
        'export G4REALSURFACEDATA="${GEANT4_DATA}/RealSurface2.2"',
        'export G4SAIDXSDATA="${GEANT4_DATA}/SAIDDATA2.0"',
        'export G4ABLADATA="${GEANT4_DATA}/ABLA3.3"',
        'export G4INCLDATA="${GEANT4_DATA}/INCL1.2"',
        'export G4ENSDFSTATEDATA="${GEANT4_DATA}/ENSDFSTATE2.3"',
        "",
        'cd "${REPO_ROOT}"',
        'mkdir -p "${RAW_ROOT}" "$(dirname "${RESULTS_PATH}")"',
        '[[ -x "${VANILLA_BIN}" ]] || { echo "missing executable vanilla binary: ${VANILLA_BIN}" >&2; exit 2; }',
        '[[ -x "${OPTIMIZED_BIN}" ]] || { echo "missing executable optimized binary: ${OPTIMIZED_BIN}" >&2; exit 2; }',
        (
            '"${PYTHON_BIN}" -m benchmarks.harness.run --collect --collect-check >/dev/null 2>&1 || '
            '{ echo "COLLECTOR_NOT_IMPLEMENTED: benchmarks.harness.run --collect is still a stub" >&2; exit 2; }'
        ),
        "",
        "run_one() {",
        '  local variant="$1"',
        '  local binary="$2"',
        '  local seed="$3"',
        '  local out="${RAW_ROOT}/${variant}_seed_${seed}.parquet"',
        '  local log="${RAW_ROOT}/${variant}_seed_${seed}.txt"',
        '  echo "RUN variant=${variant} seed=${seed} binary=${binary}"',
        '  "${binary}" --events "${N_EVENTS}" --commit "${OPT_ID}_${variant}_seed_${seed}" --output "${out}" >"${log}" 2>&1',
        "}",
        "",
        'for seed in "${SEEDS[@]}"; do',
        '  export G4GPU_HARNESS_SEED="${seed}"',
        '  run_one vanilla "${VANILLA_BIN}" "${seed}"',
        '  run_one optimized "${OPTIMIZED_BIN}" "${seed}"',
        "done",
        "",
        '"${PYTHON_BIN}" -m benchmarks.harness.run --collect \\',
        '  --opt-id "${OPT_ID}" \\',
        '  --opt-branch "${OPT_BRANCH}" \\',
        '  --workload "${WORKLOAD_ID}" \\',
        '  --physics-list "${PHYSICS_LIST}" \\',
        '  --hw "${HW_ID}" \\',
        '  --n-events "${N_EVENTS}" \\',
        '  --seeds "${SEEDS[@]}" \\',
        '  --slurm-job-id "${SLURM_JOB_ID}" \\',
        '  --raw-dir "${RAW_ROOT}" \\',
        '  --results "${RESULTS_PATH}"',
        "",
    ]
    return "\n".join(lines)


def write_sbatch(spec: RunnerSpec, script_path: str | Path) -> Path:
    """Write ``spec`` as an executable sbatch script and return its path."""

    path = Path(script_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_sbatch(spec), encoding="utf-8")
    path.chmod(0o755)
    return path


def submit_sbatch(
    script_path: str | Path,
    *,
    dry_run: bool = False,
    sbatch: str | Path = "sbatch",
) -> str:
    """Submit ``script_path`` with ``sbatch`` and return the submitted job id."""

    path = Path(script_path)
    if not path.is_file():
        raise RunnerError(f"sbatch script is absent: {path}")
    if dry_run:
        return f"DRY_RUN {path}"
    proc = subprocess.run(
        [str(sbatch), str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RunnerError(f"sbatch failed with rc={proc.returncode}: {proc.stdout.strip()}")
    match = re.search(r"Submitted batch job\s+(\S+)", proc.stdout)
    if not match:
        raise RunnerError(f"cannot parse sbatch job id from: {proc.stdout.strip()}")
    return match.group(1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    spec = RunnerSpec(
        opt_id=args.opt_id,
        opt_branch=args.opt_branch,
        workload=args.workload,
        physics_list=args.physics_list,
        hw_id=args.hw,
        seeds=tuple(args.seed),
        n_events=args.n_events,
        vanilla_build=args.vanilla_build,
        optimized_build=args.optimized_build,
        repo_root=args.repo_root,
        geant4_prefix=args.geant4_prefix,
        python=args.python,
        account=args.account,
        partition=args.partition,
        time_limit=args.time,
        cpus_per_task=args.cpus_per_task,
        raw_root=args.raw_root,
        results_path=args.results_path,
    )
    script = render_sbatch(spec)
    if args.script:
        write_sbatch(spec, args.script)
    if args.submit:
        if args.dry_run:
            print(script)
            return 0
        script_path = args.script or (spec.repo_root / "benchmarks/raw" / _sanitize(spec.opt_id) / "run.sbatch")
        if not args.script:
            write_sbatch(spec, script_path)
        print(submit_sbatch(script_path, sbatch=args.sbatch))
        return 0
    print(script)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opt-id", required=True)
    parser.add_argument("--opt-branch", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--physics-list", required=True)
    parser.add_argument("--hw", required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--n-events", type=int, default=1000)
    parser.add_argument("--vanilla-build", type=Path, required=True)
    parser.add_argument("--optimized-build", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--geant4-prefix", type=Path, default=DEFAULT_GEANT4_PREFIX)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--partition", default=DEFAULT_PARTITION)
    parser.add_argument("--time", default=DEFAULT_TIME)
    parser.add_argument("--cpus-per-task", type=int, default=DEFAULT_CPUS)
    parser.add_argument("--raw-root", type=Path)
    parser.add_argument("--results-path", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--submit", action="store_true", help="submit with sbatch unless --dry-run is set")
    parser.add_argument("--dry-run", action="store_true", help="print the sbatch script and do not call sbatch")
    parser.add_argument("--sbatch", default="sbatch")
    return parser


def _validate_spec(spec: RunnerSpec) -> None:
    if spec.n_events <= 0:
        raise RunnerError("n_events must be positive")
    if spec.cpus_per_task <= 0:
        raise RunnerError("cpus_per_task must be positive")
    if not spec.seeds:
        raise RunnerError("at least one seed is required")
    if any(seed < 0 for seed in spec.seeds):
        raise RunnerError("seeds must be non-negative integers")
    for name, value in {
        "opt_id": spec.opt_id,
        "opt_branch": spec.opt_branch,
        "physics_list": spec.physics_list,
        "hw_id": spec.hw_id,
        "account": spec.account,
        "partition": spec.partition,
    }.items():
        if not str(value).strip():
            raise RunnerError(f"{name} must be non-empty")


def _binary_path(build_dir: Path, binary_rel: str) -> Path:
    return Path(build_dir) / binary_rel


def _sanitize(value: str) -> str:
    return SAFE_TOKEN.sub("-", str(value)).strip("-") or "unknown"


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        print(f"runner error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
