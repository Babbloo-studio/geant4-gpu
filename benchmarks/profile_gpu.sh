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
PARTITION="${G4GPU_GPU_PROFILE_PARTITION:-gpua40}"
GRES="${G4GPU_GPU_PROFILE_GRES:-gpu:1}"
EVENT_COUNT="${G4GPU_PROFILE_EVENTS:-1000}"
PYTHON_BIN="${G4GPU_BENCHMARK_PYTHON:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python}"
GEANT4_DIR="${G4GPU_GEANT4_DIR:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/lib/cmake/Geant4}"

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

ensure_lunarc_socket() {
  ssh -O check "$REMOTE_HOST" 2>/dev/null && echo "Connected" || /Users/billy/lunarc-init.sh
}

profile_event_gpu() {
  local event="$1"
  local commit="$2"
  mkdir -p benchmarks/profiles benchmarks/results
  local report="benchmarks/profiles/${event}_gpu_${commit}.ncu-rep"
  local text="benchmarks/profiles/${event}_gpu_${commit}.txt"
  local parquet="benchmarks/results/${event}_${commit}_ncu.parquet"

  {
    echo "# G4GPU Nsight Compute profile"
    echo "# event=${event}"
    echo "# report=${report}"
    echo
  } >"$text"

  set +e
  ncu --set full --target-processes all \
    --force-overwrite --export "$report" --log-file "$text.tmp" \
    "./build/benchmarks/benchmark_${event}" \
      --events "$EVENT_COUNT" \
      --commit "${commit}_ncu" \
      --csv-only \
      --output "$parquet"
  local ncu_rc=$?
  set -e
  cat "$text.tmp" >>"$text"
  rm -f "$text.tmp"
  if ((ncu_rc != 0)); then
    echo "OPEN: ncu exited with status ${ncu_rc}; see log above." >>"$text"
    if [[ "${G4GPU_NCU_ALLOW_EMPTY:-1}" != "1" ]]; then
      return "$ncu_rc"
    fi
  fi
  echo "wrote ${text}"
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
  mkdir -p benchmarks/profiles
  local job_script="benchmarks/profiles/phase5b_gpu_${commit}.slurm"
  cat >"$job_script" <<EOF
#!/usr/bin/env bash
#SBATCH --job-name=g4gpu-prof-gpu
#SBATCH --account=${ACCOUNT}
#SBATCH --partition=${PARTITION}
#SBATCH --gres=${GRES}
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --output=${REMOTE_REPO}/benchmarks/profiles/phase5b_gpu_${commit}_%j.out

set -euo pipefail
cd "${REMOTE_REPO}"
EVENT_COUNT="${EVENT_COUNT}"
$(declare -f load_modules)
$(declare -f profile_event_gpu)
load_modules
export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"
events=(${EVENTS[*]})
for event in "\${events[@]}"; do
  profile_event_gpu "\${event}" "${commit}"
done
EOF
  sbatch --wait "$job_script"
  ls -lh benchmarks/profiles/*_gpu_"${commit}".txt
}

from_local() {
  ensure_lunarc_socket
  rsync -av --exclude build/ --exclude '._*' "$LOCAL_REPO"/ "$REMOTE_HOST":"$REMOTE_REPO"/
  ensure_lunarc_socket
  ssh "$REMOTE_HOST" "cd '$REMOTE_REPO' && bash benchmarks/profile_gpu.sh --on-lunarc"
  ensure_lunarc_socket
  mkdir -p "$LOCAL_REPO/benchmarks/profiles"
  rsync -av "$REMOTE_HOST":"$REMOTE_REPO/benchmarks/profiles/" "$LOCAL_REPO/benchmarks/profiles/"
}

case "${1:-}" in
  --on-lunarc)
    on_lunarc
    ;;
  --help|-h)
    echo "Usage: benchmarks/profile_gpu.sh [--on-lunarc]"
    echo "Runs Nsight Compute for each phase-5 benchmark driver."
    ;;
  "")
    from_local
    ;;
  *)
    echo "unknown argument: $1" >&2
    exit 2
    ;;
esac
