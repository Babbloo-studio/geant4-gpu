#include "g4gpu/CrossSectionInterpolator.hh"

#include <array>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace {

void Fail(const char* msg) {
    std::cerr << "FAIL: " << msg << '\n';
    std::exit(1);
}

}  // namespace

int main() {
    constexpr std::size_t kBins = 257;
    std::array<float, kBins> values{};
    for (std::size_t i = 0; i < values.size(); ++i) {
        const float x = static_cast<float>(i);
        values[i] = 0.25f + 0.003f * x + 0.05f * std::sin(0.07f * x);
    }

    const g4gpu::UniformCrossSectionTable table{values.data(), values.size(), 0.0f, 0.5f};
    std::vector<float> energies;
    for (int i = -32; i < 640; ++i) {
        energies.push_back(0.25f * static_cast<float>(i) + 0.03125f * (i % 7));
    }
    std::vector<float> scalar(energies.size());
    std::vector<float> batch(energies.size());
    g4gpu::InterpolateCrossSectionBatchScalar(table, energies.data(), scalar.data(), energies.size());
    g4gpu::InterpolateCrossSectionBatch(table, energies.data(), batch.data(), energies.size());

    float max_abs = 0.0f;
    for (std::size_t i = 0; i < energies.size(); ++i) {
        max_abs = std::max(max_abs, std::abs(scalar[i] - batch[i]));
    }
    if (max_abs > 1.0e-6f) {
        std::cerr << "max_abs=" << max_abs << '\n';
        Fail("SIMD and scalar interpolation differ");
    }

    const float below = g4gpu::InterpolateCrossSectionScalar(table, -10.0f);
    const float above = g4gpu::InterpolateCrossSectionScalar(table, 1.0e6f);
    if (below != values.front() || above != values.back()) {
        Fail("clamping at table boundaries failed");
    }

    std::cout << "PASS: cross-section interpolation backend="
              << g4gpu::CrossSectionInterpolatorBackend()
              << ", max_abs=" << max_abs << '\n';
    return 0;
}
