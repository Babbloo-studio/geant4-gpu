# Phase 3 RTX geometry backend status

This compact Phase 3 iteration wires the verified OptiX 9.0 SDK into G4GPU and
adds the first RTX geometry backend interface. It is research-only and remains
isolated from NNBAR production.

Implemented surfaces:

- `cmake/FindOptiX.cmake` discovers the SDK by `OptiX_INSTALL_DIR`.
- `G4GPU_WITH_RTX=ON` compiles `RTXGeometry.cc/.cu` into `libG4GPU.so`.
- `RTXGeometry` walks `G4VPhysicalVolume` solids, emits triangle meshes for
  `G4Box` and `G4Tubs`, allocates CUDA buffers, and builds an OptiX GAS from the
  real SDK headers/stubs.
- Named OptiX program entry points (`__raygen__boundary_query`,
  `__closesthit__record_boundary`, `__miss__no_boundary`) compile as the
  placeholder shader surface for the later SBT/pipeline runtime launcher.
- `g4gpu_rtx_geometry` verifies both ON/OFF compile paths without requiring a
  detector world or GPU ray launch.

Open Phase 3 follow-ups before physics/performance claims:

- Wire the OptiX module, program groups, pipeline, SBT records, launch params,
  and `optixLaunch` path so `DistanceToNextBoundary` uses RT Cores at runtime.
- Preserve volume/material IDs through instance or SBT hit records.
- Add the V5 accuracy comparison against `G4Navigator`.
- Run the V5 GPU-node validation before claiming exact boundary equivalence or
  speedup.

No NNBAR production code, data path, SLURM production job, physics claim, or
speed claim is changed by this iteration.
