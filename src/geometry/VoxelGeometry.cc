#include "VoxelGeometry.hh"

#include <limits>

namespace g4gpu {

void VoxelGeometry::Build(G4VPhysicalVolume* world, float voxel_mm) {
    (void)world;
    (void)voxel_mm;
}

float VoxelGeometry::DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) {
    (void)pos;
    (void)dir;
    next_vol = -1;
    return std::numeric_limits<float>::infinity();
}

}  // namespace g4gpu
