#include "g4gpu/G4GPUHitBuffer.hh"

#include "g4gpu/G4GPUCudaCompat.hh"

namespace g4gpu {

__global__ void NullStepKernel(int* status, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        status[i] = 1;
    }
}

void LaunchNullStepKernel(int* status, int n) {
    if (n <= 0) return;
    constexpr int threads_per_block = 256;
    const int blocks = (n + threads_per_block - 1) / threads_per_block;
    NullStepKernel<<<blocks, threads_per_block>>>(status, n);
    CheckCuda(cudaGetLastError(), "NullStepKernel launch");
}

}  // namespace g4gpu
