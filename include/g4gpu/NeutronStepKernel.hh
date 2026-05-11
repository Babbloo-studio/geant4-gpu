#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"

#if defined(__CUDACC__)
#  define G4GPU_NEUTRON_HOST_DEVICE __host__ __device__
#else
#  define G4GPU_NEUTRON_HOST_DEVICE
#endif

namespace g4gpu {

// Compact status codes are kept as integers so the helper can be used from
// host and device code without depending on exceptions or CUDA-side RTTI.
enum class NeutronElasticStatus : int {
    ok = 0,
    invalid_target_mass_ratio = 1,
};

struct NeutronElasticResult {
    float incident_energy_mev = 0.0f;
    float target_mass_ratio = 0.0f;
    float cos_theta_cm = 0.0f;
    float energy_fraction = 0.0f;
    float outgoing_energy_mev = 0.0f;
    NeutronElasticStatus status = NeutronElasticStatus::invalid_target_mass_ratio;
};

// Deterministic lab-frame neutron elastic kinematics for a stationary target.
// A is the target-to-neutron mass ratio. cos_theta_cm is clamped to [-1, 1]
// only for numerical safety. Invalid A <= 0 is reported in the result status.
G4GPU_NEUTRON_HOST_DEVICE NeutronElasticResult ComputeNeutronElasticKinematics(
    float incident_energy_mev,
    float target_mass_ratio_A,
    float cos_theta_cm) noexcept;

G4GPU_NEUTRON_HOST_DEVICE float NeutronElasticOutgoingEnergyFraction(
    float target_mass_ratio_A,
    float cos_theta_cm) noexcept;

// Explicit scaffold notice used by tests and handoffs: this compact kernel is
// not a Geant4 neutron-physics parity statement and encodes no speed claim.
const char* NeutronStepKernelScaffoldNotice() noexcept;

void LaunchNeutronStepKernel(
    TrackSOA* d_tracks,
    int n_tracks,
    float target_mass_ratio_A,
    float cos_theta_cm,
    cudaStream_t stream = nullptr);

}  // namespace g4gpu

#undef G4GPU_NEUTRON_HOST_DEVICE
