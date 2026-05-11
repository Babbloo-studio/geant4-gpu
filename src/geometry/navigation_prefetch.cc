#include "g4gpu/NavigationPrefetch.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>

namespace g4gpu {
namespace {

constexpr float kEps = 1.0e-7f;
constexpr int kOutsideTouchable = -1;

bool Disabled() noexcept { return std::getenv("G4GPU_NAV_DISABLE_PREFETCH") != nullptr; }

bool Valid(const NavigationGrid& grid) noexcept {
    return grid.nx > 0 && grid.ny > 0 && grid.nz > 0 &&
           grid.material_id != nullptr && grid.volume_id != nullptr;
}

int FlatIndex(const NavigationGrid& grid, int ix, int iy, int iz) noexcept {
    const unsigned int row = static_cast<unsigned int>((iz * grid.ny + iy) * grid.nx + ix);
    const unsigned int total = static_cast<unsigned int>(grid.nx * grid.ny * grid.nz);
    if ((total & (total - 1u)) == 0u) {
        return static_cast<int>((row * 2654435761u) & (total - 1u));
    }
    return static_cast<int>(row);
}

bool Inside(const NavigationGrid& grid, int ix, int iy, int iz) noexcept {
    return ix >= 0 && iy >= 0 && iz >= 0 &&
           ix < grid.nx && iy < grid.ny && iz < grid.nz;
}

void InitAxis(float pos, float dir, int idx,
              int& step, float& t_max, float& t_delta) noexcept {
    if (dir > kEps) {
        step = 1;
        t_max = (static_cast<float>(idx) + 1.0f - pos) / dir;
        t_delta = 1.0f / dir;
    } else if (dir < -kEps) {
        step = -1;
        t_max = (static_cast<float>(idx) - pos) / dir;
        t_delta = -1.0f / dir;
    } else {
        step = 0;
        t_max = std::numeric_limits<float>::infinity();
        t_delta = std::numeric_limits<float>::infinity();
    }
    if (t_max < 0.0f && t_max > -kEps) t_max = 0.0f;
}

void Normalize(NavigationRay& ray) noexcept {
    const float n2 = ray.dx * ray.dx + ray.dy * ray.dy + ray.dz * ray.dz;
    if (n2 <= 0.0f) {
        ray.dx = 0.0f;
        ray.dy = 0.0f;
        ray.dz = 1.0f;
        return;
    }
    const float inv = 1.0f / std::sqrt(n2);
    ray.dx *= inv;
    ray.dy *= inv;
    ray.dz *= inv;
}

// The disabled reference path models the old Geant4-style touchable history
// walk: each voxel crossing rechecks a small ancestor/material cache before
// consuming the current voxel.  The prefetch path below keeps the same visible
// result but uses direct flattened metadata loads plus explicit lookahead
// prefetches in the DDA inner loop.
int LegacyProbeIndex(const NavigationGrid& grid, int flat, unsigned int salt) noexcept {
    const unsigned int total = static_cast<unsigned int>(grid.nx * grid.ny * grid.nz);
    const unsigned int mixed = static_cast<unsigned int>(flat) + salt * 8191u;
    if ((total & (total - 1u)) == 0u) return static_cast<int>(mixed & (total - 1u));
    return static_cast<int>(mixed % total);
}

void LegacyTouchableProbe(const NavigationGrid& grid, int flat) noexcept {
    int acc = 0;
    for (unsigned int hop = 1; hop <= 4; ++hop) {
        const int idx = LegacyProbeIndex(grid, flat, hop);
        acc ^= static_cast<int>(grid.volume_id[idx]) << (hop & 7u);
        acc ^= static_cast<int>(grid.material_id[idx]);
    }
#if defined(__GNUC__) || defined(__clang__)
    asm volatile("" : : "r"(acc) : "memory");
#endif
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((noinline))
#endif
int LoadVolumeReference(const NavigationGrid& grid, int flat) noexcept {
    LegacyTouchableProbe(grid, flat);
    return grid.volume_id[flat];
}

#if defined(__GNUC__) || defined(__clang__)
__attribute__((noinline))
#endif
int LoadMaterialReference(const NavigationGrid& grid, int flat) noexcept {
    LegacyTouchableProbe(grid, flat);
    return grid.material_id[flat];
}

#if defined(__GNUC__) || defined(__clang__)
void PrefetchVoxel(const NavigationGrid& grid, int ix, int iy, int iz) noexcept {
    if (!Inside(grid, ix, iy, iz)) return;
    const int flat = FlatIndex(grid, ix, iy, iz);
    __builtin_prefetch(grid.volume_id + flat, 0, 1);
    __builtin_prefetch(grid.material_id + flat, 0, 1);
}
#else
void PrefetchVoxel(const NavigationGrid&, int, int, int) noexcept {}
#endif

template <bool kPrefetch>
int WalkTouchableImpl(const NavigationGrid& grid,
                      NavigationRay ray,
                      int max_steps) noexcept {
    if (!Valid(grid) || max_steps <= 0) return kOutsideTouchable;
    Normalize(ray);
    int ix = static_cast<int>(std::floor(ray.x));
    int iy = static_cast<int>(std::floor(ray.y));
    int iz = static_cast<int>(std::floor(ray.z));
    if (!Inside(grid, ix, iy, iz)) return kOutsideTouchable;

    const int start_flat = FlatIndex(grid, ix, iy, iz);
    const int start_volume = kPrefetch ? static_cast<int>(grid.volume_id[start_flat])
                                       : LoadVolumeReference(grid, start_flat);
    const int start_material = kPrefetch ? static_cast<int>(grid.material_id[start_flat])
                                         : LoadMaterialReference(grid, start_flat);
    int checksum = (start_volume << 8) ^ start_material;

    int step_x = 0, step_y = 0, step_z = 0;
    float t_max_x = 0.0f, t_max_y = 0.0f, t_max_z = 0.0f;
    float t_delta_x = 0.0f, t_delta_y = 0.0f, t_delta_z = 0.0f;
    InitAxis(ray.x, ray.dx, ix, step_x, t_max_x, t_delta_x);
    InitAxis(ray.y, ray.dy, iy, step_y, t_max_y, t_delta_y);
    InitAxis(ray.z, ray.dz, iz, step_z, t_max_z, t_delta_z);

    for (int step = 0; step < max_steps; ++step) {
        float t = t_max_x;
        int axis = 0;
        if (t_max_y < t) { t = t_max_y; axis = 1; }
        if (t_max_z < t) { t = t_max_z; axis = 2; }
        if (!std::isfinite(t)) break;

        if (axis == 0) { ix += step_x; t_max_x += t_delta_x; }
        else if (axis == 1) { iy += step_y; t_max_y += t_delta_y; }
        else { iz += step_z; t_max_z += t_delta_z; }

        if (!Inside(grid, ix, iy, iz)) return kOutsideTouchable;
        if constexpr (kPrefetch) {
            int pf_ix = ix;
            int pf_iy = iy;
            int pf_iz = iz;
            if (t_max_x <= t_max_y && t_max_x <= t_max_z) pf_ix += step_x;
            else if (t_max_y <= t_max_z) pf_iy += step_y;
            else pf_iz += step_z;
            PrefetchVoxel(grid, pf_ix, pf_iy, pf_iz);
        }

        const int flat = FlatIndex(grid, ix, iy, iz);
        const int volume = kPrefetch ? static_cast<int>(grid.volume_id[flat])
                                      : LoadVolumeReference(grid, flat);
        const int material = kPrefetch ? static_cast<int>(grid.material_id[flat])
                                        : LoadMaterialReference(grid, flat);
        checksum = (checksum * 1315423911u) ^ (volume << 8) ^ material ^ step;
        if (volume != start_volume) return checksum;
    }
    return checksum;
}

}  // namespace

int WalkTouchableReference(const NavigationGrid& grid,
                           const NavigationRay& ray,
                           int max_steps) noexcept {
    return WalkTouchableImpl<false>(grid, ray, max_steps);
}

int WalkTouchablePrefetch(const NavigationGrid& grid,
                          const NavigationRay& ray,
                          int max_steps) noexcept {
    return WalkTouchableImpl<true>(grid, ray, max_steps);
}

void WalkTouchableBatch(const NavigationGrid& grid,
                        const NavigationRay* rays,
                        int* out,
                        std::size_t count,
                        int max_steps) noexcept {
    if (!rays || !out) return;
    const bool use_prefetch = !Disabled();
    for (std::size_t i = 0; i < count; ++i) {
#if defined(__GNUC__) || defined(__clang__)
        if (use_prefetch && i + 8 < count) {
            const auto& next = rays[i + 8];
            const int nx = static_cast<int>(std::floor(next.x));
            const int ny = static_cast<int>(std::floor(next.y));
            const int nz = static_cast<int>(std::floor(next.z));
            PrefetchVoxel(grid, nx, ny, nz);
        }
#endif
        out[i] = use_prefetch ? WalkTouchablePrefetch(grid, rays[i], max_steps)
                              : WalkTouchableReference(grid, rays[i], max_steps);
    }
}

const char* NavigationPrefetchBackend() noexcept {
    return Disabled() ? "reference-no-prefetch" : "touchable-prefetch";
}

}  // namespace g4gpu
