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
PARTITION="${G4GPU_CPU_PROFILE_PARTITION:-lu48}"
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

write_perf_text() {
  local perf_data="$1"
  local output="$2"
  {
    echo "# G4GPU CPU perf profile"
    echo "# perf_data=${perf_data}"
    echo
    echo "## perf report --stdio (top symbols)"
    perf report --stdio --no-children --sort=symbol -i "$perf_data" 2>&1 || true
    echo
    echo "## perf annotate --stdio (top 20 symbols)"
    mapfile -t symbols < <(
      perf report --stdio --no-children --sort=symbol -i "$perf_data" 2>/dev/null |
        awk '/^[[:space:]]*[0-9]+[.][0-9]+%/ {
          line = $0
          sub(/^[[:space:]]*[0-9.]+%[[:space:]]+/, "", line)
          sub(/[[:space:]]+-[[:space:]]+-[[:space:]]*$/, "", line)
          sub(/^[[:space:]]*\[[^]]+\][[:space:]]+/, "", line)
          sub(/[[:space:]]+$/, "", line)
          print line
        }' |
        awk 'NF && $0 !~ /^0x/ && $0 !~ /^0xffffffff/ && !seen[$0]++ {print}' |
        head -20
    )
    if ((${#symbols[@]} == 0)); then
      echo "OPEN: no symbols parsed from perf report; raw report above is the evidence."
      return 0
    fi
    for symbol in "${symbols[@]}"; do
      echo
      echo "### ${symbol}"
      perf annotate --stdio --symbol "$symbol" -i "$perf_data" 2>&1 ||
        echo "OPEN: perf annotate failed for symbol ${symbol}"
    done
  } >"$output"
}

profile_event_cpu() {
  local event="$1"
  local commit="$2"
  mkdir -p benchmarks/profiles benchmarks/results
  local perf_data="benchmarks/profiles/${event}_cpu_${commit}.data"
  local output="benchmarks/profiles/${event}_cpu_${commit}.txt"
  local parquet="benchmarks/results/${event}_${commit}_profile.parquet"

  perf record -g -o "$perf_data" -- \
    "./build/benchmarks/benchmark_${event}" \
      --events "$EVENT_COUNT" \
      --commit "${commit}_profile" \
      --csv-only \
      --output "$parquet"
  write_perf_text "$perf_data" "$output"
  rm -f "$perf_data"
  echo "wrote ${output}"
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
  local job_script="benchmarks/profiles/phase5b_cpu_${commit}.slurm"
  cat >"$job_script" <<EOF
#!/usr/bin/env bash
#SBATCH --job-name=g4gpu-prof-cpu
#SBATCH --account=${ACCOUNT}
#SBATCH --partition=${PARTITION}
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --output=${REMOTE_REPO}/benchmarks/profiles/phase5b_cpu_${commit}_%j.out

set -euo pipefail
cd "${REMOTE_REPO}"
EVENT_COUNT="${EVENT_COUNT}"
$(declare -f load_modules)
$(declare -f write_perf_text)
$(declare -f profile_event_cpu)
load_modules
export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"
events=(${EVENTS[*]})
for event in "\${events[@]}"; do
  profile_event_cpu "\${event}" "${commit}"
done
EOF
  sbatch --wait "$job_script"
  ls -lh benchmarks/profiles/*_cpu_"${commit}".txt
}

from_local() {
  ensure_lunarc_socket
  rsync -av --exclude build/ --exclude '._*' "$LOCAL_REPO"/ "$REMOTE_HOST":"$REMOTE_REPO"/
  ensure_lunarc_socket
  ssh "$REMOTE_HOST" "cd '$REMOTE_REPO' && bash benchmarks/profile_cpu.sh --on-lunarc"
  ensure_lunarc_socket
  mkdir -p "$LOCAL_REPO/benchmarks/profiles"
  rsync -av "$REMOTE_HOST":"$REMOTE_REPO/benchmarks/profiles/" "$LOCAL_REPO/benchmarks/profiles/"
}

case "${1:-}" in
  --on-lunarc)
    on_lunarc
    ;;
  --help|-h)
    echo "Usage: benchmarks/profile_cpu.sh [--on-lunarc]"
    echo "Runs perf record/report/annotate for each phase-5 benchmark driver."
    ;;
  "")
    from_local
    ;;
  *)
    echo "unknown argument: $1" >&2
    exit 2
    ;;
esac
