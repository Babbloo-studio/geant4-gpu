#include "g4gpu/HadronicXSKernel.hh"

#include <algorithm>
#include <cmath>

#include <cuda_runtime.h>

namespace g4gpu {
namespace {

constexpr int kThreadsPerBlock = 256;
constexpr float kPi = 3.14159265358979323846f;
constexpr float kNucleonMassGeV = 0.938272f;
constexpr float kSqrtSMinGeV = 1.90f;
constexpr float kSqrtSMaxGeV = 100.0f;
constexpr float kFm2ToMb = 10.0f;
constexpr float kDefaultCoeff0 = 32.0f;
constexpr float kDefaultCoeff1 = 18.0f;
constexpr float kDefaultCoeff2 = 4.0f;

__constant__ float d_sigma_nn_coeff[3];
__device__ bool d_coeff_initialized;

void UploadSigmaCoefficients(cudaStream_t stream) {
    const float coeff[3] = {kDefaultCoeff0, kDefaultCoeff1, kDefaultCoeff2};
    CheckCuda(cudaMemcpyToSymbolAsync(d_sigma_nn_coeff, coeff, sizeof(coeff), 0,
                                      cudaMemcpyHostToDevice, stream),
              "cudaMemcpyToSymbolAsync d_sigma_nn_coeff");
    const bool initialized = true;
    CheckCuda(cudaMemcpyToSymbolAsync(d_coeff_initialized, &initialized,
                                      sizeof(initialized), 0,
                                      cudaMemcpyHostToDevice, stream),
              "cudaMemcpyToSymbolAsync d_coeff_initialized");
}

__device__ float Clamp(float value, float lo, float hi) {
    return fminf(hi, fmaxf(lo, value));
}

__device__ HadronicXSTarget SelectTarget(
    const TrackSOA& tracks,
    int i,
    const HadronicXSTarget* targets,
    int n_targets
) {
    if (!targets || n_targets <= 0) return {1, 1};
    if (n_targets == 1) return targets[0];
    int idx = tracks.material_idx ? tracks.material_idx[i] : 0;
    idx = max(0, min(idx, n_targets - 1));
    HadronicXSTarget target = targets[idx];
    if (target.a <= 0) target = {1, 1};
    return target;
}

__device__ float SigmaNNMb(float sqrt_s_gev) {
    const float s = Clamp(sqrt_s_gev, kSqrtSMinGeV, kSqrtSMaxGeV);
    const float x = logf(s / kSqrtSMinGeV) / logf(kSqrtSMaxGeV / kSqrtSMinGeV);
    const float c0 = d_coeff_initialized ? d_sigma_nn_coeff[0] : kDefaultCoeff0;
    const float c1 = d_coeff_initialized ? d_sigma_nn_coeff[1] : kDefaultCoeff1;
    const float c2 = d_coeff_initialized ? d_sigma_nn_coeff[2] : kDefaultCoeff2;
    return c0 + c1 * x + c2 * x * x;
}

__device__ float GlauberOpticalLimitXS(int a, float ekin_mev) {
    a = max(a, 1);
    const float ekin_gev = fmaxf(0.0f, ekin_mev) * 1.0e-3f;
    const float s = 2.0f * kNucleonMassGeV * kNucleonMassGeV +
                    2.0f * kNucleonMassGeV * (ekin_gev + kNucleonMassGeV);
    const float sqrt_s = sqrtf(fmaxf(s, 0.0f));
    const float radius_fm = 1.3f * powf(static_cast<float>(a), 1.0f / 3.0f);
    const float rho_l = 3.0f * static_cast<float>(a) / (2.0f * kPi * radius_fm);
    const float sigma_nn_fm2 = SigmaNNMb(sqrt_s) / kFm2ToMb;
    const float xs_fm2 = kPi * radius_fm * radius_fm *
                         (1.0f - expf(-sigma_nn_fm2 * rho_l));
    return xs_fm2 * kFm2ToMb;
}

__global__ void HadronicXSKernel(
    TrackSOA tracks,
    int n_tracks,
    const HadronicXSTarget* targets,
    int n_targets,
    float* xs_out
) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n_tracks || i >= tracks.size || !xs_out) return;

    if (tracks.status && tracks.status[i] != 0) {
        xs_out[i] = 0.0f;
        return;
    }

    const HadronicXSTarget target = SelectTarget(tracks, i, targets, n_targets);
    xs_out[i] = GlauberOpticalLimitXS(target.a, tracks.ekin[i]);
}

}  // namespace

void InitializeHadronicXS(cudaStream_t stream) {
    UploadSigmaCoefficients(stream);
    CheckCuda(cudaStreamSynchronize(stream), "cudaStreamSynchronize hadronic init");
}

void EvaluateHadronicXSBatch(
    const TrackSOA* d_tracks,
    int n_tracks,
    const HadronicXSTarget* d_targets,
    int n_targets,
    float* d_xs_out,
    cudaStream_t stream
) {
    if (!d_tracks || n_tracks <= 0 || !d_xs_out) return;
    const int blocks = (n_tracks + kThreadsPerBlock - 1) / kThreadsPerBlock;
    HadronicXSKernel<<<blocks, kThreadsPerBlock, 0, stream>>>(*d_tracks, n_tracks,
                                                              d_targets, n_targets,
                                                              d_xs_out);
    CheckCuda(cudaGetLastError(), "HadronicXSKernel launch");
    CheckCuda(cudaStreamSynchronize(stream), "cudaStreamSynchronize hadronic xs");
}

}  // namespace g4gpu
