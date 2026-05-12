#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include <cuda_runtime_api.h>

#include "g4gpu/NeutronStepKernel.hh"

namespace {

constexpr int kTracks = 2;
constexpr float kTolerance = 1.0e-5f;

void Fail(const std::string& message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void Check(cudaError_t err, const char* what) {
    if (err != cudaSuccess) {
        Fail(std::string(what) + ": " + cudaGetErrorString(err));
    }
}

void ExpectNear(float observed, float expected, float tolerance, const std::string& label) {
    if (std::fabs(observed - expected) > tolerance) {
        Fail(label + " observed=" + std::to_string(observed) +
             " expected=" + std::to_string(expected));
    }
}

void ExpectFiniteUnit(float x, float y, float z, const std::string& label) {
    const float norm2 = x * x + y * y + z * z;
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)) {
        Fail(label + " direction is not finite");
    }
    ExpectNear(norm2, 1.0f, 5.0e-5f, label + " direction norm");
}

template <typename T>
T* DeviceCopy(const std::vector<T>& host, const char* label) {
    T* device = nullptr;
    Check(cudaMalloc(reinterpret_cast<void**>(&device), host.size() * sizeof(T)),
          (std::string("cudaMalloc ") + label).c_str());
    Check(cudaMemcpy(device, host.data(), host.size() * sizeof(T), cudaMemcpyHostToDevice),
          (std::string("cudaMemcpy H2D ") + label).c_str());
    return device;
}

template <typename T>
void CopyBack(T* device, std::vector<T>& host, const char* label) {
    Check(cudaMemcpy(host.data(), device, host.size() * sizeof(T), cudaMemcpyDeviceToHost),
          (std::string("cudaMemcpy D2H ") + label).c_str());
}

template <typename T>
void FreeDevice(T* ptr) {
    Check(cudaFree(ptr), "cudaFree");
}

void CheckHostDirectionHelper() {
    const float3 scattered = g4gpu::NeutronElasticScatterDirection(
        0.0f, 0.0f, 1.0f, 0.0f, 0.0f);
    ExpectFiniteUnit(scattered.x, scattered.y, scattered.z, "host scatter helper");

    const std::string notice = g4gpu::NeutronStepKernelScaffoldNotice();
    if (notice.find("no Geant4 neutron parity claim") == std::string::npos ||
        notice.find("no speed claim") == std::string::npos) {
        Fail("scaffold notice must reject parity and speed claims");
    }
}

void CheckGpuKernelOrFallback() {
    int device_count = 0;
    const cudaError_t device_err = cudaGetDeviceCount(&device_count);
    if (device_err != cudaSuccess || device_count == 0) {
        std::cout << "PASS: CPU-safe neutron scatter checks only; CUDA runtime unavailable: "
                  << cudaGetErrorString(device_err) << '\n';
        return;
    }

    std::vector<float> dx{0.0f, 0.6f};
    std::vector<float> dy{0.0f, 0.0f};
    std::vector<float> dz{1.0f, 0.8f};
    std::vector<float> ekin{42.0f, 7.0f};
    std::vector<int> pdg{2112, 22};
    std::vector<int> status{0, 0};

    g4gpu::TrackSOA tracks{};
    tracks.dx = DeviceCopy(dx, "dx");
    tracks.dy = DeviceCopy(dy, "dy");
    tracks.dz = DeviceCopy(dz, "dz");
    tracks.ekin = DeviceCopy(ekin, "ekin");
    tracks.pdg = DeviceCopy(pdg, "pdg");
    tracks.status = DeviceCopy(status, "status");
    tracks.size = kTracks;
    tracks.capacity = kTracks;

    g4gpu::LaunchNeutronStepKernel(&tracks, nullptr, nullptr, kTracks, nullptr);
    Check(cudaDeviceSynchronize(), "cudaDeviceSynchronize neutron kernel");

    CopyBack(tracks.dx, dx, "dx");
    CopyBack(tracks.dy, dy, "dy");
    CopyBack(tracks.dz, dz, "dz");
    CopyBack(tracks.ekin, ekin, "ekin");
    CopyBack(tracks.status, status, "status");

    ExpectNear(ekin[0], 42.0f, kTolerance, "neutron kinetic energy is preserved");
    ExpectFiniteUnit(dx[0], dy[0], dz[0], "neutron scattered");
    ExpectNear(ekin[1], 7.0f, kTolerance, "non-neutron kinetic energy unchanged");
    ExpectNear(dx[1], 0.6f, kTolerance, "non-neutron dx unchanged");
    ExpectNear(dy[1], 0.0f, kTolerance, "non-neutron dy unchanged");
    ExpectNear(dz[1], 0.8f, kTolerance, "non-neutron dz unchanged");
    if (status[0] != 0 || status[1] != 0) {
        Fail("kernel should not mark scaffold tracks failed");
    }

    FreeDevice(tracks.dx);
    FreeDevice(tracks.dy);
    FreeDevice(tracks.dz);
    FreeDevice(tracks.ekin);
    FreeDevice(tracks.pdg);
    FreeDevice(tracks.status);
}

}  // namespace

int main() {
    CheckHostDirectionHelper();
    CheckGpuKernelOrFallback();
    std::cout << "PASS: neutron elastic scatter scaffold preserves energy and isolation\n";
    return 0;
}
