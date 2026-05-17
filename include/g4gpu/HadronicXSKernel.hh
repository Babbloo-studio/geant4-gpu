#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"

namespace g4gpu {

struct HadronicXSTarget {
    int z = 1;
    int a = 1;
};

/// Upload the compact nucleon-nucleon cross-section surrogate used by the
/// GPU optical-limit Glauber evaluator. Safe to call more than once.
void InitializeHadronicXS(cudaStream_t stream = nullptr);

/// Launch the GPU batch evaluator.
///
/// `d_tracks` is the host TrackSOA descriptor whose members are device arrays.
/// `d_targets` is a device array of material-index to (Z,A) targets; when only
/// one target is supplied it is used for every track. Cross-sections are written
/// in millibarn. The function synchronizes `stream` before returning so callers
/// can immediately copy `d_xs_out` for deterministic validation.
void EvaluateHadronicXSBatch(
    const TrackSOA* d_tracks,
    int n_tracks,
    const HadronicXSTarget* d_targets,
    int n_targets,
    float* d_xs_out,
    cudaStream_t stream = nullptr
);

class G4GPUHadronicXS {
public:
    static void Initialize(cudaStream_t stream = nullptr) {
        InitializeHadronicXS(stream);
    }

    static void EvaluateBatch(
        const TrackSOA* d_tracks,
        int n_tracks,
        const HadronicXSTarget* d_targets,
        int n_targets,
        float* d_xs_out,
        cudaStream_t stream = nullptr
    ) {
        EvaluateHadronicXSBatch(d_tracks, n_tracks, d_targets, n_targets,
                                d_xs_out, stream);
    }
};

}  // namespace g4gpu
