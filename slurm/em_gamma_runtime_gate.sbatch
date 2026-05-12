#!/usr/bin/env bash
#SBATCH --job-name=g4gpu-em-rtgate
#SBATCH --account=lu2026-2-51
#SBATCH --partition=gpua40i
#SBATCH --gres=gpu:1
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=slurm/em-gamma-runtime-%j.out
#SBATCH --error=slurm/em-gamma-runtime-%j.err

set -euo pipefail

if [[ "${EM_GAMMA_RUNTIME_APPROVED:-NO}" != "YES" ]]; then
  echo "ERROR: set EM_GAMMA_RUNTIME_APPROVED=YES to run the GPU runtime gate" >&2
  exit 2
fi

resolve_existing_dir() {
  local path="$1"
  (cd "${path}" >/dev/null && pwd -P)
}

resolve_dir() {
  local path="$1"
  mkdir -p "${path}"
  (cd "${path}" >/dev/null && pwd -P)
}

default_repo_dir() {
  local candidate="${SLURM_SUBMIT_DIR:-$(pwd)}"
  if [[ -f "${candidate}/scripts/verify_em_gamma_runtime_gate.py" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi
  echo "ERROR: submit from the geant4-gpu checkout or set G4GPU_EM_REPO_DIR" >&2
  return 2
}

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

REPO_DIR="$(resolve_existing_dir "${G4GPU_EM_REPO_DIR:-$(default_repo_dir)}")"
BUILD_DIR="$(resolve_dir "${G4GPU_EM_BUILD_DIR:-${REPO_DIR}/build}")"
LOG_DIR="$(resolve_dir "${G4GPU_EM_LOG_DIR:-${REPO_DIR}/slurm}")"
PYTHON_BIN="${G4GPU_EM_PYTHON:-python3}"
NVCC_BIN="${G4GPU_EM_NVCC:-/sw/easybuild_milan/software/CUDA/12.8.0/bin/nvcc}"
GEANT4_DIR="${G4GPU_EM_GEANT4_DIR:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/lib/cmake/Geant4}"
JOB_ID="${SLURM_JOB_ID:-manual}"

cd "${REPO_DIR}"
load_modules

echo "EM gamma runtime repo: ${REPO_DIR}"
echo "EM gamma runtime build: ${BUILD_DIR}"
echo "EM gamma runtime log dir: ${LOG_DIR}"
echo "EM gamma runtime host: $(hostname)"
echo "EM gamma runtime job: ${JOB_ID}"
nvidia-smi || true

cmake -S "${REPO_DIR}" -B "${BUILD_DIR}" \
  -DG4GPU_WITH_EM=ON \
  -DG4GPU_WITH_OPTICAL=OFF \
  -DG4GPU_WITH_RTX=OFF \
  -DCMAKE_CUDA_COMPILER="${NVCC_BIN}" \
  -DGeant4_DIR="${GEANT4_DIR}"
cmake --build "${BUILD_DIR}" --target G4GPU test_em_klein_nishina -j "${SLURM_CPUS_PER_TASK:-2}"

ctest --test-dir "${BUILD_DIR}" --output-on-failure -V -R '^g4gpu_em_klein_nishina$' | \
  tee "${LOG_DIR}/em_gamma_runtime_ctest_${JOB_ID}.txt"
"${PYTHON_BIN}" scripts/verify_em_gamma_runtime_gate.py --timeout 180 | \
  tee "${LOG_DIR}/em_gamma_runtime_gate_${JOB_ID}.txt"

echo "EM_GAMMA_RUNTIME_SLURM_OK job=${JOB_ID}"
