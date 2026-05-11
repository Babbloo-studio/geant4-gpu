#!/usr/bin/env bash
set -euo pipefail

EVENTS=(
  gamma_100mev
  muon_10gev
  nbar_carbon
  cosmic_shower
  optical_scintillator
  beam_neutron
)

REMOTE_HOST="${G4GPU_LUNARC_HOST:-lunarc}"
REMOTE_REPO="${G4GPU_LUNARC_REPO:-/projects/hep/fs10/shared/nnbar/billy/geant4-gpu}"
LOCAL_REPO="${G4GPU_LOCAL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ACCOUNT="${G4GPU_SLURM_ACCOUNT:-lu2026-2-51}"
PARTITION="${G4GPU_SLURM_PARTITION:-lu48}"
EVENT_COUNT="${G4GPU_BENCHMARK_EVENTS:-1000}"
PYTHON_BIN="${G4GPU_BENCHMARK_PYTHON:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python}"
GEANT4_DIR="${G4GPU_GEANT4_DIR:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/lib/cmake/Geant4}"

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

ensure_lunarc_socket() {
  ssh -O check "$REMOTE_HOST" 2>/dev/null && echo "Connected" || /Users/billy/lunarc-init.sh
}

on_lunarc() {
  cd "$REMOTE_REPO"
  load_modules
  cmake -B build \
    -DCMAKE_CUDA_COMPILER=nvcc \
    -DGeant4_DIR="$GEANT4_DIR" \
    -DG4GPU_WITH_OPTICAL=OFF \
    -DG4GPU_WITH_RTX=OFF \
    -DG4GPU_BENCHMARK_PYTHON="$PYTHON_BIN" \
    .
  cmake --build build -j8

  local commit
  commit="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
  mkdir -p benchmarks/results
  local job_script="benchmarks/results/phase5a_${commit}.slurm"
  cat >"$job_script" <<EOF
#!/usr/bin/env bash
#SBATCH --job-name=g4gpu-phase5a
#SBATCH --account=${ACCOUNT}
#SBATCH --partition=${PARTITION}
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --output=${REMOTE_REPO}/benchmarks/results/phase5a_${commit}_%j.out

set -euo pipefail
cd "${REMOTE_REPO}"
$(declare -f load_modules)
load_modules
export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"
events=(${EVENTS[*]})
for event in "\${events[@]}"; do
  "./build/benchmarks/benchmark_\${event}" \\
    --events "${EVENT_COUNT}" \\
    --commit "${commit}" \\
    --output "benchmarks/results/\${event}_${commit}.parquet"
done
EOF
  sbatch --wait "$job_script"
  ls -lh benchmarks/results/*_"${commit}".parquet
}

from_local() {
  ensure_lunarc_socket
  rsync -av --exclude build/ --exclude '._*' "$LOCAL_REPO"/ "$REMOTE_HOST":"$REMOTE_REPO"/
  ensure_lunarc_socket
  ssh "$REMOTE_HOST" "cd '$REMOTE_REPO' && bash benchmarks/run_baseline.sh --on-lunarc"
  ensure_lunarc_socket
  mkdir -p "$LOCAL_REPO/benchmarks/results"
  rsync -av "$REMOTE_HOST":"$REMOTE_REPO/benchmarks/results/" "$LOCAL_REPO/benchmarks/results/"
}

case "${1:-}" in
  --on-lunarc)
    on_lunarc
    ;;
  --help|-h)
    echo "Usage: benchmarks/run_baseline.sh [--on-lunarc]"
    echo "Run without arguments locally; it rsyncs to LUNARC, runs via SLURM, and syncs results back."
    ;;
  "")
    from_local
    ;;
  *)
    echo "unknown argument: $1" >&2
    exit 2
    ;;
esac
