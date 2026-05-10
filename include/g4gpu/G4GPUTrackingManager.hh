#pragma once

#include <memory>
#include <vector>

#include "g4gpu/G4GPUGeometry.hh"
#include "g4gpu/G4GPUTrackBuffer.hh"

#if defined(G4GPU_HAVE_GEANT4)
#  include "G4VTrackingManager.hh"
class G4ParticleDefinition;
class G4Track;
#else
class G4ParticleDefinition {};
class G4Track {};
class G4VTrackingManager {
public:
    virtual ~G4VTrackingManager() = default;
    virtual void BuildPhysicsTable(const G4ParticleDefinition&) {}
    virtual void PreparePhysicsTable(const G4ParticleDefinition&) {}
    virtual void HandOverOneTrack(G4Track*) = 0;
    virtual void FlushEvent() {}
};
#endif

namespace g4gpu {

class G4GPUPhysicsTable;

class G4GPUTrackingManager : public G4VTrackingManager {
public:
    G4GPUTrackingManager();
    explicit G4GPUTrackingManager(int batch_size);
    ~G4GPUTrackingManager() override = default;

    void HandOverOneTrack(G4Track* track) override;
    void FlushEvent() override;
    void BuildPhysicsTable(const G4ParticleDefinition& pd) override;

    void SetBatchSize(int n);
    int GetBatchSize() const noexcept { return batch_size_; }

    void SetGeometryBackend(G4GPUGeometry* geometry) noexcept { geometry_ = geometry; }
    void SetPhysicsTable(G4GPUPhysicsTable* tables) noexcept { tables_ = tables; }
    void SetPhysicsKernel(void* kernel) noexcept { physics_kernel_ = kernel; }

    G4GPUTrackBuffer& buffer() noexcept { return *track_buffer_; }
    const G4GPUTrackBuffer& buffer() const noexcept { return *track_buffer_; }

private:
    std::unique_ptr<G4GPUTrackBuffer> track_buffer_;
    std::vector<G4Track*> pending_tracks_;
    G4GPUGeometry* geometry_ = nullptr;
    G4GPUPhysicsTable* tables_ = nullptr;
    void* physics_kernel_ = nullptr;
    int batch_size_ = 65536;

    void LaunchKernels_();
    void InjectSecondaries_();
};

}  // namespace g4gpu
