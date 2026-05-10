#include <algorithm>
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
constexpr int kSteps = 10;
constexpr float kStepMm = 10.0f;
constexpr float kInitialEnergyMeV = 1000.0f;
constexpr float kMuonMassMeV = 105.658f;
constexpr float kElectronMassMeV = 0.511f;
constexpr float kK = 0.307075f;
constexpr float kStoppingPowerScale = 0.46878f;
constexpr float kTolerance = 0.10f;

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

float BetheBlochHost(float ekin, const g4gpu::MaterialData& mat) {
    const float gamma = 1.0f + ekin / kMuonMassMeV;
    const float beta2 = 1.0f - 1.0f / (gamma * gamma);
    const float tmax = 2.0f * kElectronMassMeV * beta2 * gamma * gamma /
                       (1.0f + 2.0f * gamma * kElectronMassMeV / kMuonMassMeV +
                        (kElectronMassMeV / kMuonMassMeV) *
                            (kElectronMassMeV / kMuonMassMeV));
    const float dedx = kK * mat.Z_over_A / beta2 *
                       (0.5f * std::log(2.0f * kElectronMassMeV * beta2 *
                                             gamma * gamma * tmax / (mat.I * mat.I)) -
                        beta2);
    return dedx * mat.density * kStoppingPowerScale;
}

float HighlandHost(float ekin, float step, const g4gpu::MaterialData& mat) {
    const float total = ekin + kMuonMassMeV;
    const float p = std::sqrt(total * total - kMuonMassMeV * kMuonMassMeV);
    const float beta = p / total;
    const float x_over_x0 = step / mat.X0;
    return 13.6f / (p * beta) * std::sqrt(x_over_x0) *
           (1.0f + 0.038f * std::log(x_over_x0 / (beta * beta)));
}

float StepwiseHighlandReference(const g4gpu::MaterialData& mat) {
    float ekin = kInitialEnergyMeV;
    float variance = 0.0f;
    for (int i = 0; i < kSteps; ++i) {
        const float theta0 = HighlandHost(ekin, kStepMm, mat);
        variance += theta0 * theta0;
        ekin = std::max(0.0f, ekin - BetheBlochHost(ekin, mat) * kStepMm);
    }
    return std::sqrt(variance);
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
    const auto iron = Iron();
    g4gpu::G4GPUTrackBuffer buffer(kTracks);
    FillMuons(buffer.host());

    g4gpu::MaterialData* d_materials = nullptr;
    curandState* d_rng = nullptr;
    Check(cudaMalloc(&d_materials, sizeof(g4gpu::MaterialData)), "cudaMalloc materials");
    Check(cudaMemcpy(d_materials, &iron, sizeof(g4gpu::MaterialData), cudaMemcpyHostToDevice),
          "cudaMemcpy materials");
    Check(cudaMalloc(&d_rng, kTracks * sizeof(curandState)), "cudaMalloc rng");

    buffer.copyHostToDevice();
    g4gpu::LaunchInitRNGKernel(d_rng, kTracks, 7654321ULL, nullptr);
    for (int i = 0; i < kSteps; ++i) {
        g4gpu::LaunchMuonStepKernel(&buffer.device(), d_rng, d_materials, kTracks, nullptr);
    }
    buffer.copyDeviceToHost();

    double sum = 0.0;
    double sum2 = 0.0;
    for (int i = 0; i < kTracks; ++i) {
        const double theta_x = std::atan2(buffer.host().dx[i], buffer.host().dz[i]);
        sum += theta_x;
        sum2 += theta_x * theta_x;
    }
    const double mean = sum / kTracks;
    const double rms = std::sqrt(sum2 / kTracks - mean * mean);
    const double prediction = StepwiseHighlandReference(iron);

    Check(cudaFree(d_rng), "cudaFree rng");
    Check(cudaFree(d_materials), "cudaFree materials");

    const double rel_err = std::abs(rms - prediction) / prediction;
    if (rel_err > kTolerance) {
        std::cerr << "FAIL: theta_x RMS=" << rms
                  << " rad, Highland prediction=" << prediction << " rad\n";
        return 1;
    }

    std::cout << "PASS: theta_x RMS=" << rms
              << " rad, Highland prediction=" << prediction << " rad\n";
    return 0;
}
