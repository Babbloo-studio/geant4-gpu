#pragma once

#include <cstddef>

#include "g4gpu/G4GPUCudaCompat.hh"

class G4Track;

namespace g4gpu {

struct TrackSOA {
    float* x = nullptr;
    float* y = nullptr;
    float* z = nullptr;
    float* dx = nullptr;
    float* dy = nullptr;
    float* dz = nullptr;
    float* ekin = nullptr;
    float* time = nullptr;

    int* pdg = nullptr;
    int* material_idx = nullptr;
    int* volume_idx = nullptr;
    int* track_id = nullptr;
    int* parent_id = nullptr;
    int* status = nullptr;

    int size = 0;
    int capacity = 0;
};

class G4GPUTrackBuffer {
public:
    explicit G4GPUTrackBuffer(int capacity);
    ~G4GPUTrackBuffer();

    G4GPUTrackBuffer(const G4GPUTrackBuffer&) = delete;
    G4GPUTrackBuffer& operator=(const G4GPUTrackBuffer&) = delete;
    G4GPUTrackBuffer(G4GPUTrackBuffer&& other) noexcept;
    G4GPUTrackBuffer& operator=(G4GPUTrackBuffer&& other) noexcept;

    TrackSOA& host() noexcept { return h_buffer_; }
    const TrackSOA& host() const noexcept { return h_buffer_; }
    TrackSOA& device() noexcept { return d_buffer_; }
    const TrackSOA& device() const noexcept { return d_buffer_; }

    int capacity() const noexcept { return h_buffer_.capacity; }
    int size() const noexcept { return h_buffer_.size; }
    bool empty() const noexcept { return size() == 0; }
    bool full() const noexcept { return size() >= capacity(); }

    void clear() noexcept;
    void append(const G4Track& track);
    void copyHostToDevice(cudaStream_t stream = nullptr);
    void copyDeviceToHost(cudaStream_t stream = nullptr);

private:
    TrackSOA h_buffer_;
    TrackSOA d_buffer_;
    void* h_storage_ = nullptr;
    void* d_storage_ = nullptr;
    std::size_t storage_bytes_ = 0;

    static std::size_t storageBytes(int capacity) noexcept;
    static void bindSoA(TrackSOA& soa, void* storage, int capacity) noexcept;
    void release() noexcept;
};

}  // namespace g4gpu
