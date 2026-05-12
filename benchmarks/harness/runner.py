#!/usr/bin/env python3
"""Fail-closed SLURM runner for the benchmark harness.

This module only writes and optionally submits an ``sbatch`` script.  It never
executes a Geant4 benchmark binary directly on the LUNARC holder node.  The
generated script performs the compute-node work and then calls
``benchmarks.harness.run --collect`` to append the Parquet result row or update
the vanilla reference manifest.
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
    optimized_geant4_prefix: Path | None = None
    python: Path = DEFAULT_PYTHON
    account: str = DEFAULT_ACCOUNT
    partition: str = DEFAULT_PARTITION
    time_limit: str = DEFAULT_TIME
    cpus_per_task: int = DEFAULT_CPUS
    raw_root: Path | None = None
    results_path: Path | None = None
    opt_cmake_flags: str = ""
    reference_mode: bool = False
    claim_level: str = "L0"
    geant4_version: str = "v11.2.2"
    notes: str = ""


def render_sbatch(spec: RunnerSpec) -> str:
    """Return a bash- and ``sbatch``-valid script for ``spec``."""

    _validate_spec(spec)
    workload = resolve_workload(spec.workload)
    raw_root = spec.raw_root or (
        spec.repo_root / "benchmarks/raw" / _sanitize(spec.opt_id) / workload.workload_id
    )
    optimized_geant4_prefix = spec.optimized_geant4_prefix or spec.geant4_prefix
    results_path = spec.results_path or spec.repo_root / "benchmarks/results/results.parquet"
    vanilla_bin = _binary_path(spec.vanilla_build, workload.binary_rel)
    opt_bin = _binary_path(spec.optimized_build, workload.binary_rel)
    output_dir = raw_root / "%x-%j"
    job_name = _sanitize(f"g4gpu-{spec.opt_id}-{workload.workload_id}")[:48]
    seed_words = " ".join(str(seed) for seed in spec.seeds)

    lines = _render_common_header(
        spec,
        raw_root,
        results_path,
        vanilla_bin,
        opt_bin,
        output_dir,
        job_name,
        workload.workload_id,
        seed_words,
        optimized_geant4_prefix,
    )
    lines.extend(_render_reference_body() if spec.reference_mode else _render_result_body())
    return "\n".join(lines)


def _render_common_header(
    spec: RunnerSpec,
    raw_root: Path,
    results_path: Path,
    vanilla_bin: Path,
    opt_bin: Path,
    output_dir: Path,
    job_name: str,
    workload_id: str,
    seed_words: str,
    optimized_geant4_prefix: Path,
) -> list[str]:
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
        f"VANILLA_GEANT4_PREFIX={_quote(spec.geant4_prefix)}",
        f"OPTIMIZED_GEANT4_PREFIX={_quote(optimized_geant4_prefix)}",
        'GEANT4_PREFIX="${VANILLA_GEANT4_PREFIX}"',
        f"PYTHON_BIN={_quote(spec.python)}",
        f"VANILLA_BIN={_quote(vanilla_bin)}",
        f"OPTIMIZED_BIN={_quote(opt_bin)}",
        f"RAW_ROOT={_quote(raw_root)}",
        f"RESULTS_PATH={_quote(results_path)}",
        f"OPT_ID={_quote(spec.opt_id)}",
        f"OPT_BRANCH={_quote(spec.opt_branch)}",
        f"OPT_CMAKE_FLAGS={_quote(spec.opt_cmake_flags)}",
        f"CLAIM_LEVEL={_quote(spec.claim_level)}",
        f"GEANT4_VERSION={_quote(spec.geant4_version)}",
        f"NOTES={_quote(spec.notes)}",
        f"WORKLOAD_ID={_quote(workload_id)}",
        f"PHYSICS_LIST={_quote(spec.physics_list)}",
        f"HW_ID={_quote(spec.hw_id)}",
        f"N_EVENTS={int(spec.n_events)}",
        f"SEEDS=({seed_words})",
        "",
        'export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"',
        "",
        "geant4_config() {",
        '  local prefix="$1"',
        '  if [[ -f "${prefix}/lib/cmake/Geant4/Geant4Config.cmake" ]]; then',
        '    printf "%s\n" "${prefix}/lib/cmake/Geant4/Geant4Config.cmake"',
        '  elif [[ -f "${prefix}/Geant4Config.cmake" ]]; then',
        '    printf "%s\n" "${prefix}/Geant4Config.cmake"',
        "  else",
        '    return 1',
        "  fi",
        "}",
        "",
        "setup_geant4_env() {",
        '  local prefix="$1"',
        '  geant4_config "${prefix}" >/dev/null || { echo "missing Geant4Config.cmake under ${prefix}" >&2; exit 2; }',
        '  export GEANT4_PREFIX="${prefix}"',
        '  export CMAKE_PREFIX_PATH="${prefix}:${prefix}/lib/CLHEP-2.4.6.2:${CMAKE_PREFIX_PATH:-}"',
        '  export LD_LIBRARY_PATH="${prefix}/lib:${LD_LIBRARY_PATH:-}"',
        '  GEANT4_DATA="${prefix}/share/Geant4/data"',
        '  export G4NEUTRONHPDATA="${GEANT4_DATA}/NDL4.7.1"',
        '  export G4LEDATA="${GEANT4_DATA}/EMLOW8.5"',
        '  export G4LEVELGAMMADATA="${GEANT4_DATA}/PhotonEvaporation5.7"',
        '  export G4RADIOACTIVEDATA="${GEANT4_DATA}/RadioactiveDecay5.6"',
        '  export G4PARTICLEXSDATA="${GEANT4_DATA}/PARTICLEXS4.0"',
        '  export G4PIIDATA="${GEANT4_DATA}/PII1.3"',
        '  export G4REALSURFACEDATA="${GEANT4_DATA}/RealSurface2.2"',
        '  export G4SAIDXSDATA="${GEANT4_DATA}/SAIDDATA2.0"',
        '  export G4ABLADATA="${GEANT4_DATA}/ABLA3.3"',
        '  export G4INCLDATA="${GEANT4_DATA}/INCL1.2"',
        '  export G4ENSDFSTATEDATA="${GEANT4_DATA}/ENSDFSTATE2.3"',
        "}",
        "",
        'setup_geant4_env "${VANILLA_GEANT4_PREFIX}"',
        'if [[ "${OPTIMIZED_GEANT4_PREFIX}" != "${VANILLA_GEANT4_PREFIX}" ]]; then',
        '  geant4_config "${OPTIMIZED_GEANT4_PREFIX}" >/dev/null || { echo "missing optimized Geant4Config.cmake under ${OPTIMIZED_GEANT4_PREFIX}" >&2; exit 2; }',
        "fi",
        "",
        'cd "${REPO_ROOT}"',
        'mkdir -p "${RAW_ROOT}" "$(dirname "${RESULTS_PATH}")"',
        '[[ -x "${VANILLA_BIN}" ]] || { echo "missing executable vanilla binary: ${VANILLA_BIN}" >&2; exit 2; }',
        '"${PYTHON_BIN}" -m benchmarks.harness.run --collect --collect-check',
        "",
    ]
    if not spec.reference_mode:
        lines.append(
            '[[ -x "${OPTIMIZED_BIN}" ]] || { echo "missing executable optimized binary: ${OPTIMIZED_BIN}" >&2; exit 2; }'
        )
        lines.append("")
    return lines


def _render_result_body() -> list[str]:
    return [
        "run_one() {",
        '  local variant="$1"',
        '  local binary="$2"',
        '  local seed="$3"',
        '  local geant4_prefix="$4"',
        '  local out="${RAW_ROOT}/${variant}_seed_${seed}.parquet"',
        '  local log="${RAW_ROOT}/${variant}_seed_${seed}.txt"',
        '  echo "RUN variant=${variant} seed=${seed} binary=${binary}"',
        '  setup_geant4_env "${geant4_prefix}"',
        '  "${binary}" --events "${N_EVENTS}" --commit "${OPT_ID}_${variant}_seed_${seed}" \\',
        '    --physics-list "${PHYSICS_LIST}" --output "${out}" >"${log}" 2>&1',
        "}",
        "",
        'for seed in "${SEEDS[@]}"; do',
        '  export G4GPU_HARNESS_SEED="${seed}"',
        '  run_one vanilla "${VANILLA_BIN}" "${seed}" "${VANILLA_GEANT4_PREFIX}"',
        '  run_one optimized "${OPTIMIZED_BIN}" "${seed}" "${OPTIMIZED_GEANT4_PREFIX}"',
        "done",
        "",
        '"${PYTHON_BIN}" -m benchmarks.harness.run --collect \\',
        '  --opt-id "${OPT_ID}" \\',
        '  --opt-branch "${OPT_BRANCH}" \\',
        '  --opt-cmake-flags "${OPT_CMAKE_FLAGS}" \\',
        '  --workload "${WORKLOAD_ID}" \\',
        '  --physics-list "${PHYSICS_LIST}" \\',
        '  --hw "${HW_ID}" \\',
        '  --n-events "${N_EVENTS}" \\',
        '  --seeds "${SEEDS[@]}" \\',
        '  --slurm-job-id "${SLURM_JOB_ID}" \\',
        '  --raw-dir "${RAW_ROOT}" \\',
        '  --results "${RESULTS_PATH}" \\',
        '  --claim-level "${CLAIM_LEVEL}" \\',
        '  --geant4-version "${GEANT4_VERSION}" \\',
        '  --notes "${NOTES}"',
        "",
    ]


def _render_reference_body() -> list[str]:
    return [
        "run_reference() {",
        '  local seed="$1"',
        '  local out="${RAW_ROOT}/seed_${seed}.parquet"',
        '  local log="${RAW_ROOT}/seed_${seed}.txt"',
        '  echo "REFERENCE seed=${seed} binary=${VANILLA_BIN}"',
        '  setup_geant4_env "${VANILLA_GEANT4_PREFIX}"',
        '  "${VANILLA_BIN}" --events "${N_EVENTS}" --commit "reference_${WORKLOAD_ID}_${PHYSICS_LIST}_seed_${seed}" \\',
        '    --physics-list "${PHYSICS_LIST}" --output "${out}" >"${log}" 2>&1',
        "}",
        "",
        'for seed in "${SEEDS[@]}"; do',
        '  export G4GPU_HARNESS_SEED="${seed}"',
        '  run_reference "${seed}"',
        "done",
        "",
        '"${PYTHON_BIN}" -m benchmarks.harness.run --collect --generate-reference \\',
        '  --opt-id "${OPT_ID}" \\',
        '  --opt-branch "${OPT_BRANCH}" \\',
        '  --workload "${WORKLOAD_ID}" \\',
        '  --physics-list "${PHYSICS_LIST}" \\',
        '  --hw "${HW_ID}" \\',
        '  --n-events "${N_EVENTS}" \\',
        '  --seeds "${SEEDS[@]}" \\',
        '  --slurm-job-id "${SLURM_JOB_ID}" \\',
        '  --raw-dir "${RAW_ROOT}" \\',
        '  --repo-root "${REPO_ROOT}" \\',
        '  --results "${RESULTS_PATH}" \\',
        '  --geant4-version "${GEANT4_VERSION}"',
        "",
    ]

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
        optimized_geant4_prefix=args.optimized_geant4_prefix,
        python=args.python,
        account=args.account,
        partition=args.partition,
        time_limit=args.time,
        cpus_per_task=args.cpus_per_task,
        raw_root=args.raw_root,
        results_path=args.results_path,
        opt_cmake_flags=args.opt_cmake_flags,
        reference_mode=args.reference_mode,
        claim_level=args.claim_level,
        geant4_version=args.geant4_version,
        notes=args.notes,
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
    parser.add_argument("--optimized-geant4-prefix", type=Path)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--partition", default=DEFAULT_PARTITION)
    parser.add_argument("--time", default=DEFAULT_TIME)
    parser.add_argument("--cpus-per-task", type=int, default=DEFAULT_CPUS)
    parser.add_argument("--raw-root", type=Path)
    parser.add_argument("--results-path", type=Path)
    parser.add_argument("--opt-cmake-flags", default="")
    parser.add_argument("--reference-mode", action="store_true")
    parser.add_argument("--claim-level", default="L0")
    parser.add_argument("--geant4-version", default="v11.2.2")
    parser.add_argument("--notes", default="")
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
    if spec.opt_id == "BD-geant4-001" and not spec.reference_mode:
        if spec.optimized_geant4_prefix is None:
            raise RunnerError("BD-geant4-001 requires an explicit optimized_geant4_prefix")
        if Path(spec.optimized_geant4_prefix) == Path(spec.geant4_prefix):
            raise RunnerError("BD-geant4-001 optimized_geant4_prefix must differ from vanilla geant4_prefix")


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
