#include "g4gpu/NeutronStepKernel.hh"

#include <cmath>

#include <cuda_runtime.h>
#include <curand_kernel.h>

namespace g4gpu {
namespace {

constexpr int THREADS_PER_BLOCK = 256;
constexpr int NEUTRON_PDG = 2112;
constexpr float PI = 3.14159265358979323846f;

__host__ __device__ float ClampUnit(float value) noexcept {
    if (!(value >= -1.0f)) return -1.0f;
    if (value > 1.0f) return 1.0f;
    return value;
}

__host__ __device__ float3 Vec(float x, float y, float z) noexcept {
    float3 out{x, y, z};
    return out;
}

__host__ __device__ float Dot(float3 a, float3 b) noexcept {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

__host__ __device__ float3 Cross(float3 a, float3 b) noexcept {
    return Vec(a.y * b.z - a.z * b.y,
               a.z * b.x - a.x * b.z,
               a.x * b.y - a.y * b.x);
}

__host__ __device__ float3 Normalize(float3 v) noexcept {
    const float n2 = Dot(v, v);
    if (!(n2 > 0.0f)) return Vec(0.0f, 0.0f, 1.0f);
    const float inv = 1.0f / sqrtf(n2);
    return Vec(v.x * inv, v.y * inv, v.z * inv);
}

__host__ __device__ void OrthonormalBasis(float3 dir, float3& u, float3& v) noexcept {
    const float3 ref = fabsf(dir.z) < 0.9f ? Vec(0.0f, 0.0f, 1.0f)
                                           : Vec(1.0f, 0.0f, 0.0f);
    u = Normalize(Cross(ref, dir));
    v = Normalize(Cross(dir, u));
}

__device__ float SafeUniform(curandState* rng) noexcept {
    return rng ? fminf(fmaxf(curand_uniform(rng), 1.0e-7f), 0.99999994f) : 0.5f;
}

__device__ void SampleIsotropicCenterOfMass(
    curandState* rng,
    float& cos_theta_cm,
    float& phi_rad) noexcept {
    cos_theta_cm = rng ? (2.0f * SafeUniform(rng) - 1.0f) : 0.0f;
    phi_rad = rng ? (2.0f * PI * SafeUniform(rng)) : 0.0f;
}

__global__ void NeutronStepKernel(
    TrackSOA tracks,
    curandState* rng,
    const MaterialData* materials,
    int n_tracks) {
    (void)materials;
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_tracks || i >= tracks.size || tracks.status[i] != 0) return;
    if (tracks.pdg[i] != NEUTRON_PDG) return;

    curandState local_rng{};
    curandState* local_rng_ptr = nullptr;
    if (rng) {
        local_rng = rng[i];
        local_rng_ptr = &local_rng;
    }

    float cos_theta_cm = 0.0f;
    float phi_rad = 0.0f;
    SampleIsotropicCenterOfMass(local_rng_ptr, cos_theta_cm, phi_rad);

    const float3 dir = NeutronElasticScatterDirection(
        tracks.dx[i], tracks.dy[i], tracks.dz[i], cos_theta_cm, phi_rad);
    tracks.dx[i] = dir.x;
    tracks.dy[i] = dir.y;
    tracks.dz[i] = dir.z;

    // First scaffold deliberately preserves the neutron kinetic-energy field.
    // TODO Phase N: replace forced elastic scattering with material-dependent
    // cross-section tables and mean-free-path sampling.
    // OPEN: target isotope selection from MaterialData/composition tables.
    // OPEN: thermal scattering kernels for low-energy moderator materials.
    // OPEN: inelastic channels and capture/fission process competition.
    // OPEN: secondary recoil bookkeeping once TrackSOA has an appendable
    // secondary-particle pool.
    tracks.ekin[i] = tracks.ekin[i];

    if (rng) rng[i] = local_rng;
}

}  // namespace

__host__ __device__ float3 NeutronElasticScatterDirection(
    float incident_dx,
    float incident_dy,
    float incident_dz,
    float cos_theta_cm,
    float phi_rad) noexcept {
    float3 dir = Normalize(Vec(incident_dx, incident_dy, incident_dz));
    float3 u_axis;
    float3 v_axis;
    OrthonormalBasis(dir, u_axis, v_axis);

    const float c = ClampUnit(cos_theta_cm);
    const float s = sqrtf(fmaxf(0.0f, 1.0f - c * c));
    return Normalize(Vec(c * dir.x + s * (cosf(phi_rad) * u_axis.x + sinf(phi_rad) * v_axis.x),
                         c * dir.y + s * (cosf(phi_rad) * u_axis.y + sinf(phi_rad) * v_axis.y),
                         c * dir.z + s * (cosf(phi_rad) * u_axis.z + sinf(phi_rad) * v_axis.z)));
}

const char* NeutronStepKernelScaffoldNotice() noexcept {
    return "scaffold only: no Geant4 neutron parity claim and no speed claim";
}

void LaunchNeutronStepKernel(
    TrackSOA* d_tracks,
    curandState* d_rng,
    const MaterialData* d_mats,
    int n_tracks,
    cudaStream_t stream) {
    if (!d_tracks || n_tracks <= 0) return;
    const int blocks = (n_tracks + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    NeutronStepKernel<<<blocks, THREADS_PER_BLOCK, 0, stream>>>(
        *d_tracks, d_rng, d_mats, n_tracks);
    CheckCuda(cudaGetLastError(), "NeutronStepKernel launch");
}

}  // namespace g4gpu
