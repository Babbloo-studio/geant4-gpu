#include "g4gpu/NeutronStepKernel.hh"

#include <cuda_runtime.h>

namespace g4gpu {
namespace {

constexpr int THREADS_PER_BLOCK = 256;
constexpr int NEUTRON_PDG = 2112;

__host__ __device__ float ClampUnit(float value) noexcept {
    if (!(value >= -1.0f)) return -1.0f;
    if (value > 1.0f) return 1.0f;
    return value;
}

__host__ __device__ float ClampFraction(float value) noexcept {
    if (!(value >= 0.0f)) return 0.0f;
    if (value > 1.0f) return 1.0f;
    return value;
}

__global__ void NeutronStepKernel(
    TrackSOA tracks,
    int n_tracks,
    float target_mass_ratio_A,
    float cos_theta_cm) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_tracks || i >= tracks.size || tracks.status[i] != 0) return;
    if (tracks.pdg[i] != NEUTRON_PDG) return;

    const auto result = ComputeNeutronElasticKinematics(
        tracks.ekin[i], target_mass_ratio_A, cos_theta_cm);
    if (result.status != NeutronElasticStatus::ok) {
        tracks.status[i] = 2;
        return;
    }
    tracks.ekin[i] = result.outgoing_energy_mev;
}

}  // namespace

__host__ __device__ float NeutronElasticOutgoingEnergyFraction(
    float target_mass_ratio_A,
    float cos_theta_cm) noexcept {
    if (!(target_mass_ratio_A > 0.0f)) return 0.0f;
    const float A = target_mass_ratio_A;
    const float c = ClampUnit(cos_theta_cm);
    const float numerator = A * A + 2.0f * A * c + 1.0f;
    const float denominator = (A + 1.0f) * (A + 1.0f);
    return ClampFraction(numerator / denominator);
}

__host__ __device__ NeutronElasticResult ComputeNeutronElasticKinematics(
    float incident_energy_mev,
    float target_mass_ratio_A,
    float cos_theta_cm) noexcept {
    NeutronElasticResult result{};
    result.incident_energy_mev = incident_energy_mev > 0.0f ? incident_energy_mev : 0.0f;
    result.target_mass_ratio = target_mass_ratio_A;
    result.cos_theta_cm = ClampUnit(cos_theta_cm);

    if (!(target_mass_ratio_A > 0.0f)) {
        result.status = NeutronElasticStatus::invalid_target_mass_ratio;
        return result;
    }

    result.status = NeutronElasticStatus::ok;
    result.energy_fraction = NeutronElasticOutgoingEnergyFraction(
        target_mass_ratio_A, result.cos_theta_cm);
    result.outgoing_energy_mev = result.incident_energy_mev * result.energy_fraction;
    return result;
}

const char* NeutronStepKernelScaffoldNotice() noexcept {
    return "scaffold only: no Geant4 neutron parity claim and no speed claim";
}

void LaunchNeutronStepKernel(
    TrackSOA* d_tracks,
    int n_tracks,
    float target_mass_ratio_A,
    float cos_theta_cm,
    cudaStream_t stream) {
    if (!d_tracks || n_tracks <= 0) return;
    const int blocks = (n_tracks + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    NeutronStepKernel<<<blocks, THREADS_PER_BLOCK, 0, stream>>>(
        *d_tracks, n_tracks, target_mass_ratio_A, cos_theta_cm);
    CheckCuda(cudaGetLastError(), "NeutronStepKernel launch");
}

}  // namespace g4gpu
