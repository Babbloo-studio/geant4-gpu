#include "g4gpu/EMStepKernel.hh"

#include <cstddef>

#include <cuda_runtime.h>
#include <curand_kernel.h>

namespace g4gpu {
namespace {

constexpr float kElectronMassMeV = 0.51099895f;
constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 2.0f * kPi;
constexpr int kThreadsPerBlock = 256;

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

__device__ float Uniform(curandState* rng) {
    if (!rng) return 0.5f;
    return fminf(0.99999994f, fmaxf(1.0e-7f, curand_uniform(rng)));
}

__device__ MaterialData LoadMaterialOrDefault(const MaterialData* materials, int idx) {
    MaterialData mat{};
    if (materials && idx >= 0 && idx < 64) mat = materials[idx];
    return mat;
}

__device__ void OrthonormalBasis(float3 dir, float3& u, float3& v) {
    const float3 ref = fabsf(dir.z) < 0.9f ? Vec(0.0f, 0.0f, 1.0f)
                                           : Vec(1.0f, 0.0f, 0.0f);
    u = Normalize(Cross(ref, dir));
    v = Normalize(Cross(dir, u));
}

__device__ float3 ScatterDirection(float3 dir, float cos_theta,
                                   float sin_theta, float phi) {
    float3 u;
    float3 v;
    OrthonormalBasis(dir, u, v);
    const float cp = cosf(phi);
    const float sp = sinf(phi);
    return Normalize(Vec(cos_theta * dir.x + sin_theta * (cp * u.x + sp * v.x),
                         cos_theta * dir.y + sin_theta * (cp * u.y + sp * v.y),
                         cos_theta * dir.z + sin_theta * (cp * u.z + sp * v.z)));
}

__device__ float SampleKleinNishinaEnergyFraction(float alpha, curandState* rng) {
    alpha = fmaxf(alpha, 1.0e-6f);
    const float epsilon_min = 1.0f / (1.0f + 2.0f * alpha);
    const float epsilon_min2 = epsilon_min * epsilon_min;
    const float branch_log = -logf(epsilon_min);
    const float branch_square = 0.5f * (1.0f - epsilon_min2);
    const float branch_norm = branch_log + branch_square;
    const float branch_cut = branch_norm > 0.0f ? branch_log / branch_norm : 1.0f;

    // Kahn/Butcher-Messel rejection sampler for the Klein-Nishina density.
    // Propose epsilon = E'/E from a two-component majorant on
    // [1/(1+2alpha), 1], then accept with the KN rejection factor.
    for (int attempt = 0; attempt < 10000; ++attempt) {
        float epsilon = 1.0f;
        float epsilon2 = 1.0f;
        if (Uniform(rng) < branch_cut) {
            epsilon = expf(-branch_log * Uniform(rng));
            epsilon2 = epsilon * epsilon;
        } else {
            epsilon2 = epsilon_min2 + (1.0f - epsilon_min2) * Uniform(rng);
            epsilon = sqrtf(epsilon2);
        }

        float one_minus_cos = (1.0f - epsilon) / (epsilon * alpha);
        one_minus_cos = fminf(2.0f, fmaxf(0.0f, one_minus_cos));
        const float sin2 = one_minus_cos * (2.0f - one_minus_cos);
        const float accept = 1.0f - epsilon * sin2 / (1.0f + epsilon2);
        if (Uniform(rng) <= fmaxf(0.0f, accept)) return epsilon;
    }

    // Extremely unlikely fallback: 90-degree Compton scatter.
    return 1.0f / (1.0f + alpha);
}

__global__ void EMStepKernel(TrackSOA tracks, curandState* rng,
                             const MaterialData* materials, int n_tracks) {
    EMStep(tracks, materials, rng, n_tracks);
}

__global__ void ComptonSampleKernel(float incident_energy_mev, curandState* rng,
                                    float* scattered_energy_mev,
                                    float* cos_theta, int n_samples) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_samples) return;

    curandState local_rng{};
    const bool stochastic = rng != nullptr;
    if (stochastic) local_rng = rng[i];

    MaterialData material{};
    EMInteractionResult result{};
    SampleCompton(incident_energy_mev, material,
                  stochastic ? &local_rng : nullptr, result);
    scattered_energy_mev[i] = result.primary_energy_mev;
    cos_theta[i] = result.cos_theta;

    if (stochastic) rng[i] = local_rng;
}

}  // namespace

__device__ void SamplePhotoelectric(float gamma_energy_mev,
                                    const MaterialData& material,
                                    curandState* rng,
                                    EMInteractionResult& out) {
    (void)gamma_energy_mev;
    (void)material;
    (void)rng;
    out = {};
    // TODO Phase 2.EM-photoelectric: tabulate shell cross sections and
    // fluorescence/Auger secondaries per docs/SPEC.md EM kernel contract.
    return;
}

