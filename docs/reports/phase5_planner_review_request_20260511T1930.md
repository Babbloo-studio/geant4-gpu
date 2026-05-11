# Phase 5 planner review request — 2026-05-11 19:30 CEST

Lane: `g4gpu-phase5`
Requesting pane: G4GPU pane 0
Current audited HEAD before this request: `608ec24`

## Requested planner decision

Please review the Phase 5a--5c measurement framework and decide whether pane 0
may proceed to Phase 5d once the remaining external gates clear. This request is
**not** asking for immediate 5d execution; the lane spec still requires planner
review plus full GPU CTest/publication closure before L0 optimization work.

## Evidence package

Primary repo evidence:

- `docs/reports/phase5_completion_audit_20260511T1926.md` — full
  prompt-to-artifact checklist and completion audit.
- `docs/reports/phase5_measurement_audit.md` — original 5a--5c implementation
  audit for profiled commit `57800c2`.
- `docs/reports/phase5_artifact_manifest_57800c2.md` — hashes and sizes for
  ignored LUNARC Parquet, canonical-log, validation, SLURM, and perf evidence.
- `scripts/phase5_resume_after_blockers.sh` — current blocker/resume helper;
  reports `GPU_CTEST_READY`, `CHECKSUM_READY`, `MIRROR_READY`, and
  `GITHUB_READY`.

Credential-free publication evidence:

- Bare mirror: `/projects/hep/fs10/shared/nnbar/billy/g4gpu-phase5-publication/geant4-gpu-phase5.git`
- Bundle, patch, request-pull, README, status JSON, and transcripts in
  `/projects/hep/fs10/shared/nnbar/billy/g4gpu-phase5-publication/`
- Latest checksum file at request time: `SHA256SUMS-608ec24`

## Current green gates

- Six benchmark drivers exist and LUNARC job `3041865` produced six 1000-event
  Parquet outputs for `57800c2`.
- Six canonical Geant4 example logs were produced for `57800c2`.
- Six CPU `perf report`/`perf annotate` artifacts are committed for
  `57800c2`.
- Six validation self-comparisons passed all four required observables.
- Focused non-device measurement CTest gate passes 9/9.
- Fallback mirror/bundle/patch verification passes, including mirror fsck and
  clone/tree-match checks.

## Current blockers

- Full GPU CTest job `3041846` is still `PENDING` / `Priority`; latest observed
  scheduler estimate is `2026-05-12T09:51:19` on `cg06`.
- GitHub push is blocked in this pane: dry-run push cannot read an HTTPS
  username and `gh auth status` reports no login.
- Login-node full CTest is not a substitute for the GPU CTest; device tests fail
  outside a GPU allocation with CUDA driver/runtime mismatch.
- Phase 5d is intentionally unstarted per the lane stop condition.

## Review questions

1. Is the 5a--5c measurement framework sufficient for planner approval once GPU
   CTest completes?
2. If GitHub credentials remain unavailable, is the verified local mirror plus
   bundle/patch fallback acceptable as temporary publication closure?
3. After GPU CTest passes and publication is accepted, should pane 0 start 5d.1
   (`src/physics/CrossSectionInterpolator.cc`) or wait for a separate queued
   5d task spec?

## Guardrail

Until those questions are answered and GPU CTest/publication gates clear, pane 0
must keep reporting `BLOCKED: do not start 5d yet` and must not edit the 5d L0
optimization target files.
