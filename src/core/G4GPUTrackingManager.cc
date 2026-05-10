#include "g4gpu/G4GPUTrackingManager.hh"

#include <stdexcept>

#include "g4gpu/G4GPUHitBuffer.hh"
#include "g4gpu/MuonStepKernel.hh"

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
    bool has_muon = false;
    for (int i = 0; i < n; ++i) {
        const int pdg = track_buffer_->host().pdg[i];
        has_muon = has_muon || pdg == 13 || pdg == -13;
    }
    if (!has_muon) return;

#if defined(G4GPU_WITH_MUON)
    curandState* d_rng = AllocateRNGStates(n);
    UploadDefaultMaterials();
    LaunchInitRNGKernel(d_rng, n, 0x4d554f4eULL);
    LaunchMuonStepKernel(&track_buffer_->device(), d_rng, nullptr, n);
    FreeRNGStates(d_rng);
#else
    throw std::runtime_error("G4GPU muon tracks require G4GPU_WITH_MUON=ON");
#endif
}

void G4GPUTrackingManager::InjectSecondaries_() {
    // Phase 0 only proves the batch transfer path; no GPU secondaries are produced yet.
}

}  // namespace g4gpu
