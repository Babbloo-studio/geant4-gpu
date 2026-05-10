# G4GPU

G4GPU is a Phase-0 skeleton for a Geant4 custom tracking manager that batches
tracks into structure-of-arrays buffers and exercises a minimal CUDA transfer
path.  This repository currently contains infrastructure only: pinned host
track buffers, mirrored device buffers, a `G4VTrackingManager` subclass, a
geometry backend interface, a hit-buffer declaration, and a null CUDA kernel.

## Status

Implemented Phase 0 infrastructure:

- `G4GPUTrackBuffer`: pinned host allocations with `cudaMallocHost`, mirrored
  device allocations with `cudaMalloc`, and basic AoS (`G4Track`) to SoA copy.
- `G4GPUTrackingManager`: accepts tracks, appends them to the buffer, flushes a
  batch through one H2D transfer, one null kernel launch, one device sync, and
  one D2H transfer.
- `G4GPUGeometry` and `VoxelGeometry`: abstract geometry interface plus a CPU
  stub for later voxel grid construction.
- `G4GPUHitBuffer`: Phase-0 hit SoA declaration and `NullStepKernel` launch API.
- `tests/test_stub.cc`: allocates 1024 tracks, runs the null kernel, and checks
  every status becomes stopped (`1`).

Physics, real geometry navigation, secondary injection, and hit accumulation are
intentionally stubbed for later phases.

## Build

Requirements:

- CMake 3.18+
- C++17 compiler
- CUDA Toolkit with `nvcc`
- Geant4 11+ with CMake config files

Configure and build:

```bash
cmake -B build \
  -DCMAKE_CUDA_COMPILER=$(which nvcc 2>/dev/null || echo nvcc) \
  -DGeant4_DIR=/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/lib/cmake/Geant4 \
  -DG4GPU_WITH_OPTICAL=OFF -DG4GPU_WITH_RTX=OFF \
  .
cmake --build build -j4
```

The default CUDA architectures are SM 80 and SM 86, matching the Phase-0 lane
requirements.

## Runtime stub test

```bash
./build/tests/test_stub
```

Expected output:

```text
PASS
```

The test validates the Phase-0 H2D/kernel/D2H path by confirming that the null
kernel changes all 1024 track statuses from alive (`0`) to stopped (`1`).
