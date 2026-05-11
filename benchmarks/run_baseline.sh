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

CANONICAL_NAMES=(
  basic_b1
  testem0
  hadr01
  hadr02
  opnovice2
  par01
)
CANONICAL_SOURCES=(
  examples/basic/B1
  examples/extended/electromagnetic/TestEm0
  examples/extended/hadronic/Hadr01
  examples/extended/hadronic/Hadr02
  examples/extended/optical/OpNovice2
  examples/extended/parameterisations/Par01
)
CANONICAL_EXECUTABLES=(
  exampleB1
  TestEm0
  Hadr01
  Hadr02
  OpNovice2
  examplePar01
)
CANONICAL_MACROS=(
  run1.mac
  TestEm0.in
  hadr01.in
  hadr02.in
  electron.mac
  examplePar01.in
)

REMOTE_HOST="${G4GPU_LUNARC_HOST:-lunarc}"
REMOTE_REPO="${G4GPU_LUNARC_REPO:-/projects/hep/fs10/shared/nnbar/billy/geant4-gpu}"
LOCAL_REPO="${G4GPU_LOCAL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ACCOUNT="${G4GPU_SLURM_ACCOUNT:-lu2026-2-51}"
PARTITION="${G4GPU_SLURM_PARTITION:-lu48}"
EVENT_COUNT="${G4GPU_BENCHMARK_EVENTS:-1000}"
PYTHON_BIN="${G4GPU_BENCHMARK_PYTHON:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python}"
GEANT4_DIR="${G4GPU_GEANT4_DIR:-/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/lib/cmake/Geant4}"
GEANT4_SOURCE="${G4GPU_GEANT4_SOURCE:-/projects/hep/fs10/shared/nnbar/billy/geant4-fork}"
CANONICAL_BUILD_ROOT="${G4GPU_CANONICAL_BUILD_ROOT:-${REMOTE_REPO}/build/canonical}"

load_modules() {
  module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || \
    module load GCC/13.2.0 CUDA/12.8.0
}

source_geant4_env() {
  local geant4_prefix
  geant4_prefix="$(cd "$(dirname "${GEANT4_DIR}")/../.." && pwd)"
  export GEANT4_PREFIX="$geant4_prefix"
  export CMAKE_PREFIX_PATH="${geant4_prefix}:${geant4_prefix}/lib/CLHEP-2.4.6.2:${CMAKE_PREFIX_PATH:-}"
  export LD_LIBRARY_PATH="${geant4_prefix}/lib:${LD_LIBRARY_PATH:-}"
  local geant4_data="${geant4_prefix}/share/Geant4/data"
  export G4NEUTRONHPDATA="${geant4_data}/NDL4.7.1"
  export G4LEDATA="${geant4_data}/EMLOW8.5"
  export G4LEVELGAMMADATA="${geant4_data}/PhotonEvaporation5.7"
  export G4RADIOACTIVEDATA="${geant4_data}/RadioactiveDecay5.6"
  export G4PARTICLEXSDATA="${geant4_data}/PARTICLEXS4.0"
  export G4PIIDATA="${geant4_data}/PII1.3"
  export G4REALSURFACEDATA="${geant4_data}/RealSurface2.2"
  export G4SAIDXSDATA="${geant4_data}/SAIDDATA2.0"
  export G4ABLADATA="${geant4_data}/ABLA3.3"
  export G4INCLDATA="${geant4_data}/INCL1.2"
  export G4ENSDFSTATEDATA="${geant4_data}/ENSDFSTATE2.3"
}

ensure_lunarc_socket() {
  ssh -O check "$REMOTE_HOST" 2>/dev/null && echo "Connected" || /Users/billy/lunarc-init.sh
}

run_canonical_examples() {
  local commit="$1"
  mkdir -p benchmarks/results/canonical "$CANONICAL_BUILD_ROOT"
  local summary="benchmarks/results/canonical_examples_${commit}.csv"
  echo "name,source_path,executable,macro,wall_time_ns,log_path" >"$summary"

  for i in "${!CANONICAL_NAMES[@]}"; do
    local name="${CANONICAL_NAMES[$i]}"
    local source_rel="${CANONICAL_SOURCES[$i]}"
    local executable="${CANONICAL_EXECUTABLES[$i]}"
    local macro="${CANONICAL_MACROS[$i]}"
    local source_dir="${GEANT4_SOURCE}/${source_rel}"
    local build_dir="${CANONICAL_BUILD_ROOT}/${name}"
    local log_path="${REMOTE_REPO}/benchmarks/results/canonical/${name}_${commit}.log"

    if [[ ! -d "$source_dir" ]]; then
      echo "missing canonical Geant4 example: $source_dir" >&2
      return 1
    fi

    cmake -S "$source_dir" -B "$build_dir" \
      -DGeant4_DIR="$GEANT4_DIR" \
      -DCMAKE_PREFIX_PATH="${GEANT4_PREFIX};${GEANT4_PREFIX}/lib/CLHEP-2.4.6.2" \
      -DZLIB_ROOT="$GEANT4_PREFIX" \
      -DZLIB_LIBRARY="$GEANT4_PREFIX/lib/libz.so" \
      -DZLIB_INCLUDE_DIR="$GEANT4_PREFIX/include" \
      -DWITH_GEANT4_UIVIS=OFF
    cmake --build "$build_dir" -j2

    local start_ns
    local stop_ns
    start_ns="$(date +%s%N)"
    (cd "$build_dir" && "./${executable}" "$macro") >"$log_path" 2>&1
    stop_ns="$(date +%s%N)"
    echo "${name},${source_rel},${executable},${macro},$((stop_ns - start_ns)),${log_path}" \
      >>"$summary"
  done
}

on_lunarc() {
  cd "$REMOTE_REPO"
  load_modules
  source_geant4_env
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
$(declare -p CANONICAL_NAMES CANONICAL_SOURCES CANONICAL_EXECUTABLES CANONICAL_MACROS)
GEANT4_DIR="${GEANT4_DIR}"
GEANT4_SOURCE="${GEANT4_SOURCE}"
REMOTE_REPO="${REMOTE_REPO}"
CANONICAL_BUILD_ROOT="${CANONICAL_BUILD_ROOT}"
$(declare -f load_modules)
$(declare -f source_geant4_env)
$(declare -f run_canonical_examples)
load_modules
source_geant4_env
export G4GPU_BENCHMARK_PYTHON="${PYTHON_BIN}"
events=(${EVENTS[*]})
for event in "\${events[@]}"; do
  "./build/benchmarks/benchmark_\${event}" \\
    --events "${EVENT_COUNT}" \\
    --commit "${commit}" \\
    --output "benchmarks/results/\${event}_${commit}.parquet"
done
run_canonical_examples "${commit}"
EOF
  sbatch --wait "$job_script"
  ls -lh benchmarks/results/*_"${commit}".parquet
  ls -lh benchmarks/results/canonical/*_"${commit}".log \
    "benchmarks/results/canonical_examples_${commit}.csv"
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
