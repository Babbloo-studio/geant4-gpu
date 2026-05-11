#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"
#include "g4gpu/MaterialData.hh"

#if defined(__CUDACC__)
#  include <curand_kernel.h>
#  define G4GPU_DEVICE __device__
#else
struct curandStateXORWOW;
using curandState = curandStateXORWOW;
#  define G4GPU_DEVICE
#endif

namespace g4gpu {

/**
 * Electromagnetic single-step GPU interface for e-/e+/gamma tracks.
 *
 * Inputs:
 * - TrackSOA: positions, directions, kinetic energies, PDG codes, material ids,
 *   and status values using the Phase-0 G4GPU SoA contract.
 * - MaterialData*: optional device material table, indexed by TrackSOA::material_idx.
 * - curandState*: one RNG state per track/sample; nullptr selects deterministic
 *   fallback values for compile-only smoke paths.
 * - n_tracks / n_samples: number of active tracks or validation samples.
 *
 * Outputs:
 * - EMStep updates TrackSOA in place. This scaffold performs one Compton scatter
 *   for gamma tracks and leaves photoelectric, pair-production, and charged-lepton
 *   bremsstrahlung as documented no-op stubs for later Phase-2 EM work.
 * - SampleCompton fills EMInteractionResult with scattered-photon energy,
 *   recoil-electron energy, cos(theta), sin(theta), and azimuth phi.
 * - LaunchComptonSampleKernel writes sampled scattered-photon energies and
 *   cos(theta) values for the Klein-Nishina validation test.
 *
 * Device-callable functions below are declared as __device__ when this header is
 * compiled by nvcc; host translation units see inert declarations only.
 */

enum class EMProcess : int {
    kNone = 0,
    kPhotoelectric = 1,
    kCompton = 2,
    kPairProduction = 3,
    kBremsstrahlung = 4,
};

struct EMInteractionResult {
    EMProcess process = EMProcess::kNone;
    float primary_energy_mev = 0.0f;
    float secondary_energy_mev = 0.0f;
    float cos_theta = 1.0f;
    float sin_theta = 0.0f;
    float phi = 0.0f;
    int secondary_pdg = 0;
    int status = 0;
};

G4GPU_DEVICE void SamplePhotoelectric(
    float gamma_energy_mev,
    const MaterialData& material,
    curandState* rng,
    EMInteractionResult& out);

G4GPU_DEVICE void SampleCompton(
    float gamma_energy_mev,
    const MaterialData& material,
    curandState* rng,
    EMInteractionResult& out);

G4GPU_DEVICE void SamplePair(
    float gamma_energy_mev,
    const MaterialData& material,
    curandState* rng,
    EMInteractionResult& out);

G4GPU_DEVICE void SampleBremsstrahlung(
    float lepton_energy_mev,
    int lepton_pdg,
    const MaterialData& material,
    curandState* rng,
    EMInteractionResult& out);

G4GPU_DEVICE void EMStep(
    TrackSOA tracks,
    const MaterialData* materials,
    curandState* rng,
    int n_tracks);

void LaunchEMStepKernel(
    TrackSOA* d_tracks,
    curandState* d_rng,
    const MaterialData* d_mats,
    int n_tracks,
    cudaStream_t stream = nullptr);

void LaunchComptonSampleKernel(
    float incident_energy_mev,
    curandState* d_rng,
    float* d_scattered_energy_mev,
    float* d_cos_theta,
    int n_samples,
    cudaStream_t stream = nullptr);

}  // namespace g4gpu

#undef G4GPU_DEVICE
