# Phase 4 Opticks integration scaffold

Status: compact scaffold only; no optical speedup or physics-equivalence claim.

## Local dependency inventory (2026-05-11)

Searches from the LUNARC checkout found no usable Opticks or NVIDIA OptiX SDK
installation:

- `find /projects/hep/fs10/shared/nnbar/billy/packages /sw /opt /usr/local ...`
  found only CMake help text mentioning CUDA OptiX compilation.
- Targeted `/scratch`, `/home/scyiu`, and `/projects/hep/fs10/shared/nnbar`
  searches found no `optix.h`, `G4CXOpticks.hh`, `NVIDIA-OptiX*`, or
  `libOpticks*` candidate.
- `module spider optix` and `module avail opticks optix` reported no OptiX or
  Opticks modules.
- `ldconfig -p | grep -Ei 'opticks|optix'` found no system library.

The manual OptiX SDK blocker from the NNBAR task plan therefore still applies.
The adapter added here builds and tests the explicit disabled/fallback path when
`G4GPU_WITH_OPTICKS=OFF`.

## Fallback-path build evidence (2026-05-12)

The CMake scaffold now propagates CUDA runtime include and RPATH information to
C++ consumers so fallback tests resolve `cudaStream_t` and `libcudart.so`
consistently in a clean LUNARC shell. Verified commands:

- `cmake -S . -B build_phase4_off -DG4GPU_WITH_OPTICKS=OFF -DG4GPU_WITH_RTX=OFF`
- `cmake --build build_phase4_off -j2`
- `ctest --test-dir build_phase4_off --output-on-failure -R g4gpu_opticks_backend`

The focused fallback test passed. A full local `ctest` on the holder shell still
has four driver-dependent CUDA tests fail with `CUDA driver version is
insufficient for CUDA runtime version`; those are not Phase-4 Opticks fallback
tests and require the usual GPU-node validation path.

## Adapter contract

`g4gpu::OpticksOpticalBackend` is an off-by-default bridge boundary. It accepts
opaque Geant4 world geometry plus compact scintillation/Cerenkov gensteps, but
it does not produce physics hits unless Opticks is compiled, initialized, and a
future validated propagation bridge is implemented.

When unavailable or disabled, the backend reports a reason string and returns
false/empty results so the caller can keep photons on the vanilla Geant4 CPU
optical path. This is intentional fail-closed behavior, not a silent fallback.

## Validation required before any DONE/speed claim

A later Phase 4 validation gate must provide all of the following before G4GPU
optical transport can be promoted beyond scaffold status:

1. A real Opticks + OptiX SDK installation path and compile-on build evidence.
2. Opticks's own validation evidence for the installed version.
3. NNBAR-specific scintillator and lead-glass optical comparisons against CPU
   Geant4: detection efficiency, optical-hit counts, path length, and timing.
4. KS p-values above 0.05 for path-length and timing distributions, plus an
   agreed efficiency tolerance before any performance benchmark is interpreted.
5. Explicit fallback accounting for unsupported geometry/material cases.

No SLURM jobs or benchmark claims were run in this compact iteration.
