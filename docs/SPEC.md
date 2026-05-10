# G4GPU Full Specification

See docs/DESIGN_BRIEF.md for the overview.

This spec is the codex implementation guide.

## Repo layout

```
geant4-gpu/
├── include/g4gpu/
│   ├── G4GPUTrackingManager.hh   — G4VTrackingManager subclass
│   ├── G4GPUTrackBuffer.hh       — SoA buffer, host+device
│   ├── G4GPUGeometry.hh          — geometry backend interface
│   ├── G4GPUPhysicsTable.hh      — cross-section tables on GPU
│   └── G4GPUHitBuffer.hh         — hit accumulation
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
│   │   └── VoxelGeometry.cu      — 3DDA ray march on GPU
│   └── hits/
│       └── G4GPUHitBuffer.cu     — atomic hit accumulation
├── tests/
│   ├── test_muon_range.cc        — muon range in iron vs. Geant4
│   ├── test_mcs.cc               — multiple scattering angle distribution
│   └── test_em_shower.cc         — EM shower profile
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
set(CMAKE_CUDA_ARCHITECTURES 80)   # A100

find_package(Geant4 REQUIRED)
find_package(CUDAToolkit REQUIRED)

option(G4GPU_WITH_EM    "Enable EM shower kernels"      ON)
option(G4GPU_WITH_MUON  "Enable muon physics kernels"   ON)
option(G4GPU_WITH_NEUTRON "Enable neutron elastic"      ON)

add_library(G4GPU SHARED ...)
target_link_libraries(G4GPU PUBLIC ${Geant4_LIBRARIES} CUDA::cudart CUDA::curand)
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
4. `src/core/G4GPUTrackingManager.cc` — HandOverOneTrack + FlushEvent skeleton
   (kernels stubbed, just buffer management + device transfer working)
5. `src/core/G4GPUTrackBuffer.cc` — pinned alloc + AoS→SoA conversion
6. `README.md` — project description, build instructions, status

Syntax check: `cmake -B build -DCMAKE_CUDA_COMPILER=nvcc .` should succeed.
No CUDA device needed to build the CPU parts with stubs.
