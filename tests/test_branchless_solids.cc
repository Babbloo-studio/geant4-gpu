#include "g4gpu/BranchlessSolids.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <random>
#include <vector>

namespace {

void Fail(const char* what) {
    std::cerr << "FAIL: " << what << '\n';
    std::exit(1);
}

bool Close(float a, float b, float tol = 2.0e-4f) {
    if (std::isinf(a) || std::isinf(b)) return std::isinf(a) && std::isinf(b);
    return std::abs(a - b) <= tol * std::max(1.0f, std::max(std::abs(a), std::abs(b)));
}

}  // namespace

int main() {
    const g4gpu::BoxSolid box{10.0f, 20.0f, 30.0f};
    if (!Close(g4gpu::DistanceToInBoxBranchless(box, 20.0f, 0.0f, 0.0f, -1.0f, 0.2f, 0.1f), 10.0f)) {
        Fail("box distance-to-in axial case");
    }
    if (!Close(g4gpu::DistanceToOutBoxBranchless(box, 0.0f, 0.0f, 0.0f, 1.0f, 0.1f, 0.2f), 10.0f)) {
        Fail("box distance-to-out axial case");
    }

    const g4gpu::TubsSolid tubs{0.0f, 10.0f, 25.0f};
    if (!Close(g4gpu::DistanceToInTubsBranchless(tubs, 20.0f, 0.0f, 0.0f, -1.0f, 0.0f, 0.0f), 10.0f)) {
        Fail("tubs distance-to-in radial case");
    }
    if (!Close(g4gpu::DistanceToOutTubsBranchless(tubs, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f), 10.0f)) {
        Fail("tubs distance-to-out radial case");
    }

    std::mt19937 rng(424242);
    std::uniform_real_distribution<float> pos(-50.0f, 50.0f);
    std::uniform_real_distribution<float> dir(-1.0f, 1.0f);
    constexpr int kSamples = 4096;
    std::vector<float> x(kSamples), y(kSamples), z(kSamples), dx(kSamples), dy(kSamples), dz(kSamples);
    std::vector<float> ref(kSamples), batch(kSamples);
    float max_abs = 0.0f;
    for (int i = 0; i < kSamples; ++i) {
        x[i] = pos(rng);
        y[i] = pos(rng);
        z[i] = pos(rng);
        dx[i] = dir(rng);
        dy[i] = dir(rng);
        dz[i] = dir(rng);
        if (std::abs(dx[i]) + std::abs(dy[i]) + std::abs(dz[i]) < 0.1f) dx[i] = 1.0f;
        const float norm = std::sqrt(dx[i] * dx[i] + dy[i] * dy[i] + dz[i] * dz[i]);
        dx[i] /= norm;
        dy[i] /= norm;
        dz[i] /= norm;
        ref[i] = g4gpu::DistanceToInBoxReference(box, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
        const float b = g4gpu::DistanceToInBoxBranchless(box, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
        if (!Close(ref[i], b)) Fail("box branchless/reference mismatch");
        max_abs = std::max(max_abs, std::isfinite(ref[i]) ? std::abs(ref[i] - b) : 0.0f);
    }
    g4gpu::DistanceToInBoxBatch(box, x.data(), y.data(), z.data(), dx.data(), dy.data(), dz.data(), batch.data(), batch.size());
    for (int i = 0; i < kSamples; ++i) {
        if (!Close(ref[i], batch[i], 5.0e-4f)) Fail("box batch/reference mismatch");
    }

    for (int i = 0; i < kSamples; ++i) {
        const float a = g4gpu::DistanceToInTubsReference(tubs, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
        const float b = g4gpu::DistanceToInTubsBranchless(tubs, x[i], y[i], z[i], dx[i], dy[i], dz[i]);
        if (!Close(a, b)) Fail("tubs branchless/reference mismatch");
    }

    std::cout << "PASS: branchless solids backend=" << g4gpu::BranchlessSolidsBackend()
              << ", samples=" << kSamples << ", max_abs=" << max_abs << '\n';
    return 0;
}
