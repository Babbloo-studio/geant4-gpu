#pragma once

#include <cstddef>
#include <cstdint>

namespace g4gpu {

struct NavigationGrid {
    int nx = 0;
    int ny = 0;
    int nz = 0;
    const std::uint8_t* material_id = nullptr;
    const std::uint16_t* volume_id = nullptr;
};

struct NavigationRay {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float dx = 0.0f;
    float dy = 0.0f;
    float dz = 1.0f;
};

int WalkTouchableReference(const NavigationGrid& grid,
                           const NavigationRay& ray,
                           int max_steps) noexcept;

int WalkTouchablePrefetch(const NavigationGrid& grid,
                          const NavigationRay& ray,
                          int max_steps) noexcept;

void WalkTouchableBatch(const NavigationGrid& grid,
                        const NavigationRay* rays,
                        int* out,
                        std::size_t count,
                        int max_steps) noexcept;

const char* NavigationPrefetchBackend() noexcept;

}  // namespace g4gpu
