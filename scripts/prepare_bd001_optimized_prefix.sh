#!/usr/bin/env bash
# Guarded BD-geant4-001 optimized Geant4 install-prefix builder.
#
# This wrapper is intentionally fail-closed by default.  It only configures,
# builds, and installs the default-off Moller/Bhabha inverse-sampler Geant4
# source tree when a later planner-approved compute job sets the approval
# environment variable.  It does not run benchmark events or write harness
# result rows.

set -euo pipefail

SOURCE_REPO="${BD001_GEANT4_SOURCE_REPO:-/projects/hep/fs10/shared/nnbar/billy/geant4-fork}"
BUILD_DIR="${BD001_GEANT4_BUILD_DIR:-/projects/hep/fs10/shared/nnbar/billy/geant4-fork/build-bd001-optimized-prefix}"
PREFIX="${BD001_OPTIMIZED_GEANT4_PREFIX:-/projects/hep/fs10/shared/nnbar/billy/pending/bd001-optimized-geant4}"
SOURCE_COMMIT="4ac150b"
HANDOFF_HEAD="782d84c"
CMAKE_FLAG="-DG4EM_MOLLER_BHABHA_INVERSE_SAMPLER=ON"
JOBS="${BD001_PREFIX_BUILD_JOBS:-8}"

if [[ "${BD001_OPTIMIZED_PREFIX_BUILD_APPROVED:-}" != "YES" ]]; then
  cat <<MSG
BD001_OPTIMIZED_PREFIX_PREFLIGHT_BLOCKED
Set BD001_OPTIMIZED_PREFIX_BUILD_APPROVED=YES only in a fresh planner-approved
compute job. Intended command:
  BD001_OPTIMIZED_PREFIX_BUILD_APPROVED=YES $0
source_repo=${SOURCE_REPO}
source_commit=${SOURCE_COMMIT}
handoff_head=${HANDOFF_HEAD}
prefix=${PREFIX}
cmake_flag=${CMAKE_FLAG}
MSG
  exit 2
fi

if [[ -z "${SLURM_JOB_ID:-}" && "${BD001_ALLOW_NON_SLURM_PREFIX_BUILD:-}" != "YES" ]]; then
  echo "BD001_OPTIMIZED_PREFIX_COMPUTE_GUARD: run inside an approved compute job" >&2
  exit 2
fi

if [[ ! -d "${SOURCE_REPO}/.git" ]]; then
  echo "BD001_OPTIMIZED_PREFIX_SOURCE_MISSING: ${SOURCE_REPO}" >&2
  exit 2
fi

actual_head="$(git -C "${SOURCE_REPO}" rev-parse --short=7 HEAD)"
if [[ "${actual_head}" != "${HANDOFF_HEAD}" ]]; then
  echo "BD001_OPTIMIZED_PREFIX_WRONG_HEAD: expected ${HANDOFF_HEAD}, got ${actual_head}" >&2
  exit 2
fi
git -C "${SOURCE_REPO}" merge-base --is-ancestor "${SOURCE_COMMIT}" HEAD

if [[ -e "${PREFIX}" && -n "$(find "${PREFIX}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "BD001_OPTIMIZED_PREFIX_NONEMPTY: refusing to overwrite ${PREFIX}" >&2
  exit 2
fi

cmake -S "${SOURCE_REPO}" -B "${BUILD_DIR}" \
  -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
  -DGEANT4_BUILD_MULTITHREADED=ON \
  -DGEANT4_BUILD_EXAMPLES=OFF \
  -DGEANT4_INSTALL_DATA=OFF \
  "${CMAKE_FLAG}"
cmake --build "${BUILD_DIR}" --target install -j "${JOBS}"
test -f "${PREFIX}/lib/cmake/Geant4/Geant4Config.cmake"
echo "BD001_OPTIMIZED_PREFIX_BUILD_OK prefix=${PREFIX}"
