#pragma once

#include "g4gpu/G4GPUGeometry.hh"

class G4VPhysicalVolume;

namespace g4gpu {

class VoxelGeometry : public G4GPUGeometry {
public:
    VoxelGeometry() = default;
    ~VoxelGeometry() override = default;

    void Build(G4VPhysicalVolume* world, float voxel_mm);
    float DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) override;

    float voxelSizeMm() const noexcept { return voxel_mm_; }
    bool built() const noexcept { return built_; }

private:
    G4VPhysicalVolume* world_ = nullptr;
    float voxel_mm_ = 0.0f;
    bool built_ = false;
};

}  // namespace g4gpu
