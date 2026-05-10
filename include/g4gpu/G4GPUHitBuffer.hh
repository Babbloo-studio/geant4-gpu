#pragma once

namespace g4gpu {

struct HitSOA {
    float* x = nullptr;
    float* y = nullptr;
    float* z = nullptr;
    float* edep = nullptr;
    float* time = nullptr;
    int* track_id = nullptr;
    int* volume_idx = nullptr;
    int size = 0;
    int capacity = 0;
};

class G4GPUHitBuffer {
public:
    G4GPUHitBuffer() = default;
    explicit G4GPUHitBuffer(int capacity) : capacity_(capacity) {}

    int capacity() const noexcept { return capacity_; }
    HitSOA& host() noexcept { return h_hits_; }
    const HitSOA& host() const noexcept { return h_hits_; }
    HitSOA& device() noexcept { return d_hits_; }
    const HitSOA& device() const noexcept { return d_hits_; }

private:
    int capacity_ = 0;
    HitSOA h_hits_;
    HitSOA d_hits_;
};

#if defined(__CUDACC__)
__global__ void NullStepKernel(int* status, int n);
#endif
void LaunchNullStepKernel(int* status, int n);

}  // namespace g4gpu
