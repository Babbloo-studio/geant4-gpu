#pragma once

#include "g4gpu/G4GPUGeometry.hh"
#include "g4gpu/MaterialData.hh"

#include <cstddef>
#include <cstdint>
#include <vector>

class G4Material;
class G4VPhysicalVolume;

namespace g4gpu {

struct VoxelGrid {
    float origin_x = 0.0f;
    float origin_y = 0.0f;
    float origin_z = 0.0f;
    float voxel_size = 0.0f;
    int nx = 0;
    int ny = 0;
    int nz = 0;
    std::uint8_t* material_id = nullptr;
    std::uint16_t* volume_id = nullptr;
};

class VoxelGeometry : public G4GPUGeometry {
public:
    explicit VoxelGeometry(float voxel_mm = 1.0f);
    ~VoxelGeometry() override;

    VoxelGeometry(const VoxelGeometry&) = delete;
    VoxelGeometry& operator=(const VoxelGeometry&) = delete;

    void Build(G4VPhysicalVolume* world);
    void Build(G4VPhysicalVolume* world, float voxel_mm);

    const VoxelGrid& HostGrid() const noexcept { return h_grid_; }
    const VoxelGrid& DeviceGrid() const noexcept { return d_grid_; }
    const std::vector<MaterialData>& materials() const noexcept { return materials_; }

    int MaterialIdAtHost(float3 pos) const noexcept;
    int VolumeIdAtHost(float3 pos) const noexcept;
    float DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) override;

    float voxelSizeMm() const noexcept { return voxel_mm_; }
    bool built() const noexcept { return built_; }

private:
    int FlatIndex(int ix, int iy, int iz) const noexcept;
    int MaterialIndexFor(const G4Material* material);
    int VolumeIndexFor(const G4VPhysicalVolume* volume);
    void ResetGrid() noexcept;
    void CopyToDevice();
    void ReleaseDevice() noexcept;

    G4VPhysicalVolume* world_ = nullptr;
    float voxel_mm_ = 1.0f;
    bool built_ = false;
    VoxelGrid h_grid_{};
    VoxelGrid d_grid_{};
    std::vector<std::uint8_t> host_material_ids_;
    std::vector<std::uint16_t> host_volume_ids_;
    std::vector<const G4Material*> material_keys_;
    std::vector<const G4VPhysicalVolume*> volume_keys_;
    std::vector<MaterialData> materials_;
};

#if defined(__CUDACC__)
extern __constant__ VoxelGrid d_active_voxel_grid;
__device__ bool ActiveVoxelGridAvailable();
__device__ float DistanceToNextVoxelBoundary(
    float3 pos, float3 dir, const VoxelGrid grid, int& out_material_id);
#endif

void UploadActiveVoxelGrid(const VoxelGrid& grid, cudaStream_t stream = nullptr);
void UploadVoxelMaterials(const MaterialData* materials, int count, cudaStream_t stream = nullptr);
float LaunchDistanceToNextVoxelBoundary(
    float3 pos, float3 dir, const VoxelGrid& grid, int& out_material_id,
    cudaStream_t stream = nullptr);

}  // namespace g4gpu
