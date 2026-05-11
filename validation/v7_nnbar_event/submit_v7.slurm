#!/usr/bin/env bash
#SBATCH --job-name=g4gpu-v7-shake
#SBATCH --account=lu2026-2-51
#SBATCH --partition=gpua40
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=validation/v7_nnbar_event/v7_shakedown_%j.out
#SBATCH --error=validation/v7_nnbar_event/v7_shakedown_%j.err

set -euo pipefail

PYTHON_BIN="${G4GPU_V7_PYTHON:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python}"

resolve_dir() {
  local path="$1"
  mkdir -p "${path}"
  (cd "${path}" >/dev/null && pwd -P)
}

resolve_existing_dir() {
  local path="$1"
  (cd "${path}" >/dev/null && pwd -P)
}

default_repo_dir() {
  # Under Slurm, BASH_SOURCE points at a spooled copy of this script, not the
  # checkout. Prefer the submit directory and require it to contain the runner.
  local candidate="${SLURM_SUBMIT_DIR:-$(pwd)}"
  if [[ -f "${candidate}/validation/v7_nnbar_event/run_v7.py" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi
  printf 'ERROR: cannot locate geant4-gpu checkout; set G4GPU_V7_REPO_DIR or submit from repo root\n' >&2
  return 2
}

if [[ -n "${G4GPU_V7_REPO_DIR:-}" ]]; then
  REPO_CANDIDATE="${G4GPU_V7_REPO_DIR}"
else
  REPO_CANDIDATE="$(default_repo_dir)"
fi
REPO_DIR="$(resolve_existing_dir "${REPO_CANDIDATE}")"
RUN_ROOT="$(resolve_dir "${G4GPU_V7_RUN_ROOT:-${SLURM_SUBMIT_DIR:-${REPO_DIR}}}")"
CANDIDATE_PATH="${G4GPU_V7_CANDIDATE:-${RUN_ROOT}/output/v7_g4gpu.root}"
REFERENCE_PATH="${G4GPU_V7_REFERENCE:-${RUN_ROOT}/output/v7_geant4_ref.root}"
SUMMARY_PATH="${G4GPU_V7_SUMMARY:-${RUN_ROOT}/output/v7_summary.json}"

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

cd "${REPO_DIR}"
load_modules
mkdir -p "${RUN_ROOT}/output" "${RUN_ROOT}/validation/v7_nnbar_event"

echo "G4GPU V7 repo dir: ${REPO_DIR}"
echo "G4GPU V7 run root: ${RUN_ROOT}"
echo "G4GPU V7 candidate input: ${CANDIDATE_PATH}"
echo "G4GPU V7 reference input: ${REFERENCE_PATH}"
echo "G4GPU V7 summary output: ${SUMMARY_PATH}"

"${PYTHON_BIN}" validation/v7_nnbar_event/run_v7.py \
  --run-root "${RUN_ROOT}" \
  --candidate "${CANDIDATE_PATH}" \
  --reference "${REFERENCE_PATH}" \
  --output "${SUMMARY_PATH}"
