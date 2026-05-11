#!/usr/bin/env bash
# Resume checklist for g4gpu-phase5 after the external blockers clear.
# This script intentionally does not start Phase 5d optimization work.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GPU_JOB_ID="${G4GPU_PHASE5_GPU_CTEST_JOB:-3041846}"
REMOTE="${G4GPU_PHASE5_REMOTE:-origin}"
BRANCH="${G4GPU_PHASE5_BRANCH:-lane/g4gpu-phase5}"
PUBLICATION_DIR="${G4GPU_PHASE5_PUBLICATION_DIR:-/projects/hep/fs10/shared/nnbar/billy/g4gpu-phase5-publication}"
if [[ -n "${G4GPU_PHASE5_SHA_FILE:-}" ]]; then
  SHA_FILE="$G4GPU_PHASE5_SHA_FILE"
else
  HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || true)"
  if [[ -n "$HEAD_SHORT" && -f "${PUBLICATION_DIR}/SHA256SUMS-${HEAD_SHORT}" ]]; then
    SHA_FILE="${PUBLICATION_DIR}/SHA256SUMS-${HEAD_SHORT}"
  else
    SHA_FILE="$(ls -1t "${PUBLICATION_DIR}"/SHA256SUMS-* 2>/dev/null | head -1 || true)"
  fi
fi

section() {
  printf '\n== %s ==\n' "$*"
}

section "branch"
git status --short --branch
git log --oneline "${REMOTE}/${BRANCH}..HEAD" || true

section "GPU CTest job ${GPU_JOB_ID}"
if command -v squeue >/dev/null 2>&1; then
  squeue --start -j "$GPU_JOB_ID" 2>/dev/null || true
  squeue -j "$GPU_JOB_ID" -o '%.18i %.9T %.10M %.20R' || true
fi
if command -v sacct >/dev/null 2>&1; then
  sacct -j "$GPU_JOB_ID" --format=JobID,State,Elapsed,ExitCode -X 2>/dev/null || true
fi
if [[ -f "build/g4gpu_phase5_ctest_current_${GPU_JOB_ID}.out" ]]; then
  section "GPU CTest output tail"
  tail -120 "build/g4gpu_phase5_ctest_current_${GPU_JOB_ID}.out"
fi

section "publication fallback checksums"
if [[ -f "$SHA_FILE" ]]; then
  sha256sum -c "$SHA_FILE"
else
  echo "missing fallback checksum file: $SHA_FILE" >&2
fi

section "GitHub auth and push readiness"
if command -v gh >/dev/null 2>&1; then
  gh auth status 2>&1 || true
else
  echo "gh not found"
fi
if git ls-remote --heads "$REMOTE" "$BRANCH" >/tmp/g4gpu_phase5_remote_ref 2>/tmp/g4gpu_phase5_remote_err; then
  cat /tmp/g4gpu_phase5_remote_ref
else
  cat /tmp/g4gpu_phase5_remote_err >&2 || true
fi

cat <<'MSG'

Next steps after blockers clear:
1. Require GPU CTest job 3041846 to complete successfully (or rerun an equivalent GPU CTest).
2. Authenticate GitHub, then run: git push origin lane/g4gpu-phase5
3. Ask planner to review the 5a--5c measurement framework before any 5d L0 work.
MSG
