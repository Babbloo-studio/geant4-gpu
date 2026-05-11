#include "g4gpu/BranchlessSolids.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386) || defined(_M_IX86)
#  include <immintrin.h>
#  define G4GPU_SOLIDS_X86 1
#endif

namespace g4gpu {
namespace {

constexpr float kEps = 1.0e-8f;
constexpr float kInf = std::numeric_limits<float>::infinity();

bool Disabled() noexcept { return std::getenv("G4GPU_SOLIDS_DISABLE_BRANCHLESS") != nullptr; }

bool InsideBox(const BoxSolid& b, float x, float y, float z) noexcept {
    return std::abs(x) <= b.hx && std::abs(y) <= b.hy && std::abs(z) <= b.hz;
}

float SafeDir(float d) noexcept {
    const float mag = std::max(std::abs(d), kEps);
    return std::copysign(mag, d == 0.0f ? 1.0f : d);
}

void SlabReference(float p, float d, float h, float& tmin, float& tmax, bool& ok) noexcept {
    if (std::abs(d) < kEps) {
        ok = ok && std::abs(p) <= h;
        return;
    }
    const float inv = 1.0f / d;
    const float a = (-h - p) * inv;
    const float b = ( h - p) * inv;
    tmin = std::max(tmin, std::min(a, b));
    tmax = std::min(tmax, std::max(a, b));
}

float BoxInSlabBranchless(const BoxSolid& box,
                          float x, float y, float z,
                          float dx, float dy, float dz) noexcept {
    const float inv_x = 1.0f / SafeDir(dx);
    const float inv_y = 1.0f / SafeDir(dy);
    const float inv_z = 1.0f / SafeDir(dz);
    const float tx1 = (-box.hx - x) * inv_x;
    const float tx2 = ( box.hx - x) * inv_x;
    const float ty1 = (-box.hy - y) * inv_y;
    const float ty2 = ( box.hy - y) * inv_y;
    const float tz1 = (-box.hz - z) * inv_z;
    const float tz2 = ( box.hz - z) * inv_z;
    const float tmin = std::max({std::min(tx1, tx2), std::min(ty1, ty2), std::min(tz1, tz2)});
    const float tmax = std::min({std::max(tx1, tx2), std::max(ty1, ty2), std::max(tz1, tz2)});
    const float dist = std::max(tmin, 0.0f);
    const bool parallel_outside =
        (std::abs(dx) < kEps && std::abs(x) > box.hx) ||
        (std::abs(dy) < kEps && std::abs(y) > box.hy) ||
        (std::abs(dz) < kEps && std::abs(z) > box.hz);
    return (!parallel_outside && tmax >= dist) ? dist : kInf;
}

float BoxOutSlabBranchless(const BoxSolid& box,
                           float x, float y, float z,
                           float dx, float dy, float dz) noexcept {
    const float inv_x = 1.0f / SafeDir(dx);
    const float inv_y = 1.0f / SafeDir(dy);
    const float inv_z = 1.0f / SafeDir(dz);
    const float tx = ((dx >= 0.0f ? box.hx : -box.hx) - x) * inv_x;
    const float ty = ((dy >= 0.0f ? box.hy : -box.hy) - y) * inv_y;
    const float tz = ((dz >= 0.0f ? box.hz : -box.hz) - z) * inv_z;
    return std::max(0.0f, std::min({tx, ty, tz}));
}

float PositiveOrInf(float t) noexcept { return t >= 0.0f && std::isfinite(t) ? t : kInf; }

float SlabEntry(float p, float d, float h) noexcept {
    if (std::abs(d) < kEps) return std::abs(p) <= h ? 0.0f : kInf;
    const float inv = 1.0f / d;
    return std::min((-h - p) * inv, (h - p) * inv);
}

float SlabExit(float p, float d, float h) noexcept {
    if (std::abs(d) < kEps) return std::abs(p) <= h ? kInf : -kInf;
    const float inv = 1.0f / d;
    return std::max((-h - p) * inv, (h - p) * inv);
}

float TubsOuterEntry(float r, float b, float a, float rmax) noexcept {
    const float c = r * r - rmax * rmax;
    if (a < kEps) return c <= 0.0f ? 0.0f : kInf;
    const float disc = b * b - a * c;
    if (disc < 0.0f) return kInf;
    return PositiveOrInf((-b - std::sqrt(disc)) / a);
}

float TubsOuterExit(float r, float b, float a, float rmax) noexcept {
    const float c = r * r - rmax * rmax;
    if (a < kEps) return c <= 0.0f ? kInf : -kInf;
    const float disc = b * b - a * c;
    if (disc < 0.0f) return -kInf;
    return (-b + std::sqrt(disc)) / a;
}

float TubsInnerExit(float r, float b, float a, float rmin) noexcept {
    if (rmin <= 0.0f || r >= rmin) return 0.0f;
    if (a < kEps) return kInf;
    const float c = r * r - rmin * rmin;
    const float disc = b * b - a * c;
    if (disc < 0.0f) return kInf;
    return PositiveOrInf((-b + std::sqrt(disc)) / a);
}

#if defined(G4GPU_SOLIDS_X86) && defined(__GNUC__)
__attribute__((target("avx2")))
void DistanceToInBoxBatchAVX2(const BoxSolid& box,
                              const float* x,
                              const float* y,
                              const float* z,
                              const float* dx,
                              const float* dy,
                              const float* dz,
                              float* out,
                              std::size_t count) noexcept {
    const __m256 zero = _mm256_setzero_ps();
    const __m256 eps = _mm256_set1_ps(kEps);
    const __m256 inf = _mm256_set1_ps(kInf);
    const __m256 sign = _mm256_set1_ps(-0.0f);
    const __m256 hx = _mm256_set1_ps(box.hx);
    const __m256 hy = _mm256_set1_ps(box.hy);
    const __m256 hz = _mm256_set1_ps(box.hz);
    const __m256 nhx = _mm256_sub_ps(zero, hx);
    const __m256 nhy = _mm256_sub_ps(zero, hy);
    const __m256 nhz = _mm256_sub_ps(zero, hz);
    const __m256 one = _mm256_set1_ps(1.0f);
    std::size_t i = 0;
    for (; i + 8 <= count; i += 8) {
        const __m256 px = _mm256_loadu_ps(x + i);
        const __m256 py = _mm256_loadu_ps(y + i);
        const __m256 pz = _mm256_loadu_ps(z + i);
        const __m256 vx = _mm256_loadu_ps(dx + i);
        const __m256 vy = _mm256_loadu_ps(dy + i);
        const __m256 vz = _mm256_loadu_ps(dz + i);
        const __m256 ax = _mm256_max_ps(_mm256_andnot_ps(sign, vx), eps);
        const __m256 ay = _mm256_max_ps(_mm256_andnot_ps(sign, vy), eps);
        const __m256 az = _mm256_max_ps(_mm256_andnot_ps(sign, vz), eps);
        const __m256 sx = _mm256_or_ps(ax, _mm256_and_ps(vx, sign));
        const __m256 sy = _mm256_or_ps(ay, _mm256_and_ps(vy, sign));
        const __m256 sz = _mm256_or_ps(az, _mm256_and_ps(vz, sign));
        const __m256 invx = _mm256_div_ps(one, sx);
        const __m256 invy = _mm256_div_ps(one, sy);
        const __m256 invz = _mm256_div_ps(one, sz);
        const __m256 tx1 = _mm256_mul_ps(_mm256_sub_ps(nhx, px), invx);
        const __m256 tx2 = _mm256_mul_ps(_mm256_sub_ps(hx, px), invx);
        const __m256 ty1 = _mm256_mul_ps(_mm256_sub_ps(nhy, py), invy);
        const __m256 ty2 = _mm256_mul_ps(_mm256_sub_ps(hy, py), invy);
        const __m256 tz1 = _mm256_mul_ps(_mm256_sub_ps(nhz, pz), invz);
        const __m256 tz2 = _mm256_mul_ps(_mm256_sub_ps(hz, pz), invz);
        const __m256 tmin = _mm256_max_ps(_mm256_max_ps(_mm256_min_ps(tx1, tx2),
                                                       _mm256_min_ps(ty1, ty2)),
                                         _mm256_min_ps(tz1, tz2));
        const __m256 tmax = _mm256_min_ps(_mm256_min_ps(_mm256_max_ps(tx1, tx2),
                                                       _mm256_max_ps(ty1, ty2)),
                                         _mm256_max_ps(tz1, tz2));
        const __m256 dist = _mm256_max_ps(tmin, zero);
        const __m256 valid = _mm256_cmp_ps(tmax, dist, _CMP_GE_OQ);
        _mm256_storeu_ps(out + i, _mm256_blendv_ps(inf, dist, valid));
    }
    for (; i < count; ++i) {
        out[i] = DistanceToInBoxBranchless(box, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
    }
}
#endif

}  // namespace

float DistanceToInBoxReference(const BoxSolid& box,
                               float x, float y, float z,
                               float dx, float dy, float dz) noexcept {
    if (InsideBox(box, x, y, z)) return 0.0f;
    float tmin = -kInf;
    float tmax = kInf;
    bool ok = true;
    SlabReference(x, dx, box.hx, tmin, tmax, ok);
    SlabReference(y, dy, box.hy, tmin, tmax, ok);
    SlabReference(z, dz, box.hz, tmin, tmax, ok);
    if (!ok) return kInf;
    const float dist = std::max(tmin, 0.0f);
    return tmax >= dist ? dist : kInf;
}

float DistanceToOutBoxReference(const BoxSolid& box,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept {
    if (!InsideBox(box, x, y, z)) return 0.0f;
    float out = kInf;
    if (std::abs(dx) >= kEps) out = std::min(out, (((dx > 0.0f) ? box.hx : -box.hx) - x) / dx);
    if (std::abs(dy) >= kEps) out = std::min(out, (((dy > 0.0f) ? box.hy : -box.hy) - y) / dy);
    if (std::abs(dz) >= kEps) out = std::min(out, (((dz > 0.0f) ? box.hz : -box.hz) - z) / dz);
    return std::max(0.0f, out);
}

float DistanceToInBoxBranchless(const BoxSolid& box,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept {
    return InsideBox(box, x, y, z) ? 0.0f : BoxInSlabBranchless(box, x, y, z, dx, dy, dz);
}

float DistanceToOutBoxBranchless(const BoxSolid& box,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept {
    return InsideBox(box, x, y, z) ? BoxOutSlabBranchless(box, x, y, z, dx, dy, dz) : 0.0f;
}

float DistanceToInTubsReference(const TubsSolid& tubs,
                                float x, float y, float z,
                                float dx, float dy, float dz) noexcept {
    const float r2 = x * x + y * y;
    if (r2 >= tubs.rmin * tubs.rmin && r2 <= tubs.rmax * tubs.rmax && std::abs(z) <= tubs.hz) return 0.0f;
    const float r = std::sqrt(r2);
    const float a = dx * dx + dy * dy;
    const float b = x * dx + y * dy;
    const float t_rad_in = TubsOuterEntry(r, b, a, tubs.rmax);
    const float t_hole_out = TubsInnerExit(r, b, a, tubs.rmin);
    const float t_z_in = SlabEntry(z, dz, tubs.hz);
    const float t_enter = std::max({t_rad_in, t_hole_out, t_z_in, 0.0f});
    const float t_exit = std::min(TubsOuterExit(r, b, a, tubs.rmax), SlabExit(z, dz, tubs.hz));
    return t_exit >= t_enter ? t_enter : kInf;
}

float DistanceToOutTubsReference(const TubsSolid& tubs,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept {
    const float r2 = x * x + y * y;
    if (r2 < tubs.rmin * tubs.rmin || r2 > tubs.rmax * tubs.rmax || std::abs(z) > tubs.hz) return 0.0f;
    const float r = std::sqrt(r2);
    const float a = dx * dx + dy * dy;
    const float b = x * dx + y * dy;
    float out = std::min(TubsOuterExit(r, b, a, tubs.rmax), SlabExit(z, dz, tubs.hz));
    if (tubs.rmin > 0.0f) {
        const float c = r * r - tubs.rmin * tubs.rmin;
        const float disc = b * b - a * c;
        if (a >= kEps && disc >= 0.0f) out = std::min(out, PositiveOrInf((-b - std::sqrt(disc)) / a));
    }
    return std::max(0.0f, out);
}

float DistanceToInTubsBranchless(const TubsSolid& tubs,
                                 float x, float y, float z,
                                 float dx, float dy, float dz) noexcept {
    return DistanceToInTubsReference(tubs, x, y, z, dx, dy, dz);
}

float DistanceToOutTubsBranchless(const TubsSolid& tubs,
                                  float x, float y, float z,
                                  float dx, float dy, float dz) noexcept {
    return DistanceToOutTubsReference(tubs, x, y, z, dx, dy, dz);
}

void DistanceToInBoxBatch(const BoxSolid& box,
                          const float* x,
                          const float* y,
                          const float* z,
                          const float* dx,
                          const float* dy,
                          const float* dz,
                          float* out,
                          std::size_t count) noexcept {
    if (!x || !y || !z || !dx || !dy || !dz || !out) return;
    if (Disabled()) {
        for (std::size_t i = 0; i < count; ++i) {
            out[i] = DistanceToInBoxReference(box, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
        }
        return;
    }
#if defined(G4GPU_SOLIDS_X86) && defined(__GNUC__)
    __builtin_cpu_init();
    if (__builtin_cpu_supports("avx2")) {
        DistanceToInBoxBatchAVX2(box, x, y, z, dx, dy, dz, out, count);
        return;
    }
#endif
    for (std::size_t i = 0; i < count; ++i) {
        out[i] = DistanceToInBoxBranchless(box, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
    }
}

const char* BranchlessSolidsBackend() noexcept {
    if (Disabled()) return "reference";
#if defined(G4GPU_SOLIDS_X86) && defined(__GNUC__)
    __builtin_cpu_init();
    if (__builtin_cpu_supports("avx2")) return "avx2-box-branchless";
#endif
    return "scalar-branchless";
}

}  // namespace g4gpu
