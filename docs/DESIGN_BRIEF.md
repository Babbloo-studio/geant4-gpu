# G4GPU Design Brief

## What

G4GPU is a general-purpose GPU transport acceleration framework for Geant4.
It accelerates ALL particle types — muons, hadrons, electrons, gammas — not just EM
like Celeritas/AdePT. It works without VecGeom and without modifying Geant4 source.

## Why this is different from Celeritas / AdePT

| Feature | Celeritas | AdePT | **G4GPU** |
|---|---|---|---|
| Particle types | e⁻ e⁺ γ only | e⁻ e⁺ γ only | All types |
| Muon physics on GPU | ✗ | ✗ | ✓ |
| Hadronic physics on GPU | ✗ | ✗ | Partial (elastic) |
| VecGeom required | ✓ | ✓ | ✗ |
| Geometry backend | VecGeom | VecGeom | Voxel or Analytic |
| Geant4 source mod | ✗ | ✗ | Optional |

## How it works

Geant4 11+ provides `G4VTrackingManager` — an official plugin API that lets you
intercept entire particle species and transport them yourself:

```
G4EventManager
    → G4TrackingManager::ProcessOneTrack()   [CPU, per-track]
    → G4VTrackingManager::HandOverOneTrack() [G4GPU intercepts here]
        → buffer accumulates tracks
    → G4VTrackingManager::FlushEvent()       [G4GPU flushes to GPU here]
        → CUDA kernels run
        → results returned to Geant4
```

No Geant4 source modification required for the core. Optional deeper patches add
a `FlushMidEvent()` hook for high-secondary-multiplicity events.

## Five core components

1. **G4GPUTrackingManager** — intercepts tracks, converts AoS→SoA, batches
2. **G4GPUTrackBuffer** — SoA track buffer in pinned host memory + device memory
3. **G4GPUPhysicsKernel** — pluggable CUDA kernels per particle/process
4. **G4GPUGeometry** — voxel grid (fast, approximate) or analytic (exact)
5. **G4GPUHitBuffer** — atomic GPU hit accumulation → injected back to Geant4 SDs

## Target hardware

NVIDIA GPUs with compute capability ≥ 7.0 (Volta+).
Primary target: A100 (LUNARC HPC cluster).

## Proving ground: NNBAR cosmic simulation

First application: accelerating high-energy cosmic muon simulation for the NNBAR
neutron-antineutron oscillation experiment. Cosmic muons are the main background
and the slowest to simulate — high-energy muons produce EM showers with thousands
of secondaries.
