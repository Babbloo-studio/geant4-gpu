#include "g4gpu/G4GPUTrackBuffer.hh"

#include <cstddef>
#include <stdexcept>
#include <utility>

#if defined(G4GPU_HAVE_GEANT4)
#  include "G4ParticleDefinition.hh"
#  include "G4Track.hh"
#endif

namespace g4gpu {
namespace {

constexpr int kFloatArrayCount = 8;
constexpr int kIntArrayCount = 6;

void ensureCudaAvailable() {
#if !G4GPU_HAS_CUDA_RUNTIME
    throw std::runtime_error("G4GPU requires CUDA runtime headers and libraries");
#endif
}

template <typename T>
T* bindArray(std::byte*& cursor, int capacity) noexcept {
    auto* ptr = reinterpret_cast<T*>(cursor);
    cursor += static_cast<std::size_t>(capacity) * sizeof(T);
    return ptr;
}

}  // namespace

G4GPUTrackBuffer::G4GPUTrackBuffer(int capacity) {
    if (capacity <= 0) {
        throw std::invalid_argument("G4GPUTrackBuffer capacity must be positive");
    }
    ensureCudaAvailable();
    storage_bytes_ = storageBytes(capacity);

#if G4GPU_HAS_CUDA_RUNTIME
    try {
        CheckCuda(cudaMallocHost(&h_storage_, storage_bytes_), "cudaMallocHost");
        CheckCuda(cudaMalloc(&d_storage_, storage_bytes_), "cudaMalloc");
        bindSoA(h_buffer_, h_storage_, capacity);
        bindSoA(d_buffer_, d_storage_, capacity);
    } catch (...) {
        release();
        throw;
    }
#endif
}

G4GPUTrackBuffer::~G4GPUTrackBuffer() {
    release();
}

G4GPUTrackBuffer::G4GPUTrackBuffer(G4GPUTrackBuffer&& other) noexcept
    : h_buffer_(std::exchange(other.h_buffer_, {})),
      d_buffer_(std::exchange(other.d_buffer_, {})),
      h_storage_(std::exchange(other.h_storage_, nullptr)),
      d_storage_(std::exchange(other.d_storage_, nullptr)),
      storage_bytes_(std::exchange(other.storage_bytes_, 0)) {}

G4GPUTrackBuffer& G4GPUTrackBuffer::operator=(G4GPUTrackBuffer&& other) noexcept {
    if (this != &other) {
        release();
        h_buffer_ = std::exchange(other.h_buffer_, {});
        d_buffer_ = std::exchange(other.d_buffer_, {});
        h_storage_ = std::exchange(other.h_storage_, nullptr);
        d_storage_ = std::exchange(other.d_storage_, nullptr);
        storage_bytes_ = std::exchange(other.storage_bytes_, 0);
    }
    return *this;
}

void G4GPUTrackBuffer::clear() noexcept {
    h_buffer_.size = 0;
    d_buffer_.size = 0;
}

void G4GPUTrackBuffer::append(const G4Track& track) {
    if (full()) {
        throw std::overflow_error("G4GPUTrackBuffer is full");
    }

#if defined(G4GPU_HAVE_GEANT4)
    const int i = h_buffer_.size;
    const auto& pos = track.GetPosition();
    const auto& dir = track.GetMomentumDirection();
    const auto* pd = track.GetDefinition();

    h_buffer_.x[i] = static_cast<float>(pos.x());
    h_buffer_.y[i] = static_cast<float>(pos.y());
    h_buffer_.z[i] = static_cast<float>(pos.z());
    h_buffer_.dx[i] = static_cast<float>(dir.x());
    h_buffer_.dy[i] = static_cast<float>(dir.y());
    h_buffer_.dz[i] = static_cast<float>(dir.z());
    h_buffer_.ekin[i] = static_cast<float>(track.GetKineticEnergy());
    h_buffer_.time[i] = static_cast<float>(track.GetGlobalTime());
    h_buffer_.pdg[i] = pd ? pd->GetPDGEncoding() : 0;
    h_buffer_.material_idx[i] = -1;
    h_buffer_.volume_idx[i] = -1;
    h_buffer_.track_id[i] = track.GetTrackID();
    h_buffer_.parent_id[i] = track.GetParentID();
    h_buffer_.status[i] = 0;
    ++h_buffer_.size;
    d_buffer_.size = h_buffer_.size;
#else
    (void)track;
    throw std::runtime_error("G4GPUTrackBuffer::append requires Geant4 support");
#endif
}

void G4GPUTrackBuffer::copyHostToDevice(cudaStream_t stream) {
#if G4GPU_HAS_CUDA_RUNTIME
    if (h_buffer_.size > 0) {
        CheckCuda(cudaMemcpyAsync(d_storage_, h_storage_, storage_bytes_,
                                  cudaMemcpyHostToDevice, stream),
                  "cudaMemcpyAsync H2D TrackSOA storage");
    }
#else
    (void)stream;
    ensureCudaAvailable();
#endif
    d_buffer_.size = h_buffer_.size;
}

void G4GPUTrackBuffer::copyDeviceToHost(cudaStream_t stream) {
#if G4GPU_HAS_CUDA_RUNTIME
    if (h_buffer_.size > 0) {
        CheckCuda(cudaMemcpyAsync(h_storage_, d_storage_, storage_bytes_,
                                  cudaMemcpyDeviceToHost, stream),
                  "cudaMemcpyAsync D2H TrackSOA storage");
        CheckCuda(cudaStreamSynchronize(stream), "cudaStreamSynchronize");
    }
#else
    (void)stream;
    ensureCudaAvailable();
#endif
}

std::size_t G4GPUTrackBuffer::storageBytes(int capacity) noexcept {
    return static_cast<std::size_t>(capacity) *
           (kFloatArrayCount * sizeof(float) + kIntArrayCount * sizeof(int));
}

void G4GPUTrackBuffer::bindSoA(TrackSOA& soa, void* storage, int capacity) noexcept {
    auto* cursor = static_cast<std::byte*>(storage);
    soa.x = bindArray<float>(cursor, capacity);
    soa.y = bindArray<float>(cursor, capacity);
    soa.z = bindArray<float>(cursor, capacity);
    soa.dx = bindArray<float>(cursor, capacity);
    soa.dy = bindArray<float>(cursor, capacity);
    soa.dz = bindArray<float>(cursor, capacity);
    soa.ekin = bindArray<float>(cursor, capacity);
    soa.time = bindArray<float>(cursor, capacity);
    soa.pdg = bindArray<int>(cursor, capacity);
    soa.material_idx = bindArray<int>(cursor, capacity);
    soa.volume_idx = bindArray<int>(cursor, capacity);
    soa.track_id = bindArray<int>(cursor, capacity);
    soa.parent_id = bindArray<int>(cursor, capacity);
    soa.status = bindArray<int>(cursor, capacity);
    soa.size = 0;
    soa.capacity = capacity;
}

void G4GPUTrackBuffer::release() noexcept {
#if G4GPU_HAS_CUDA_RUNTIME
    if (h_storage_) {
        (void)cudaFreeHost(h_storage_);
    }
    if (d_storage_) {
        (void)cudaFree(d_storage_);
    }
#endif
    h_storage_ = nullptr;
    d_storage_ = nullptr;
    storage_bytes_ = 0;
    h_buffer_ = {};
    d_buffer_ = {};
}

}  // namespace g4gpu
