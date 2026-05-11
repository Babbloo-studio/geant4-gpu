#!/usr/bin/env bash
# Resume checklist for g4gpu-phase5 after the external blockers clear.
# This script intentionally does not start Phase 5d optimization work.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GPU_JOB_ID="${G4GPU_PHASE5_GPU_CTEST_JOB:-3041846}"
REMOTE="${G4GPU_PHASE5_REMOTE:-origin}"
FORK_REMOTE="${G4GPU_PHASE5_FORK_REMOTE:-fork}"
BRANCH="${G4GPU_PHASE5_BRANCH:-lane/g4gpu-phase5}"
PUBLICATION_DIR="${G4GPU_PHASE5_PUBLICATION_DIR:-/projects/hep/fs10/shared/nnbar/billy/g4gpu-phase5-publication}"
LOCAL_MIRROR="${G4GPU_PHASE5_LOCAL_MIRROR:-${PUBLICATION_DIR}/geant4-gpu-phase5.git}"
CURRENT_HEAD="$(git rev-parse HEAD 2>/dev/null || true)"
HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || true)"
if [[ -n "${G4GPU_PHASE5_SHA_FILE:-}" ]]; then
  SHA_FILE="$G4GPU_PHASE5_SHA_FILE"
else
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

GPU_CTEST_READY=unknown
GITHUB_AUTH_READY=unknown
GITHUB_READY=unknown
GITHUB_ORIGIN_PUSH_READY=unknown
GITHUB_FORK_PUSH_READY=unknown
GITHUB_PUBLICATION_REMOTE=none
CHECKSUM_READY=unknown
MIRROR_READY=unknown

section "GPU CTest job ${GPU_JOB_ID}"
if command -v squeue >/dev/null 2>&1; then
  squeue --start -j "$GPU_JOB_ID" 2>/dev/null || true
  squeue -j "$GPU_JOB_ID" -o '%.18i %.9T %.10M %.20R' || true
fi
if command -v sacct >/dev/null 2>&1; then
  sacct -j "$GPU_JOB_ID" --format=JobID,State,Elapsed,ExitCode -X 2>/dev/null || true
  sacct_line="$(sacct -P -n -j "$GPU_JOB_ID" --format=State,ExitCode -X 2>/dev/null | head -1 || true)"
  if [[ "$sacct_line" == COMPLETED\|0:0 ]]; then
    GPU_CTEST_READY=yes
  elif [[ -n "$sacct_line" ]]; then
    GPU_CTEST_READY=no
  fi
fi
if [[ -f "build/g4gpu_phase5_ctest_current_${GPU_JOB_ID}.out" ]]; then
  section "GPU CTest output tail"
  tail -120 "build/g4gpu_phase5_ctest_current_${GPU_JOB_ID}.out"
fi

section "publication fallback checksums"
if [[ -f "$SHA_FILE" ]]; then
  SHA_DIR="$(cd "$(dirname "$SHA_FILE")" && pwd)"
  SHA_BASE="$(basename "$SHA_FILE")"
  if (cd "$SHA_DIR" && sha256sum -c "$SHA_BASE"); then
    CHECKSUM_READY=yes
  else
    CHECKSUM_READY=no
  fi
else
  echo "missing fallback checksum file: $SHA_FILE" >&2
  CHECKSUM_READY=no
fi

section "local mirror fallback"
if [[ -d "$LOCAL_MIRROR" ]]; then
  mirror_ref="refs/heads/${BRANCH}"
  mirror_head="$(git --git-dir="$LOCAL_MIRROR" rev-parse "$mirror_ref" 2>/dev/null || true)"
  printf 'mirror=%s\n' "$LOCAL_MIRROR"
  printf 'mirror_ref=%s\n' "$mirror_ref"
  printf 'mirror_head=%s\n' "$mirror_head"
  printf 'current_head=%s\n' "$CURRENT_HEAD"
  if [[ -n "$CURRENT_HEAD" && "$mirror_head" == "$CURRENT_HEAD" ]] && \
     git --git-dir="$LOCAL_MIRROR" fsck --strict >/tmp/g4gpu_phase5_mirror_fsck 2>&1; then
    cat /tmp/g4gpu_phase5_mirror_fsck
    MIRROR_READY=yes
  else
    cat /tmp/g4gpu_phase5_mirror_fsck 2>/dev/null || true
    MIRROR_READY=no
  fi
else
  echo "local mirror not found: $LOCAL_MIRROR"
  MIRROR_READY=no
fi

section "GitHub auth and publication readiness"
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/tmp/g4gpu_phase5_gh_auth 2>&1; then
    GITHUB_AUTH_READY=yes
  else
    GITHUB_AUTH_READY=no
  fi
  cat /tmp/g4gpu_phase5_gh_auth
else
  echo "gh not found"
  GITHUB_AUTH_READY=no
fi

