#pragma once

// GPU neutron elastic-scattering scaffold interface.
//
// Contract:
// - TrackSOA fields are in millimetres, MeV, nanoseconds, PDG codes, and status
//   values matching G4GPUTrackBuffer.hh.
// - MaterialData is accepted to preserve the process-kernel launch shape, but
//   isotope/material-dependent neutron physics is intentionally fail-closed.
// - curandState supplies one RNG state per active track when stochastic device
//   scattering is requested; a null RNG uses a deterministic CPU-safe fallback.
// - This scaffold does not invoke Geant4 application code or any production
//   detector data path.

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"
#include "g4gpu/MaterialData.hh"

#if defined(__CUDACC__)
#  include <curand_kernel.h>
#  define G4GPU_NEUTRON_HOST_DEVICE __host__ __device__
#else
struct curandStateXORWOW;
using curandState = curandStateXORWOW;
#  define G4GPU_NEUTRON_HOST_DEVICE
#endif

namespace g4gpu {

// Rotate an incident unit direction by a center-of-mass scattering direction.
// The helper is host/device so deterministic tests can verify the kinematic
// scaffold without requiring a CUDA-capable runtime.
G4GPU_NEUTRON_HOST_DEVICE float3 NeutronElasticScatterDirection(
    float incident_dx,
    float incident_dy,
    float incident_dz,
    float cos_theta_cm,
    float phi_rad) noexcept;

// Explicit scaffold notice used by tests and handoffs: this compact kernel is
// not a Geant4 neutron-physics parity statement and encodes no speed claim.
const char* NeutronStepKernelScaffoldNotice() noexcept;

void LaunchNeutronStepKernel(
    TrackSOA* d_tracks,
    curandState* d_rng,
    const MaterialData* d_mats,
    int n_tracks,
    cudaStream_t stream = nullptr);

}  // namespace g4gpu

#undef G4GPU_NEUTRON_HOST_DEVICE
