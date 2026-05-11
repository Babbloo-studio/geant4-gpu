#pragma once

#include <cstddef>

namespace g4gpu {

struct UniformCrossSectionTable {
    const float* values = nullptr;
    std::size_t size = 0;
    float energy_min = 0.0f;
    float energy_step = 1.0f;
};

float InterpolateCrossSectionScalar(const UniformCrossSectionTable& table,
                                    float energy) noexcept;

void InterpolateCrossSectionBatchScalar(const UniformCrossSectionTable& table,
                                        const float* energies,
                                        float* out,
                                        std::size_t count) noexcept;

void InterpolateCrossSectionBatch(const UniformCrossSectionTable& table,
                                  const float* energies,
                                  float* out,
                                  std::size_t count) noexcept;

const char* CrossSectionInterpolatorBackend() noexcept;

}  // namespace g4gpu
