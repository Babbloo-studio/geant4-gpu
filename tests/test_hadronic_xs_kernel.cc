#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>

#include <cuda_runtime_api.h>

#include "g4gpu/G4GPUTrackBuffer.hh"
#include "g4gpu/HadronicXSKernel.hh"

namespace {

constexpr int kTracks = 4096;
constexpr float kTolerance = 0.001f;
constexpr float kPi = 3.14159265358979323846f;

void Check(cudaError_t err, const char* what) {
    if (err != cudaSuccess) {
        std::cerr << "FAIL: " << what << ": " << cudaGetErrorString(err) << '\n';
        std::exit(1);
    }
}

float SigmaNNReference(float sqrt_s_gev) {
    constexpr float s_min = 1.90f;
    constexpr float s_max = 100.0f;
    const float x = std::log(std::max(s_min, std::min(s_max, sqrt_s_gev)) / s_min) /
                    std::log(s_max / s_min);
    return 32.0f + 18.0f * x + 4.0f * x * x;
}

float CPUOpticalLimitXS(int A, float ekin_mev) {
    const float ekin_gev = ekin_mev * 1.0e-3f;
    const float mp = 0.938272f;
    const float s = 2.0f * mp * mp + 2.0f * mp * (ekin_gev + mp);
    const float sqrt_s = std::sqrt(std::max(s, 0.0f));
    const float r = 1.3f * std::pow(static_cast<float>(A), 1.0f / 3.0f);
    const float rho_l = 3.0f * static_cast<float>(A) / (2.0f * kPi * r);
    const float sigma_nn_fm2 = SigmaNNReference(sqrt_s) / 10.0f;
    return kPi * r * r * (1.0f - std::exp(-sigma_nn_fm2 * rho_l)) * 10.0f;
}

void FillProtonsOnIron(g4gpu::TrackSOA& tracks) {
    tracks.size = kTracks;
    for (int i = 0; i < kTracks; ++i) {
        const float frac = static_cast<float>(i) / static_cast<float>(kTracks - 1);
        tracks.x[i] = tracks.y[i] = tracks.z[i] = 0.0f;
        tracks.dx[i] = tracks.dy[i] = 0.0f;
        tracks.dz[i] = 1.0f;
        tracks.ekin[i] = 1.0f * std::pow(100000.0f, frac);
        tracks.time[i] = 0.0f;
        tracks.pdg[i] = 2212;
        tracks.material_idx[i] = 0;
        tracks.volume_idx[i] = 0;
        tracks.track_id[i] = i + 1;
        tracks.parent_id[i] = 0;
        tracks.status[i] = 0;
    }
}

}  // namespace

int main() {
    g4gpu::G4GPUTrackBuffer buffer(kTracks);
    FillProtonsOnIron(buffer.host());
    buffer.copyHostToDevice();

    g4gpu::HadronicXSTarget* d_targets = nullptr;
    float* d_xs = nullptr;
    const g4gpu::HadronicXSTarget iron{26, 56};
    Check(cudaMalloc(&d_targets, sizeof(g4gpu::HadronicXSTarget)), "cudaMalloc targets");
    Check(cudaMemcpy(d_targets, &iron, sizeof(iron), cudaMemcpyHostToDevice),
          "cudaMemcpy targets");
    Check(cudaMalloc(&d_xs, kTracks * sizeof(float)), "cudaMalloc xs");

    g4gpu::G4GPUHadronicXS::Initialize();
    g4gpu::G4GPUHadronicXS::EvaluateBatch(&buffer.device(), kTracks, d_targets, 1, d_xs);

    std::vector<float> xs(kTracks);
    Check(cudaMemcpy(xs.data(), d_xs, kTracks * sizeof(float), cudaMemcpyDeviceToHost),
          "cudaMemcpy xs");

    float max_rel_err = 0.0f;
    for (int i = 0; i < kTracks; ++i) {
        const float ref = CPUOpticalLimitXS(56, buffer.host().ekin[i]);
        const float rel = std::abs(xs[i] - ref) / ref;
        max_rel_err = std::max(max_rel_err, rel);
    }

    Check(cudaFree(d_xs), "cudaFree xs");
    Check(cudaFree(d_targets), "cudaFree targets");

    if (max_rel_err >= kTolerance) {
        std::cerr << "FAIL: max relative error " << max_rel_err
                  << " exceeds " << kTolerance << '\n';
        return 1;
    }

    std::cout << "PASS: max relative error " << max_rel_err
              << " for " << kTracks << " protons on Fe\n";
    return 0;
}
