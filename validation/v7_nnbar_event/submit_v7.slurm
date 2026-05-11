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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${G4GPU_V7_PYTHON:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python}"

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

cd "${REPO_DIR}"
load_modules
mkdir -p output validation/v7_nnbar_event

"${PYTHON_BIN}" validation/v7_nnbar_event/run_v7.py \
  --candidate output/v7_g4gpu.root \
  --reference output/v7_geant4_ref.root \
  --output output/v7_summary.json
