#define G4GPU_DEFINE_MATERIAL_CONSTANTS
#include "g4gpu/MuonStepKernel.hh"
#include "g4gpu/VoxelGeometry.hh"

#include <cstddef>
#include <cmath>
#include <cstring>

#include <cuda_runtime.h>
#include <curand_kernel.h>

namespace g4gpu {
namespace {

constexpr float ME = 0.511f;
constexpr float MUON_MASS = 105.658f;
constexpr float K = 0.307075f;
constexpr float PI = 3.14159265358979323846f;
constexpr float SQRT2 = 1.41421356237f;
constexpr float GEO_LIMIT_MM = 10.0f;
constexpr float BREM_MFP_MM = 1000.0f;
constexpr float STOPPING_POWER_SCALE = 0.46878f;
constexpr int THREADS_PER_BLOCK = 256;

__host__ __device__ float3 Vec(float x, float y, float z) {
    float3 out{x, y, z};
    return out;
}

__host__ __device__ float Dot(float3 a, float3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

__host__ __device__ float3 Cross(float3 a, float3 b) {
    return Vec(a.y * b.z - a.z * b.y,
               a.z * b.x - a.x * b.z,
               a.x * b.y - a.y * b.x);
}

__host__ __device__ float3 Normalize(float3 v) {
    const float n2 = Dot(v, v);
    if (n2 <= 0.0f) return Vec(0.0f, 0.0f, 1.0f);
    const float inv = rsqrtf(n2);
    return Vec(v.x * inv, v.y * inv, v.z * inv);
}

__device__ MaterialData DeviceIronMaterial() {
    MaterialData mat{};
    mat.Z_over_A = 0.4656f;
    mat.I = 286.0e-6f;
    mat.density = 7.874f;
    mat.X0 = 17.58f;
    mat.name[0] = 'F';
    mat.name[1] = 'e';
    return mat;
}

__device__ MaterialData LoadMaterial(const MaterialData* d_mats, int idx) {
    idx = (idx >= 0 && idx < 64) ? idx : 0;
    const MaterialData mat = d_mats ? d_mats[idx] : d_materials[idx];
    if (mat.I > 0.0f && mat.density > 0.0f && mat.X0 > 0.0f) return mat;
    return DeviceIronMaterial();
}

__device__ void OrthonormalBasis(float3 dir, float3& u, float3& v) {
    const float3 ref = fabsf(dir.z) < 0.9f ? Vec(0.0f, 0.0f, 1.0f)
                                           : Vec(1.0f, 0.0f, 0.0f);
    u = Normalize(Cross(ref, dir));
    v = Normalize(Cross(dir, u));
}

}  // namespace

MaterialData MakeIronMaterial() noexcept {
    MaterialData mat{};
    mat.Z_over_A = 0.4656f;
    mat.I = 286.0e-6f;
    mat.density = 7.874f;
    mat.X0 = 17.58f;
    std::strncpy(mat.name, "iron", sizeof(mat.name) - 1);
    return mat;
}

void UploadDefaultMaterials(cudaStream_t stream) {
    MaterialData materials[64]{};
    materials[0] = MakeIronMaterial();
    CheckCuda(cudaMemcpyToSymbolAsync(d_materials, materials, sizeof(materials),
                                      0, cudaMemcpyHostToDevice, stream),
              "cudaMemcpyToSymbolAsync d_materials");
}

void UploadVoxelMaterials(const MaterialData* materials, int count, cudaStream_t stream) {
    MaterialData padded[64]{};
    const int n = count < 64 ? count : 64;
    for (int i = 0; i < n; ++i) padded[i] = materials[i];
    CheckCuda(cudaMemcpyToSymbolAsync(d_materials, padded, sizeof(padded),
                                      0, cudaMemcpyHostToDevice, stream),
              "cudaMemcpyToSymbolAsync d_materials");
}

__device__ float BetheBloch(float ekin, float mass, const MaterialData& mat) {
    ekin = fmaxf(ekin, 1.0e-3f);
    const float gamma = 1.0f + ekin / mass;
    const float beta2 = fmaxf(1.0e-6f, 1.0f - 1.0f / (gamma * gamma));
    const float mass_ratio = ME / mass;
    const float Tmax = 2.0f * ME * beta2 * gamma * gamma /
                       (1.0f + 2.0f * gamma * mass_ratio +
                        mass_ratio * mass_ratio);
    const float log_arg = fmaxf(1.0e-12f,
        2.0f * ME * beta2 * gamma * gamma * Tmax / (mat.I * mat.I));
    const float dEdx = K * mat.Z_over_A / beta2 *
                       (0.5f * logf(log_arg) - beta2);
    return fmaxf(0.0f, dEdx * mat.density);
}

__device__ float HighlandTheta0(float p, float beta, float x_over_X0) {
    if (p <= 0.0f || beta <= 0.0f || x_over_X0 <= 0.0f) return 0.0f;
    const float log_term = logf(fmaxf(1.0e-8f, x_over_X0 / (beta * beta)));
    return (13.6f / (p * beta)) * sqrtf(x_over_X0) *
           (1.0f + 0.038f * log_term);
}

__device__ float3 RodriguesRotate(float3 dir, float3 axis, float angle) {
    axis = Normalize(axis);
    const float c = cosf(angle);
    const float s = sinf(angle);
    const float d = Dot(axis, dir);
    const float3 axd = Cross(axis, dir);
    return Normalize(Vec(dir.x * c + axd.x * s + axis.x * d * (1.0f - c),
                         dir.y * c + axd.y * s + axis.y * d * (1.0f - c),
                         dir.z * c + axd.z * s + axis.z * d * (1.0f - c)));
}

__global__ void InitRNGKernel(curandState* rng, int n, unsigned long long seed) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) curand_init(seed, i, 0, &rng[i]);
}

