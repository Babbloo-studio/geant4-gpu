#pragma once

#include <cstddef>

namespace g4gpu {

struct BoxSolid {
    float hx = 1.0f;
    float hy = 1.0f;
    float hz = 1.0f;
};

struct TubsSolid {
    float rmin = 0.0f;
    float rmax = 1.0f;
    float hz = 1.0f;
};

float DistanceToInBoxReference(const BoxSolid& box,
                               float x, float y, float z,
                               float dx, float dy, float dz) noexcept;
float DistanceToOutBoxReference(const BoxSolid& box,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept;
float DistanceToInBoxBranchless(const BoxSolid& box,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept;
float DistanceToOutBoxBranchless(const BoxSolid& box,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept;

float DistanceToInTubsReference(const TubsSolid& tubs,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept;
float DistanceToOutTubsReference(const TubsSolid& tubs,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept;
float DistanceToInTubsBranchless(const TubsSolid& tubs,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept;
float DistanceToOutTubsBranchless(const TubsSolid& tubs,
                                  float x, float y, float z,
                                  float dx, float dy, float dz) noexcept;

void DistanceToInBoxBatch(const BoxSolid& box,
                          const float* x,
                          const float* y,
                          const float* z,
                          const float* dx,
                          const float* dy,
                          const float* dz,
                          float* out,
                          std::size_t count) noexcept;

const char* BranchlessSolidsBackend() noexcept;

}  // namespace g4gpu
