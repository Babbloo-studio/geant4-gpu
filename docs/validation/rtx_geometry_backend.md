# Phase 3 RTX geometry backend status

This compact Phase 3 iteration wires the verified OptiX 9.0 SDK into G4GPU and
adds a first runtime RTX boundary-query path. It is research-only and remains
isolated from NNBAR production.

Implemented surfaces:

- `cmake/FindOptiX.cmake` discovers the SDK by `OptiX_INSTALL_DIR`.
- `G4GPU_WITH_RTX=ON` compiles `RTXGeometry.cc` into `libG4GPU.so` and compiles
  `RTXGeometry.cu` to PTX for OptiX module creation at runtime.
- `RTXGeometry` triangulates the world `G4Box` (or an extent box fallback),
  allocates CUDA buffers, builds an OptiX triangle GAS, creates module/program
  groups/pipeline/SBT records, and exposes `GetBVH()`.
- `DistanceToNextBoundary` launches the OptiX raygen program and returns the
  closest boundary distance plus hit-record volume id for the current GAS.
- `g4gpu_rtx_geometry` verifies the ON path on a 20 mm box world: 12 triangles,
  a finite +x boundary distance of 10 mm, and populated next-volume id. The OFF
  path remains a compile-safe skip.

Open Phase 3 follow-ups before physics/performance claims:

- Preserve full nested volume/material IDs through instance or per-primitive SBT
  hit records instead of the current single-GAS volume id.
- Add `G4Tubs`, `G4Sphere`, and tessellated-solid meshing beyond the current box
  and extent-box fallback.
- Add the V5 accuracy comparison against `G4Navigator` on a detector geometry.
- Do not claim exact boundary equivalence or speedup until V5 validation passes.

No NNBAR production code, data path, SLURM production job, physics claim, or
speed claim is changed by this iteration.