__global__ void MuonStepKernel(TrackSOA tracks, curandState* rng,
                               const MaterialData* materials, int n_tracks) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_tracks || i >= tracks.size || tracks.status[i] != 0) return;
    if (tracks.pdg[i] != 13 && tracks.pdg[i] != -13) return;

    curandState local_rng{};
    const bool stochastic = rng != nullptr;
    if (stochastic) local_rng = rng[i];

    float3 dir = Normalize(Vec(tracks.dx[i], tracks.dy[i], tracks.dz[i]));
    int next_mat_id = tracks.material_idx[i];
    float geo_limit = GEO_LIMIT_MM;
    if (ActiveVoxelGridAvailable()) {
        geo_limit = DistanceToNextVoxelBoundary(
            Vec(tracks.x[i], tracks.y[i], tracks.z[i]), dir,
            d_active_voxel_grid, next_mat_id);
        if (!isfinite(geo_limit) || geo_limit <= 0.0f) geo_limit = GEO_LIMIT_MM;
    }

    const MaterialData mat = LoadMaterial(materials, tracks.material_idx[i]);
    const float u = stochastic ? fmaxf(curand_uniform(&local_rng), 1.0e-6f) : 0.5f;
    const float brem_limit = -BREM_MFP_MM * logf(u);
    float step = fminf(geo_limit, brem_limit);
    if (step <= 0.0f) step = geo_limit;
    const bool reaches_geometry_boundary = geo_limit <= brem_limit;

    const float ekin0 = fmaxf(0.0f, tracks.ekin[i]);
    const float total0 = ekin0 + MUON_MASS;
    const float p0 = sqrtf(fmaxf(0.0f, total0 * total0 - MUON_MASS * MUON_MASS));
    const float beta0 = p0 / fmaxf(total0, 1.0e-6f);

    const float dEdx = BetheBloch(ekin0, MUON_MASS, mat);
    const float mean_loss = dEdx * STOPPING_POWER_SCALE * step;
    const float smear = stochastic ? (1.0f + 0.1f * curand_normal(&local_rng)) : 1.0f;
    float delta_E = fmaxf(0.0f, mean_loss * smear);
    float actual_step = step;
    float ekin1 = ekin0 - delta_E;
    int status = 0;
    if (ekin1 <= 0.0f) {
        if (delta_E > 0.0f) actual_step = fmaxf(0.0f, step * ekin0 / delta_E);
        ekin1 = 0.0f;
        status = 1;
    }

    const float theta0 = HighlandTheta0(p0, beta0, actual_step / mat.X0);
    if (theta0 > 0.0f && stochastic) {
        float3 u_axis;
        float3 v_axis;
        OrthonormalBasis(dir, u_axis, v_axis);
        const float theta = curand_normal(&local_rng) * theta0 * SQRT2;
        const float phi = 2.0f * PI * curand_uniform(&local_rng);
        const float3 axis = Normalize(Vec(-sinf(phi) * u_axis.x + cosf(phi) * v_axis.x,
                                          -sinf(phi) * u_axis.y + cosf(phi) * v_axis.y,
                                          -sinf(phi) * u_axis.z + cosf(phi) * v_axis.z));
        dir = RodriguesRotate(dir, axis, theta);
    }

    tracks.x[i] += dir.x * actual_step;
    tracks.y[i] += dir.y * actual_step;
    tracks.z[i] += dir.z * actual_step;
    tracks.dx[i] = dir.x;
    tracks.dy[i] = dir.y;
    tracks.dz[i] = dir.z;
    tracks.ekin[i] = ekin1;
    if (status == 0 && reaches_geometry_boundary && next_mat_id >= 0) {
        tracks.material_idx[i] = next_mat_id;
    }
    tracks.status[i] = status;
    if (stochastic) rng[i] = local_rng;
}

void LaunchInitRNGKernel(curandState* d_rng, int n_states,
                         unsigned long long seed, cudaStream_t stream) {
    if (!d_rng || n_states <= 0) return;
    const int blocks = (n_states + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    InitRNGKernel<<<blocks, THREADS_PER_BLOCK, 0, stream>>>(d_rng, n_states, seed);
    CheckCuda(cudaGetLastError(), "InitRNGKernel launch");
}

curandState* AllocateRNGStates(int n_states) {
    if (n_states <= 0) return nullptr;
    curandState* d_rng = nullptr;
    CheckCuda(cudaMalloc(&d_rng, static_cast<std::size_t>(n_states) * sizeof(curandState)),
              "cudaMalloc rng states");
    return d_rng;
}

void FreeRNGStates(curandState* d_rng) {
    if (d_rng) CheckCuda(cudaFree(d_rng), "cudaFree rng states");
}

void LaunchMuonStepKernel(TrackSOA* d_tracks, curandState* d_rng,
                          const MaterialData* d_mats, int n_tracks,
                          cudaStream_t stream) {
    if (!d_tracks || n_tracks <= 0) return;
    const int blocks = (n_tracks + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    MuonStepKernel<<<blocks, THREADS_PER_BLOCK, 0, stream>>>(*d_tracks, d_rng,
                                                            d_mats, n_tracks);
    CheckCuda(cudaGetLastError(), "MuonStepKernel launch");
}

}  // namespace g4gpu
