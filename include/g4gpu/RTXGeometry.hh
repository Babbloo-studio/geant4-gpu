#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"
#include "g4gpu/G4GPUGeometry.hh"

#include <cstddef>
#include <limits>

class G4VPhysicalVolume;

#if defined(G4GPU_WITH_RTX)
#include <optix.h>
#include <cuda.h>
#endif

namespace g4gpu {

#if defined(G4GPU_WITH_RTX)

struct RTXLaunchParams {
    OptixTraversableHandle handle = 0;
    float3 origin{};
    float3 direction{};
    float* distance = nullptr;
    int* volume_id = nullptr;
};

struct RTXHitGroupData {
    int volume_id = -1;
};

class RTXGeometry : public G4GPUGeometry {
public:
    RTXGeometry();
    ~RTXGeometry() override;

    RTXGeometry(const RTXGeometry&) = delete;
    RTXGeometry& operator=(const RTXGeometry&) = delete;

    void Build(G4VPhysicalVolume* world);
    float DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) override;

    OptixTraversableHandle GetBVH() const noexcept { return gas_handle_; }
    std::size_t TriangleCount() const noexcept { return triangle_count_; }
    bool built() const noexcept { return built_; }

private:
    void Reset() noexcept;
    void InitContext();
    void BuildGas(G4VPhysicalVolume* world);
    void BuildPipeline();
    void BuildSbt();

    OptixDeviceContext context_ = nullptr;
    OptixTraversableHandle gas_handle_ = 0;
    OptixModule module_ = nullptr;
    OptixPipeline pipeline_ = nullptr;
    OptixProgramGroup raygen_group_ = nullptr;
    OptixProgramGroup miss_group_ = nullptr;
    OptixProgramGroup hit_group_ = nullptr;
    OptixShaderBindingTable sbt_{};
    CUdeviceptr d_gas_buffer_ = 0;
    CUdeviceptr d_raygen_record_ = 0;
    CUdeviceptr d_miss_record_ = 0;
    CUdeviceptr d_hit_record_ = 0;
    std::size_t triangle_count_ = 0;
    bool built_ = false;
};

float LaunchRTXDistanceToNextBoundary(
    OptixPipeline pipeline,
    const OptixShaderBindingTable& sbt,
    OptixTraversableHandle handle,
    float3 pos,
    float3 dir,
    int& next_vol,
    cudaStream_t stream = nullptr);

#else

class RTXGeometry : public G4GPUGeometry {
public:
    void Build(G4VPhysicalVolume*) {}
    float DistanceToNextBoundary(float3, float3, int& next_vol) override {
        next_vol = -1;
        return std::numeric_limits<float>::infinity();
    }
    std::size_t TriangleCount() const noexcept { return 0; }
    bool built() const noexcept { return false; }
};

#endif

}  // namespace g4gpu
