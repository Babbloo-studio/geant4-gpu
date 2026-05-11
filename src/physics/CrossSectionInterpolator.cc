#include "g4gpu/CrossSectionInterpolator.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386) || defined(_M_IX86)
#  include <immintrin.h>
#  define G4GPU_XS_X86 1
#endif

#if defined(__ARM_NEON) || defined(__ARM_NEON__)
#  include <arm_neon.h>
#  define G4GPU_XS_NEON 1
#endif

namespace g4gpu {
namespace {

bool Valid(const UniformCrossSectionTable& table) noexcept {
    return table.values != nullptr && table.size >= 2 && table.energy_step > 0.0f &&
           std::isfinite(table.energy_min) && std::isfinite(table.energy_step);
}

bool SimdDisabled() noexcept {
    return std::getenv("G4GPU_XS_DISABLE_SIMD") != nullptr;
}

float Position(const UniformCrossSectionTable& table, float energy) noexcept {
    const float x = (energy - table.energy_min) / table.energy_step;
    const float max_index = static_cast<float>(table.size - 1);
    return std::min(std::max(x, 0.0f), max_index);
}

#if defined(G4GPU_XS_X86) && defined(__GNUC__)
__attribute__((target("avx2,fma")))
void InterpolateBatchAVX2(const UniformCrossSectionTable& table,
                          const float* energies,
                          float* out,
                          std::size_t count) noexcept {
    const __m256 min_energy = _mm256_set1_ps(table.energy_min);
    const __m256 inv_step = _mm256_set1_ps(1.0f / table.energy_step);
    const __m256 zero = _mm256_setzero_ps();
    const __m256 max_index = _mm256_set1_ps(static_cast<float>(table.size - 1));
    const __m256i max_i = _mm256_set1_epi32(static_cast<int>(table.size - 2));
    const __m256i one_i = _mm256_set1_epi32(1);
    std::size_t i = 0;
    for (; i + 8 <= count; i += 8) {
        const __m256 e = _mm256_loadu_ps(energies + i);
        __m256 x = _mm256_mul_ps(_mm256_sub_ps(e, min_energy), inv_step);
        x = _mm256_min_ps(_mm256_max_ps(x, zero), max_index);
        __m256i idx = _mm256_cvttps_epi32(x);
        idx = _mm256_min_epi32(idx, max_i);
        const __m256 idx_f = _mm256_cvtepi32_ps(idx);
        const __m256 frac = _mm256_sub_ps(x, idx_f);
        const __m256 v0 = _mm256_i32gather_ps(table.values, idx, 4);
        const __m256 v1 = _mm256_i32gather_ps(table.values, _mm256_add_epi32(idx, one_i), 4);
        const __m256 y = _mm256_fmadd_ps(frac, _mm256_sub_ps(v1, v0), v0);
        _mm256_storeu_ps(out + i, y);
    }
    for (; i < count; ++i) out[i] = InterpolateCrossSectionScalar(table, energies[i]);
}

__attribute__((target("avx512f")))
void InterpolateBatchAVX512(const UniformCrossSectionTable& table,
                            const float* energies,
                            float* out,
                            std::size_t count) noexcept {
    const __m512 min_energy = _mm512_set1_ps(table.energy_min);
    const __m512 inv_step = _mm512_set1_ps(1.0f / table.energy_step);
    const __m512 zero = _mm512_setzero_ps();
    const __m512 max_index = _mm512_set1_ps(static_cast<float>(table.size - 1));
    const __m512i max_i = _mm512_set1_epi32(static_cast<int>(table.size - 2));
    const __m512i one_i = _mm512_set1_epi32(1);
    std::size_t i = 0;
    for (; i + 16 <= count; i += 16) {
        const __m512 e = _mm512_loadu_ps(energies + i);
        __m512 x = _mm512_mul_ps(_mm512_sub_ps(e, min_energy), inv_step);
        x = _mm512_min_ps(_mm512_max_ps(x, zero), max_index);
        __m512i idx = _mm512_cvttps_epi32(x);
        idx = _mm512_min_epi32(idx, max_i);
        const __m512 idx_f = _mm512_cvtepi32_ps(idx);
        const __m512 frac = _mm512_sub_ps(x, idx_f);
        const __m512 v0 = _mm512_i32gather_ps(idx, table.values, 4);
        const __m512 v1 = _mm512_i32gather_ps(_mm512_add_epi32(idx, one_i), table.values, 4);
        const __m512 y = _mm512_fmadd_ps(frac, _mm512_sub_ps(v1, v0), v0);
        _mm512_storeu_ps(out + i, y);
    }
    for (; i < count; ++i) out[i] = InterpolateCrossSectionScalar(table, energies[i]);
}
#endif

#if defined(G4GPU_XS_NEON)
void InterpolateBatchNEON(const UniformCrossSectionTable& table,
                          const float* energies,
                          float* out,
                          std::size_t count) noexcept {
    const float32x4_t min_energy = vdupq_n_f32(table.energy_min);
    const float32x4_t inv_step = vdupq_n_f32(1.0f / table.energy_step);
    const float32x4_t zero = vdupq_n_f32(0.0f);
    const float32x4_t max_index = vdupq_n_f32(static_cast<float>(table.size - 1));
    const int32x4_t max_i = vdupq_n_s32(static_cast<int>(table.size - 2));
    std::size_t i = 0;
    alignas(16) int idx_lane[4];
    alignas(16) float frac_lane[4];
    for (; i + 4 <= count; i += 4) {
        float32x4_t x = vmulq_f32(vsubq_f32(vld1q_f32(energies + i), min_energy), inv_step);
        x = vminq_f32(vmaxq_f32(x, zero), max_index);
        int32x4_t idx = vcvtq_s32_f32(x);
        idx = vminq_s32(idx, max_i);
        const float32x4_t frac = vsubq_f32(x, vcvtq_f32_s32(idx));
        vst1q_s32(idx_lane, idx);
        vst1q_f32(frac_lane, frac);
        for (int lane = 0; lane < 4; ++lane) {
            const int j = idx_lane[lane];
            const float v0 = table.values[j];
            out[i + lane] = v0 + frac_lane[lane] * (table.values[j + 1] - v0);
        }
    }
    for (; i < count; ++i) out[i] = InterpolateCrossSectionScalar(table, energies[i]);
}
#endif

}  // namespace

float InterpolateCrossSectionScalar(const UniformCrossSectionTable& table,
                                    float energy) noexcept {
    if (!Valid(table)) return 0.0f;
    const float x = Position(table, energy);
    std::size_t i = static_cast<std::size_t>(x);
    if (i >= table.size - 1) i = table.size - 2;
    const float frac = x - static_cast<float>(i);
    const float v0 = table.values[i];
    return v0 + frac * (table.values[i + 1] - v0);
}

void InterpolateCrossSectionBatchScalar(const UniformCrossSectionTable& table,
                                        const float* energies,
                                        float* out,
                                        std::size_t count) noexcept {
    if (!energies || !out) return;
    for (std::size_t i = 0; i < count; ++i) {
        out[i] = InterpolateCrossSectionScalar(table, energies[i]);
    }
}

const char* CrossSectionInterpolatorBackend() noexcept {
    if (SimdDisabled()) return "scalar";
#if defined(G4GPU_XS_X86) && defined(__GNUC__)
    __builtin_cpu_init();
    if (__builtin_cpu_supports("avx512f")) return "avx512f";
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma")) return "avx2";
#endif
#if defined(G4GPU_XS_NEON)
    return "neon";
#else
    return "scalar";
#endif
}

void InterpolateCrossSectionBatch(const UniformCrossSectionTable& table,
                                  const float* energies,
                                  float* out,
                                  std::size_t count) noexcept {
    if (!Valid(table) || !energies || !out || count == 0) return;
    if (SimdDisabled()) {
        InterpolateCrossSectionBatchScalar(table, energies, out, count);
        return;
    }
#if defined(G4GPU_XS_X86) && defined(__GNUC__)
    __builtin_cpu_init();
    if (__builtin_cpu_supports("avx512f")) {
        InterpolateBatchAVX512(table, energies, out, count);
        return;
    }
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma")) {
        InterpolateBatchAVX2(table, energies, out, count);
        return;
    }
#endif
#if defined(G4GPU_XS_NEON)
    InterpolateBatchNEON(table, energies, out, count);
#else
    InterpolateCrossSectionBatchScalar(table, energies, out, count);
#endif
}

}  // namespace g4gpu
