# Phase 5 local CTest refresh — 2026-05-11 19:12 CEST

Lane: `g4gpu-phase5`
Branch before this report: `lane/g4gpu-phase5` at `2fec138`

## Purpose

After the resume-script checksum fix, this pane tried to verify the current
worktree from the LUNARC checkout. This does **not** replace the pending full GPU
CTest job `3041846`; it records why the login-node check is only a partial gate.

## Commands and outcomes

### Full CTest without CUDA module environment

Command:

```bash
ctest --test-dir build --output-on-failure
```

Outcome: `3/13` tests passed and `10/13` failed immediately because the dynamic
loader could not find `libcudart.so.12`. The passing tests were the manifest,
script-syntax, and validation-harness tests. This was an environment setup
failure, not a useful code gate.

Representative failure:

```text
error while loading shared libraries: libcudart.so.12: cannot open shared object file: No such file or directory
```

### Full CTest after loading CUDA 12.8 modules

Command:

```bash
module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || module load GCC/13.2.0 CUDA/12.8.0
ctest --test-dir build --output-on-failure
```

Environment evidence:

```text
/sw/easybuild_milan/software/CUDA/12.8.0/bin/nvcc
libcudart.so.12 => /sw/easybuild_milan/software/CUDA/12.8.0/targets/x86_64-linux/lib/libcudart.so.12
```

Outcome: `9/13` tests passed and `4/13` failed. The non-GPU benchmark and
harness tests passed; the four device/runtime tests (`g4gpu_stub`,
`g4gpu_voxel_geometry`, `g4gpu_muon_range`, `g4gpu_mcs`) aborted on the login
node with:

```text
cudaMallocHost: CUDA driver version is insufficient for CUDA runtime version
cudaMalloc voxel material_id: CUDA driver version is insufficient for CUDA runtime version
```

This confirms the login node cannot clear the device tests even with the CUDA
runtime libraries available.

### Focused non-device measurement-framework gate

Command:

```bash
module load GCC/13.2.0 CUDA/12.8.0 CMake/3.27.6 2>/dev/null || module load GCC/13.2.0 CUDA/12.8.0
ctest --test-dir build -R 'g4gpu_benchmark_manifest|g4gpu_benchmark_script_syntax|g4gpu_validate_harness|g4gpu_benchmark_.*_smoke' --output-on-failure
```

Outcome: `9/9` passed:

- `g4gpu_benchmark_manifest`
- `g4gpu_benchmark_script_syntax`
- `g4gpu_validate_harness`
- six `g4gpu_benchmark_*_smoke` tests

## GPU CTest blocker state

Fresh scheduler check:

```text
3041846 g4gpu-ctest-p5 PENDING Priority TimeLimit=5:00 StartTime=2026-05-12T09:51:19
sacct: 3041846|PENDING|0:0|00:00:00|00:05:00|2026-05-11T17:05:31|Unknown|Unknown|None assigned
```

## Decision

The focused non-device gate is green after the script fix, but the full device
CTest remains blocked on the queued `gpua40` job. Do not start Phase 5d and do
not mark Phase 5 DONE until a GPU-node full CTest passes, GitHub publication is
resolved, and planner review clears the stop condition.
