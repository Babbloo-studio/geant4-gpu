#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"

namespace g4gpu {

class G4GPUGeometry {
public:
    virtual ~G4GPUGeometry() = default;

    virtual float DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) = 0;
};

}  // namespace g4gpu
