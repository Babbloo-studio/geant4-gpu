#pragma once

#include "g4gpu/G4GPUGeometry.hh"

#include <cstddef>
#include <vector>

class G4VPhysicalVolume;

#if defined(G4GPU_WITH_RTX)
#  include <cuda.h>
#  include <optix.h>
#endif

namespace g4gpu {

struct RTXTriangle {
    float3 v0{};
    float3 v1{};
    float3 v2{};
    int volume_id = 0;
};

#if defined(G4GPU_WITH_RTX)
class RTXGeometry : public G4GPUGeometry {
public:
    RTXGeometry();
    ~RTXGeometry() override;

    RTXGeometry(const RTXGeometry&) = delete;
    RTXGeometry& operator=(const RTXGeometry&) = delete;

    void Build(G4VPhysicalVolume* world);
    float DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) override;

    bool built() const noexcept { return built_; }
    bool optixReady() const noexcept { return context_ != nullptr && gas_handle_ != 0; }
    std::size_t triangleCount() const noexcept { return triangles_.size(); }
    OptixTraversableHandle GetBVH() const noexcept { return gas_handle_; }

private:
    void Reset() noexcept;
    void InitOptiX();
    void CollectVolume(const G4VPhysicalVolume* volume, int depth);
    void AddTriangle(float3 a, float3 b, float3 c, int volume_id);
    void BuildGAS();

    OptixDeviceContext context_ = nullptr;
    OptixTraversableHandle gas_handle_ = 0;
    CUdeviceptr d_vertices_ = 0;
    CUdeviceptr d_indices_ = 0;
    CUdeviceptr d_gas_buffer_ = 0;
    std::vector<RTXTriangle> triangles_;
    bool built_ = false;
};
#else
class RTXGeometry {
public:
    void Build(void*) {}
    bool built() const noexcept { return false; }
};
#endif

}  // namespace g4gpu
