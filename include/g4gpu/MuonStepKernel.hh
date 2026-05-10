#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"
#include "g4gpu/MaterialData.hh"

#if defined(__CUDACC__)
#  include <curand_kernel.h>
#else
struct curandStateXORWOW;
using curandState = curandStateXORWOW;
#endif

namespace g4gpu {

curandState* AllocateRNGStates(int n_states);
void FreeRNGStates(curandState* d_rng);

void LaunchInitRNGKernel(
    curandState* d_rng,
    int n_states,
    unsigned long long seed,
    cudaStream_t stream = nullptr
);

void LaunchMuonStepKernel(
    TrackSOA* d_tracks,
    curandState* d_rng,
    const MaterialData* d_mats,
    int n_tracks,
    cudaStream_t stream = nullptr
);

}  // namespace g4gpu