__device__ void SampleCompton(float gamma_energy_mev,
                              const MaterialData& material,
                              curandState* rng,
                              EMInteractionResult& out) {
    (void)material;
    out = {};
    if (gamma_energy_mev <= 0.0f) {
        out.status = 2;
        return;
    }

    const float alpha = gamma_energy_mev / kElectronMassMeV;
    const float epsilon = SampleKleinNishinaEnergyFraction(alpha, rng);
    float one_minus_cos = (1.0f - epsilon) / fmaxf(epsilon * alpha, 1.0e-12f);
    one_minus_cos = fminf(2.0f, fmaxf(0.0f, one_minus_cos));
    const float cos_theta = fminf(1.0f, fmaxf(-1.0f, 1.0f - one_minus_cos));
    const float sin_theta = sqrtf(fmaxf(0.0f, 1.0f - cos_theta * cos_theta));

    out.process = EMProcess::kCompton;
    out.primary_energy_mev = epsilon * gamma_energy_mev;
    out.secondary_energy_mev = fmaxf(0.0f, gamma_energy_mev - out.primary_energy_mev);
    out.cos_theta = cos_theta;
    out.sin_theta = sin_theta;
    out.phi = kTwoPi * Uniform(rng);
    out.secondary_pdg = 11;
    out.status = 0;
}

__device__ void SamplePair(float gamma_energy_mev,
                           const MaterialData& material,
                           curandState* rng,
                           EMInteractionResult& out) {
    (void)gamma_energy_mev;
    (void)material;
    (void)rng;
    out = {};
    // TODO Phase 2.EM-pair: sample nuclear/electron-field pair conversion,
    // e-/e+ energy split, and secondary insertion once a GPU secondary buffer
    // is available in the docs/SPEC.md EM kernel contract.
    return;
}

__device__ void SampleBremsstrahlung(float lepton_energy_mev,
                                     int lepton_pdg,
                                     const MaterialData& material,
                                     curandState* rng,
                                     EMInteractionResult& out) {
    (void)lepton_energy_mev;
    (void)lepton_pdg;
    (void)material;
    (void)rng;
    out = {};
    // TODO Phase 2.EM-bremsstrahlung: sample e-/e+ photon emission from
    // tabulated dσ/dk and emit the photon through the future secondary buffer
    // described by docs/SPEC.md.
    return;
}

__device__ void EMStep(TrackSOA tracks, const MaterialData* materials,
                       curandState* rng, int n_tracks) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_tracks || i >= tracks.size || tracks.status[i] != 0) return;

    curandState local_rng{};
    const bool stochastic = rng != nullptr;
    if (stochastic) local_rng = rng[i];

    const MaterialData material = LoadMaterialOrDefault(materials, tracks.material_idx[i]);
    EMInteractionResult result{};
    const int pdg = tracks.pdg[i];
    if (pdg == 22) {
        SampleCompton(tracks.ekin[i], material,
                      stochastic ? &local_rng : nullptr, result);
        if (result.status == 0 && result.process == EMProcess::kCompton) {
            const float3 dir = Normalize(Vec(tracks.dx[i], tracks.dy[i], tracks.dz[i]));
            const float3 scattered = ScatterDirection(dir, result.cos_theta,
                                                      result.sin_theta, result.phi);
            tracks.dx[i] = scattered.x;
            tracks.dy[i] = scattered.y;
            tracks.dz[i] = scattered.z;
            tracks.ekin[i] = result.primary_energy_mev;
        } else {
            tracks.status[i] = result.status;
        }
    } else if (pdg == 11 || pdg == -11) {
        SampleBremsstrahlung(tracks.ekin[i], pdg, material,
                             stochastic ? &local_rng : nullptr, result);
    }

    if (stochastic) rng[i] = local_rng;
}

void LaunchEMStepKernel(TrackSOA* d_tracks, curandState* d_rng,
                        const MaterialData* d_mats, int n_tracks,
                        cudaStream_t stream) {
    if (!d_tracks || n_tracks <= 0) return;
    const int blocks = (n_tracks + kThreadsPerBlock - 1) / kThreadsPerBlock;
    EMStepKernel<<<blocks, kThreadsPerBlock, 0, stream>>>(*d_tracks, d_rng,
                                                          d_mats, n_tracks);
    CheckCuda(cudaGetLastError(), "EMStepKernel launch");
}

void LaunchComptonSampleKernel(float incident_energy_mev, curandState* d_rng,
                               float* d_scattered_energy_mev,
                               float* d_cos_theta, int n_samples,
                               cudaStream_t stream) {
    if (!d_scattered_energy_mev || !d_cos_theta || n_samples <= 0) return;
    const int blocks = (n_samples + kThreadsPerBlock - 1) / kThreadsPerBlock;
    ComptonSampleKernel<<<blocks, kThreadsPerBlock, 0, stream>>>(
        incident_energy_mev, d_rng, d_scattered_energy_mev, d_cos_theta, n_samples);
    CheckCuda(cudaGetLastError(), "ComptonSampleKernel launch");
}

}  // namespace g4gpu
