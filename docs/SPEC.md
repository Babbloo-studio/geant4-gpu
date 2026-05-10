# G4GPU Full Specification

See docs/DESIGN_BRIEF.md for the overview.

This spec is the codex implementation guide.

## Repo layout

```
geant4-gpu/
├── include/g4gpu/
│   ├── G4GPUTrackingManager.hh   — G4VTrackingManager subclass
│   ├── G4GPUTrackBuffer.hh       — SoA buffer, host+device
│   ├── G4GPUGeometry.hh          — geometry backend interface (voxel + RTX)
│   ├── G4GPUPhysicsTable.hh      — cross-section tables on GPU
│   ├── G4GPUHitBuffer.hh         — hit accumulation
│   └── G4GPUOptical.hh           — optical photon transport interface
├── src/
│   ├── core/
│   │   ├── G4GPUTrackingManager.cc
│   │   └── G4GPUTrackBuffer.cc
│   ├── physics/
│   │   ├── MuonStepKernel.cu     — muon ionization, MCS, bremsstrahlung
│   │   ├── EMStepKernel.cu       — e-/e+/gamma (Compton, pair, brems)
│   │   └── NeutronStepKernel.cu  — elastic scattering
│   ├── geometry/
│   │   ├── VoxelGeometry.cc      — build voxel grid from G4 geometry
│   │   ├── VoxelGeometry.cu      — 3DDA ray march on GPU
│   │   ├── RTXGeometry.cc        — build OptiX BVH from G4 geometry
│   │   └── RTXGeometry.cu        — hardware RT Core ray queries
│   ├── optical/
│   │   ├── OpticalPhotonKernel.cu — OptiX path tracing kernel
│   │   └── ScintillationSampler.cu — scintillation yield + wavelength
│   └── hits/
│       └── G4GPUHitBuffer.cu     — atomic hit accumulation
├── tests/
│   ├── test_muon_range.cc        — muon range in iron vs. Geant4
│   ├── test_mcs.cc               — multiple scattering angle distribution
│   ├── test_em_shower.cc         — EM shower profile
│   ├── test_voxel_geometry.cc    — voxel material lookup accuracy
│   └── test_optical.cc           — optical photon path length distribution
├── examples/
│   └── nnbar/                    — NNBAR cosmic simulation example
├── cmake/
│   └── FindGeant4GPU.cmake
└── CMakeLists.txt
```

## Phase 0: Infrastructure (build this first)

### G4GPUTrackBuffer.hh

```cpp
struct TrackSOA {
    // Kinematics (all float for GPU efficiency)
    float* x, *y, *z;          // position (mm)
    float* dx, *dy, *dz;       // direction (unit)
    float* ekin;                // kinetic energy (MeV)
    float* time;                // global time (ns)
    // Identity
    int*   pdg;                 // PDG code
    int*   material_idx;        // into GPU material table
    int*   volume_idx;          // into GPU volume table
    int*   track_id;
    int*   parent_id;
    // Status
    int*   status;              // 0=alive, 1=stopped, 2=killed, 3=escaped
    // Bookkeeping
    int    size;                // current fill
    int    capacity;            // max tracks
};
```

Allocate with `cudaMallocHost` (pinned) on host side.
Mirror on device with `cudaMalloc`.

### G4GPUTrackingManager.hh

```cpp
class G4GPUTrackingManager : public G4VTrackingManager {
public:
    void HandOverOneTrack(G4Track* track) override;
    void FlushEvent() override;
    void BuildPhysicsTable(const G4ParticleDefinition& pd) override;

    void SetBatchSize(int n);         // default 65536
    void SetGeometryBackend(...);
    void SetPhysicsKernel(...);
private:
    TrackSOA  h_buffer_;              // pinned host buffer
    TrackSOA  d_buffer_;              // device buffer
    G4GPUGeometry*  geometry_;
    G4GPUPhysicsTable* tables_;
    int batch_size_ = 65536;
    void LaunchKernels_();
    void InjectSecondaries_();        // push GPU secondaries → G4EventManager
};
```

### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.18)
project(G4GPU LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_ARCHITECTURES 80)   # A100; also supports 70 (Volta), 86 (RTX 30xx), 89 (RTX 40xx)

find_package(Geant4 REQUIRED)
find_package(CUDAToolkit REQUIRED)

option(G4GPU_WITH_EM       "Enable EM shower kernels"        ON)
option(G4GPU_WITH_MUON     "Enable muon physics kernels"     ON)
option(G4GPU_WITH_NEUTRON  "Enable neutron elastic"          ON)
option(G4GPU_WITH_OPTICAL  "Enable OptiX optical transport"  OFF)  # requires OptiX SDK
option(G4GPU_WITH_RTX      "Enable RTX geometry backend"     OFF)  # requires OptiX SDK + SM >= 7.0

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
    find_package(OptiX REQUIRED)   # set OptiX_INSTALL_DIR or OPTIX_PATH
endif()

add_library(G4GPU SHARED ...)
target_link_libraries(G4GPU PUBLIC ${Geant4_LIBRARIES} CUDA::cudart CUDA::curand)
if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
    target_link_libraries(G4GPU PUBLIC ${OptiX_LIBRARIES})
    target_include_directories(G4GPU PRIVATE ${OptiX_INCLUDE_DIRS})
endif()
target_include_directories(G4GPU PUBLIC include)
```

## Phase 1: Muon physics kernel (MuonStepKernel.cu)

Each CUDA thread handles ONE muon step.

### Muon ionization (Bethe-Bloch)

```cuda
__device__ float BetheBloch(float ekin, float mass, const MaterialData& mat) {
    // Standard Bethe-Bloch formula
    // Returns mean dE/dx in MeV/mm
    float gamma = 1.0f + ekin / mass;
    float beta2 = 1.0f - 1.0f / (gamma * gamma);
    float beta = sqrtf(beta2);
    float Tmax = 2.0f * ME * beta2 * gamma * gamma /
                 (1.0f + 2.0f * gamma * ME / mass + (ME/mass)*(ME/mass));
    float K = 0.307075f;  // MeV cm²/mol
    float dEdx = K * mat.Z_over_A / beta2 *
                 (0.5f * logf(2.0f * ME * beta2 * gamma*gamma * Tmax /
                              (mat.I * mat.I)) - beta2);
    return dEdx * mat.density;  // MeV/mm
}
```

Landau straggling: use curand to sample from a Landau distribution or
Gaussian approximation (valid for thick absorbers, use Landau for thin).

### Multiple Coulomb scattering (Highland formula)

```cuda
__device__ float HighlandTheta0(float p, float beta, float x_over_X0) {
    float theta0 = (13.6f / (p * beta)) * sqrtf(x_over_X0) *
                   (1.0f + 0.038f * logf(x_over_X0 / (beta*beta)));
    return theta0;  // radians
}
```
Sample theta from Gaussian(0, theta0), phi uniform [0, 2pi].
Update direction: Rodrigues rotation formula.

### Bremsstrahlung (muon)

Mean free path from tabulated cross-section. When step ends at brem vertex:
- Sample photon energy from differential spectrum (approximate as 1/k)
- Create secondary photon (add to secondary buffer)
- For secondary photon: delegate to GPU EM kernel OR push to Geant4 CPU

## Phase 2: Voxel Geometry (VoxelGeometry.cu)

### Building the voxel grid (CPU, once at startup)

```cpp
void VoxelGeometry::Build(G4VPhysicalVolume* world, float voxel_mm) {
    // Walk the Geant4 geometry tree
    // For each voxel centre: shoot probe → find volume → get material
    // Store material_idx and sd_idx in flat 3D array
    // Transfer to GPU with cudaMemcpy
}
```

### Stepping on GPU (3DDA ray march)

```cuda
__device__ float DistanceToNextVoxelBoundary(
    float3 pos, float3 dir,
    const VoxelGrid grid
) {
    // Amanatides & Woo (1987) 3D DDA
    // Returns distance to next voxel boundary in mm
    // Also returns next voxel indices (to detect material change)
}
```

## Phase 3: RTX Geometry Backend (RTXGeometry.cu)

Use NVIDIA RT Cores (OptiX 8+) for hardware-accelerated geometry navigation.
This is the same hardware that game engines use for real-time ray tracing.
**No HEP experiment has used RT Cores for geometry navigation before — this is novel.**

### Why RT Cores for HEP

RT Cores implement hardware BVH (Bounding Volume Hierarchy) traversal at ~10 Giga-rays/sec.
`G4Navigator::LocateGlobalPointAndSetup()` does the same thing in software, one track at a time.
The RT Core query — given a ray (origin, direction), find the first geometry boundary —
is exactly the step-limiting geometry query in `G4SteppingManager`.

### Build BVH from Geant4 geometry (CPU, startup)

```cpp
void RTXGeometry::Build(G4VPhysicalVolume* world) {
    // Walk G4 geometry tree → collect all solid surfaces as triangle meshes
    // G4TessellatedSolid → direct; G4Box/G4Tubs → approximate with triangles
    // Create OptixBuildInput per logical volume
    // optixAccelBuild() → GAS (Geometry Acceleration Structure) per solid
    // optixAccelBuild() → IAS (Instance Acceleration Structure) for world
    // Record volume_id and material_id in SBT (Shader Binding Table) hit records
}
```

### GPU ray query (replaces G4Navigator)

```cuda
// In step kernel: find distance to next boundary
__device__ float DistanceToNextBoundary_RTX(
    float3 pos, float3 dir,
    OptixTraversableHandle bvh,
    int& next_volume_idx          // output: volume after crossing
) {
    OptixRay ray = {pos, 0.0f, dir, 1e9f};
    OptixPayload payload;
    optixTrace(bvh, ray.origin, ray.direction,
               ray.tmin, ray.tmax, 0.0f,
               OptixVisibilityMask(0xFF), OPTIX_RAY_FLAG_NONE,
               0, 1, 0,
               payload.volume_idx, payload.distance);
    next_volume_idx = payload.volume_idx;
    return payload.distance;
}
```

The `__closesthit__` program runs in the SBT and writes `volume_id` + `t` to payload.
The result is: distance to next volume boundary + which volume that is — exactly what
G4Navigator provides, delivered by hardware RT Cores.

### Accuracy vs. voxel

RTX gives **exact** geometry boundaries (triangle mesh precision), not voxel-approximate.
Trade-off: BVH build is heavier at startup; ray queries are faster and exact.
Recommended: start with voxel (Phase 2), add RTX backend for precision mode.

---

## Phase 4: Optical Photon Transport (OpticalPhotonKernel.cu)

Optical photons in Geant4 are the slowest component: scintillation light + Cherenkov
produce thousands of photons per event, transported one at a time on CPU.
This is literally **path tracing** — the same algorithm used for realistic lighting in games.

### Physics mapping to OptiX

| Geant4 optical process | OptiX equivalent |
|---|---|
| `G4OpBoundaryProcess` — reflection/refraction at surfaces | `__closesthit__` program: Snell's law + Fresnel equations |
| `G4OpAbsorption` — bulk absorption | `__miss__` program: Beer-Lambert exponential sampling |
| `G4OpRayleigh` — Rayleigh scattering | Direction perturbation in `__closesthit__` |
| Cherenkov angle — cone of photons | Generate photon directions on CPU, launch as OptiX batch |
| Scintillation yield — photons per MeV | Sample from yield table, generate initial positions |
| PMT hit detection | `__closesthit__` program on PMT surface → write to hit buffer |

### Optical kernel design

```cuda
// Each OptiX ray = one optical photon
// __raygen__ program: read photon from buffer, launch ray
// __closesthit__ program: determine surface interaction
//     - compute Fresnel coefficients (n1, n2 from material table)
//     - sample: reflected or transmitted (Russian roulette)
//     - if absorbed: write hit to PMT buffer (atomicAdd)
//     - if scattered (Rayleigh): sample new direction
// __miss__ program: photon escaped detector → mark killed
// Bulk absorption: exponential sampling of mean free path per material

