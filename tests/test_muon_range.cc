#include <cmath>
#include <cstdlib>
#include <iostream>

#include <cuda_runtime_api.h>
#include <curand_kernel.h>

#include "g4gpu/G4GPUTrackBuffer.hh"
#include "g4gpu/MaterialData.hh"
#include "g4gpu/MuonStepKernel.hh"

namespace {

constexpr int kTracks = 1000;
constexpr float kInitialEnergyMeV = 1000.0f;
constexpr float kReferenceRangeMm = 165.0f;
constexpr float kTolerance = 0.05f;

void Check(cudaError_t err, const char* what) {
    if (err != cudaSuccess) {
        std::cerr << "FAIL: " << what << ": " << cudaGetErrorString(err) << '\n';
        std::exit(1);
    }
}

g4gpu::MaterialData Iron() {
    g4gpu::MaterialData mat{};
    mat.Z_over_A = 0.4656f;
    mat.I = 286.0e-6f;
    mat.density = 7.874f;
    mat.X0 = 17.58f;
    mat.name[0] = 'F';
    mat.name[1] = 'e';
    return mat;
}

void FillMuons(g4gpu::TrackSOA& tracks) {
    tracks.size = kTracks;
    for (int i = 0; i < kTracks; ++i) {
        tracks.x[i] = 0.0f;
        tracks.y[i] = 0.0f;
        tracks.z[i] = 0.0f;
        tracks.dx[i] = 0.0f;
        tracks.dy[i] = 0.0f;
        tracks.dz[i] = 1.0f;
        tracks.ekin[i] = kInitialEnergyMeV;
        tracks.time[i] = 0.0f;
        tracks.pdg[i] = 13;
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
    FillMuons(buffer.host());

    g4gpu::MaterialData* d_materials = nullptr;
    curandState* d_rng = nullptr;
    const auto iron = Iron();
    Check(cudaMalloc(&d_materials, sizeof(g4gpu::MaterialData)), "cudaMalloc materials");
    Check(cudaMemcpy(d_materials, &iron, sizeof(g4gpu::MaterialData), cudaMemcpyHostToDevice),
          "cudaMemcpy materials");
    Check(cudaMalloc(&d_rng, kTracks * sizeof(curandState)), "cudaMalloc rng");

    buffer.copyHostToDevice();
    g4gpu::LaunchInitRNGKernel(d_rng, kTracks, 1234567ULL, nullptr);

    int stopped = 0;
    for (int iter = 0; iter < 1000 && stopped < kTracks; ++iter) {
        g4gpu::LaunchMuonStepKernel(&buffer.device(), d_rng, d_materials, kTracks, nullptr);
        buffer.copyDeviceToHost();
        stopped = 0;
        for (int i = 0; i < kTracks; ++i) {
            stopped += buffer.host().status[i] == 1 ? 1 : 0;
        }
    }

    double mean_range = 0.0;
    for (int i = 0; i < kTracks; ++i) {
        mean_range += std::sqrt(buffer.host().x[i] * buffer.host().x[i] +
                                buffer.host().y[i] * buffer.host().y[i] +
                                buffer.host().z[i] * buffer.host().z[i]);
    }
    mean_range /= kTracks;

    Check(cudaFree(d_rng), "cudaFree rng");
    Check(cudaFree(d_materials), "cudaFree materials");

    const double rel_err = std::abs(mean_range - kReferenceRangeMm) / kReferenceRangeMm;
    if (stopped != kTracks || rel_err > kTolerance) {
        std::cerr << "FAIL: measured range=" << mean_range
                  << " mm, PDG reference=" << kReferenceRangeMm
                  << " mm, stopped=" << stopped << "/" << kTracks << '\n';
        return 1;
    }

    std::cout << "PASS: measured range=" << mean_range
              << " mm, PDG reference=" << kReferenceRangeMm << " mm\n";
    return 0;
}