section "remote refs"
if git ls-remote --heads "$REMOTE" "$BRANCH" >/tmp/g4gpu_phase5_remote_ref 2>/tmp/g4gpu_phase5_remote_err; then
  printf '%s %s ref:\n' "$REMOTE" "$BRANCH"
  cat /tmp/g4gpu_phase5_remote_ref
else
  printf '%s %s ref check failed:\n' "$REMOTE" "$BRANCH" >&2
  cat /tmp/g4gpu_phase5_remote_err >&2 || true
fi
if git remote get-url "$FORK_REMOTE" >/tmp/g4gpu_phase5_fork_url 2>/tmp/g4gpu_phase5_fork_url_err; then
  if git ls-remote --heads "$FORK_REMOTE" "$BRANCH" >/tmp/g4gpu_phase5_fork_ref 2>/tmp/g4gpu_phase5_fork_ref_err; then
    printf '%s %s ref:\n' "$FORK_REMOTE" "$BRANCH"
    cat /tmp/g4gpu_phase5_fork_ref
  else
    printf '%s %s ref check failed or branch absent:\n' "$FORK_REMOTE" "$BRANCH" >&2
    cat /tmp/g4gpu_phase5_fork_ref >&2 || true
    cat /tmp/g4gpu_phase5_fork_ref_err >&2 || true
  fi
else
  printf 'fork remote unavailable (%s):\n' "$FORK_REMOTE"
  cat /tmp/g4gpu_phase5_fork_url_err || true
fi

section "push dry-runs"
if [[ "$GITHUB_AUTH_READY" == yes ]]; then
  if GIT_TERMINAL_PROMPT=0 git push --dry-run "$REMOTE" "HEAD:refs/heads/${BRANCH}" >/tmp/g4gpu_phase5_origin_push 2>&1; then
    GITHUB_ORIGIN_PUSH_READY=yes
    GITHUB_READY=yes
    GITHUB_PUBLICATION_REMOTE="$REMOTE"
    printf '%s dry-run push OK\n' "$REMOTE"
    cat /tmp/g4gpu_phase5_origin_push
  else
    GITHUB_ORIGIN_PUSH_READY=no
    printf '%s dry-run push failed:\n' "$REMOTE"
    cat /tmp/g4gpu_phase5_origin_push
  fi

  if [[ "$GITHUB_READY" != yes ]]; then
    if git remote get-url "$FORK_REMOTE" >/dev/null 2>&1 && \
       GIT_TERMINAL_PROMPT=0 git push --dry-run "$FORK_REMOTE" "HEAD:refs/heads/${BRANCH}" >/tmp/g4gpu_phase5_fork_push 2>&1; then
      GITHUB_FORK_PUSH_READY=yes
      GITHUB_READY=yes
      GITHUB_PUBLICATION_REMOTE="$FORK_REMOTE"
      printf '%s dry-run push OK\n' "$FORK_REMOTE"
      cat /tmp/g4gpu_phase5_fork_push
    else
      GITHUB_FORK_PUSH_READY=no
      printf '%s dry-run push failed or unavailable:\n' "$FORK_REMOTE"
      cat /tmp/g4gpu_phase5_fork_push 2>/dev/null || true
    fi
  else
    GITHUB_FORK_PUSH_READY=not_needed
  fi
else
  GITHUB_READY=no
  GITHUB_ORIGIN_PUSH_READY=no
  GITHUB_FORK_PUSH_READY=no
fi

section "summary"
printf 'GPU_CTEST_READY=%s\n' "$GPU_CTEST_READY"
printf 'CHECKSUM_READY=%s\n' "$CHECKSUM_READY"
printf 'MIRROR_READY=%s\n' "$MIRROR_READY"
printf 'GITHUB_AUTH_READY=%s\n' "$GITHUB_AUTH_READY"
printf 'GITHUB_ORIGIN_PUSH_READY=%s\n' "$GITHUB_ORIGIN_PUSH_READY"
printf 'GITHUB_FORK_PUSH_READY=%s\n' "$GITHUB_FORK_PUSH_READY"
printf 'GITHUB_PUBLICATION_REMOTE=%s\n' "$GITHUB_PUBLICATION_REMOTE"
printf 'GITHUB_READY=%s\n' "$GITHUB_READY"
if [[ "$GPU_CTEST_READY" == yes && "$CHECKSUM_READY" == yes && "$MIRROR_READY" == yes && "$GITHUB_READY" == yes ]]; then
  echo "READY: external blockers appear clear for GitHub publication via ${GITHUB_PUBLICATION_REMOTE}; push branch and request planner review before 5d."
else
  echo "BLOCKED: do not start 5d yet."
fi

cat <<'MSG'

Next steps after blockers clear:
1. Require GPU CTest job 3041846 to complete successfully (or rerun an equivalent GPU CTest).
2. Publish to GitHub with the ready remote reported above; if origin is denied, push the fork branch and open/update a draft PR to origin/lane/g4gpu-phase5.
3. Ask planner to review the 5a--5c measurement framework before any 5d L0 work.
MSG
