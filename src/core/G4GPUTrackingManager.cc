#include "g4gpu/G4GPUTrackingManager.hh"

#include <stdexcept>

#include "g4gpu/G4GPUHitBuffer.hh"

#if defined(G4GPU_HAVE_GEANT4)
#  include "G4ParticleDefinition.hh"
#  include "G4Track.hh"
#endif

namespace g4gpu {

G4GPUTrackingManager::G4GPUTrackingManager()
    : G4GPUTrackingManager(65536) {}

G4GPUTrackingManager::G4GPUTrackingManager(int batch_size)
    : batch_size_(batch_size) {
    if (batch_size_ <= 0) {
        throw std::invalid_argument("G4GPUTrackingManager batch size must be positive");
    }
    track_buffer_ = std::make_unique<G4GPUTrackBuffer>(batch_size_);
}

void G4GPUTrackingManager::HandOverOneTrack(G4Track* track) {
    if (!track) return;

    if (track_buffer_->full()) {
        FlushEvent();
    }

    track_buffer_->append(*track);
    pending_tracks_.push_back(track);

    if (track_buffer_->full()) {
        FlushEvent();
    }
}

void G4GPUTrackingManager::FlushEvent() {
    if (!track_buffer_ || track_buffer_->empty()) return;

    track_buffer_->copyHostToDevice();
    LaunchKernels_();
#if G4GPU_HAS_CUDA_RUNTIME
    CheckCuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize");
#else
    CheckCuda(cudaSuccess, "cudaDeviceSynchronize");
#endif
    track_buffer_->copyDeviceToHost();


    InjectSecondaries_();
    pending_tracks_.clear();
    track_buffer_->clear();
}

void G4GPUTrackingManager::BuildPhysicsTable(const G4ParticleDefinition& pd) {
    (void)pd;
}

void G4GPUTrackingManager::SetBatchSize(int n) {
    if (n <= 0) {
        throw std::invalid_argument("G4GPUTrackingManager batch size must be positive");
    }
    if (track_buffer_ && !track_buffer_->empty()) {
        throw std::logic_error("cannot change G4GPU batch size while tracks are buffered");
    }
    batch_size_ = n;
    track_buffer_ = std::make_unique<G4GPUTrackBuffer>(batch_size_);
}

void G4GPUTrackingManager::LaunchKernels_() {
    const int n = track_buffer_->host().size;
    LaunchNullStepKernel(track_buffer_->device().status, n);
}

void G4GPUTrackingManager::InjectSecondaries_() {
    // Phase 0 only proves the batch transfer path; no GPU secondaries are produced yet.
}

}  // namespace g4gpu
