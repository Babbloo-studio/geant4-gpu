#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>

#include <cuda_runtime_api.h>
#include <curand_kernel.h>

#include "g4gpu/EMStepKernel.hh"

namespace {

constexpr int kSamples = 10000;
constexpr int kCdfBins = 20000;
constexpr float kIncidentEnergyMeV = 1.0f;
constexpr double kElectronMassMeV = 0.51099895;
constexpr double kRequiredPValue = 0.05;
constexpr int kCudaUnavailableSkipCode = 77;

void Check(cudaError_t err, const char* what) {
    if (err != cudaSuccess) {
        std::cerr << "FAIL: " << what << ": " << cudaGetErrorString(err) << '\n';
        std::exit(1);
    }
}

__global__ void InitRngKernel(curandState* rng, int n, unsigned long long seed) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) curand_init(seed, i, 0, &rng[i]);
}

void LaunchInitRng(curandState* rng, int n) {
    constexpr int threads = 256;
    const int blocks = (n + threads - 1) / threads;
    InitRngKernel<<<blocks, threads>>>(rng, n, 20260511ULL);
    Check(cudaGetLastError(), "InitRngKernel launch");
}

void FillGammas(g4gpu::TrackSOA& tracks) {
    tracks.size = kSamples;
    for (int i = 0; i < kSamples; ++i) {
        tracks.x[i] = 0.0f;
        tracks.y[i] = 0.0f;
        tracks.z[i] = 0.0f;
        tracks.dx[i] = 0.0f;
        tracks.dy[i] = 0.0f;
        tracks.dz[i] = 1.0f;
        tracks.ekin[i] = kIncidentEnergyMeV;
        tracks.time[i] = 0.0f;
        tracks.pdg[i] = 22;
        tracks.material_idx[i] = 0;
        tracks.volume_idx[i] = 0;
        tracks.track_id[i] = i + 1;
        tracks.parent_id[i] = 0;
        tracks.status[i] = 0;
    }
}

double KleinNishinaMuDensity(double mu) {
    const double alpha = kIncidentEnergyMeV / kElectronMassMeV;
    const double epsilon = 1.0 / (1.0 + alpha * (1.0 - mu));
    const double sin2 = std::max(0.0, 1.0 - mu * mu);
    return epsilon * epsilon * (epsilon + 1.0 / epsilon - sin2);
}

std::vector<double> BuildKleinNishinaCdf() {
    std::vector<double> cdf(kCdfBins + 1, 0.0);
    const double dmu = 2.0 / kCdfBins;
    double previous = KleinNishinaMuDensity(-1.0);
    for (int i = 1; i <= kCdfBins; ++i) {
        const double mu = -1.0 + i * dmu;
        const double current = KleinNishinaMuDensity(mu);
        cdf[i] = cdf[i - 1] + 0.5 * (previous + current) * dmu;
        previous = current;
    }
    const double norm = cdf.back();
    for (double& value : cdf) value /= norm;
    return cdf;
}

double CdfAtEnergy(double energy, const std::vector<double>& cdf) {
    const double alpha = kIncidentEnergyMeV / kElectronMassMeV;
    const double epsilon = std::clamp(energy / kIncidentEnergyMeV,
                                      1.0 / (1.0 + 2.0 * alpha), 1.0);
    const double mu = std::clamp(1.0 - (1.0 / epsilon - 1.0) / alpha, -1.0, 1.0);
    const double x = (mu + 1.0) * 0.5 * kCdfBins;
    const int lo = std::clamp(static_cast<int>(std::floor(x)), 0, kCdfBins);
    const int hi = std::min(kCdfBins, lo + 1);
    const double t = std::clamp(x - lo, 0.0, 1.0);
    return cdf[lo] * (1.0 - t) + cdf[hi] * t;
}

double KolmogorovPValue(double d, int n) {
    if (d <= 0.0) return 1.0;
    const double en = std::sqrt(static_cast<double>(n));
    const double lambda = (en + 0.12 + 0.11 / en) * d;
    double sum = 0.0;
    for (int j = 1; j <= 100; ++j) {
        const double term = std::exp(-2.0 * j * j * lambda * lambda);
        sum += (j % 2 == 1 ? 1.0 : -1.0) * term;
        if (term < 1.0e-12) break;
    }
    return std::clamp(2.0 * sum, 0.0, 1.0);
}

double KsDistance(const std::vector<float>& samples, const std::vector<double>& cdf) {
    double d = 0.0;
    const double n = static_cast<double>(samples.size());
    for (std::size_t i = 0; i < samples.size(); ++i) {
        const double f = CdfAtEnergy(samples[i], cdf);
        const double empirical_hi = static_cast<double>(i + 1) / n;
        const double empirical_lo = static_cast<double>(i) / n;
        d = std::max(d, std::abs(empirical_hi - f));
        d = std::max(d, std::abs(f - empirical_lo));
    }
    return d;
}

}  // namespace

int main() {
    int device_count = 0;
    const cudaError_t count_status = cudaGetDeviceCount(&device_count);
    if (count_status != cudaSuccess || device_count == 0) {
        std::cout << "SKIP: CUDA device unavailable for Klein-Nishina runtime test\n";
        return kCudaUnavailableSkipCode;
    }

    curandState* d_rng = nullptr;
    g4gpu::G4GPUTrackBuffer buffer(kSamples);
    FillGammas(buffer.host());
    buffer.copyHostToDevice();

    Check(cudaMalloc(&d_rng, kSamples * sizeof(curandState)), "cudaMalloc rng");

    LaunchInitRng(d_rng, kSamples);
    g4gpu::LaunchEMStepKernel(&buffer.device(), d_rng, nullptr, kSamples, nullptr);
    buffer.copyDeviceToHost();

    std::vector<float> energy(kSamples);
    for (int i = 0; i < kSamples; ++i) {
        if (buffer.host().status[i] != 0) {
            std::cerr << "FAIL: gamma track status[" << i << "]="
                      << buffer.host().status[i] << '\n';
            return 1;
        }
        energy[i] = buffer.host().ekin[i];
    }

    Check(cudaFree(d_rng), "cudaFree rng");

    std::sort(energy.begin(), energy.end());
    const auto cdf = BuildKleinNishinaCdf();
    const double d = KsDistance(energy, cdf);
    const double p = KolmogorovPValue(d, kSamples);
    if (p <= kRequiredPValue) {
        std::cerr << "FAIL: Klein-Nishina scattered-energy KS p=" << p
                  << " D=" << d << " samples=" << kSamples << '\n';
        return 1;
    }

    std::cout << "PASS: Klein-Nishina scattered-energy KS p=" << p
              << " D=" << d << " samples=" << kSamples << '\n';
    return 0;
}