__global__ void OpticalPhotonKernel(
    PhotonSOA photons,          // SoA: pos, dir, wavelength, polarization
    OptixTraversableHandle bvh,
    MaterialOpticalData* mats,  // refractive index, absorption length per material + wavelength
    PMTHitBuffer* pmt_hits,
    curandState* rng,
    int n_photons
);
```

### Expected speedup

NNBAR has 6 scintillator bars + PMTs. One cosmic muon event produces ~50k optical photons.
CPU: ~50k photons × ~100 bounces × ~1 μs/bounce = 5 seconds per event.
GPU: 50k OptiX rays, RT Cores at ~10 Giga-rays/sec = ~0.5 ms.
**Theoretical speedup: ~10,000×** on the optical component alone.

---

## Validation tests (build alongside each phase)

### test_muon_range.cc
- Fire 10 GeV muon straight into iron slab
- Compare G4GPU range vs. Geant4 range
- Accept: within 2%

### test_mcs.cc
- 1 GeV muons through 10 cm iron
- Compare theta_plane distribution
- Accept: mean within 2%, RMS within 5%

### test_voxel_geometry.cc
- Probe random points in NNBAR geometry
- Compare G4GPU material lookup vs. G4Navigator::LocateGlobalPointAndSetup()
- Accept: 100% agreement at 1mm voxel size

## What codex should produce first

Focus on Phase 0 only:
1. `CMakeLists.txt` — working cmake that finds Geant4 + CUDA
2. `include/g4gpu/G4GPUTrackingManager.hh` — full class declaration
3. `include/g4gpu/G4GPUTrackBuffer.hh` — TrackSOA struct + Buffer class
4. `include/g4gpu/G4GPUGeometry.hh` — abstract base class for geometry backends
5. `include/g4gpu/G4GPUHitBuffer.hh` — HitSOA struct
6. `src/core/G4GPUTrackingManager.cc` — HandOverOneTrack + FlushEvent skeleton
   (kernels stubbed, just buffer management + device transfer working)
7. `src/core/G4GPUTrackBuffer.cc` — pinned alloc + AoS→SoA conversion
8. `src/geometry/VoxelGeometry.cc` — stub (CPU build/fill only, no CUDA yet)
9. `src/hits/G4GPUHitBuffer.cu` — stub kernel: `__global__ void NullStepKernel`
   that memsets status to 1 (stopped) — proves H2D/D2H transfer works
10. `README.md` — project description, build instructions, status

### Build verification protocol

The codex implementation MUST pass all three checks:

**Check 1 — cmake configure:**
```bash
cmake -B build -DCMAKE_CUDA_COMPILER=nvcc \
      -DGeant4_DIR=<path> \
      -DG4GPU_WITH_OPTICAL=OFF -DG4GPU_WITH_RTX=OFF \
      .
# Must succeed with no errors
```

**Check 2 — compile (no GPU needed):**
```bash
cmake --build build -j$(nproc)
# Must produce libG4GPU.so with no warnings treated as errors
```

**Check 3 — runtime stub test (GPU required, run on LUNARC gpua40):**
```bash
./build/tests/test_stub
# Creates 1024-track buffer, H2D transfer, launches NullStepKernel,
# D2H transfer, verifies all status==1. Prints: PASS or FAIL.
```

Geant4 install for codex: `/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/`
CUDA architectures target: `80` (A100), also enable `75` for local RTX cards.

### CUDA device compatibility

The framework targets SM 7.0+ (Volta and later):
- SM 7.0: V100 (LUNARC old)
- SM 8.0: A100 (LUNARC primary — `gpua100` partition)
- SM 8.6: RTX 3090/A6000 (local dev)
- SM 8.9: RTX 4090 (local dev)

Set `CMAKE_CUDA_ARCHITECTURES=80;86;89` for broad compatibility.
OptiX/RTX backend requires SM 7.0+ and OptiX SDK 8.0+.
