#include "g4gpu/VoxelGeometry.hh"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

#include <cuda_runtime_api.h>

#include <G4AffineTransform.hh>
#include <G4IonisParamMat.hh>
#include <G4LogicalVolume.hh>
#include <G4Material.hh>
#include <G4Navigator.hh>
#include <G4SystemOfUnits.hh>
#include <G4ThreeVector.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VSolid.hh>
#include <G4VoxelLimits.hh>
#include <geomdefs.hh>

namespace g4gpu {
namespace {

float ToMm(G4double value) {
    return static_cast<float>(value / mm);
}

MaterialData ToMaterialData(const G4Material& material) {
    MaterialData out{};
    const G4double a = material.GetA();
    if (a > 0.0) {
        out.Z_over_A = static_cast<float>(material.GetZ() / (a / (g / mole)));
    }
    out.density = static_cast<float>(material.GetDensity() / (g / cm3));
    if (const auto* ion = material.GetIonisation()) {
        out.I = static_cast<float>(ion->GetMeanExcitationEnergy() / MeV);
    }
    out.X0 = static_cast<float>(material.GetRadlen() / mm);
    std::strncpy(out.name, material.GetName().c_str(), sizeof(out.name) - 1);
    out.name[sizeof(out.name) - 1] = '\0';
    return out;
}

void RequireExtent(bool ok, const char* axis) {
    if (!ok) {
        throw std::runtime_error(std::string("VoxelGeometry failed to calculate world extent on ") + axis);
    }
}

}  // namespace

VoxelGeometry::VoxelGeometry(float voxel_mm) : voxel_mm_(voxel_mm) {
    if (voxel_mm_ <= 0.0f) {
        throw std::invalid_argument("VoxelGeometry voxel size must be positive");
    }
}

VoxelGeometry::~VoxelGeometry() { ReleaseDevice(); }

void VoxelGeometry::Build(G4VPhysicalVolume* world, float voxel_mm) {
    if (voxel_mm <= 0.0f) {
        throw std::invalid_argument("VoxelGeometry voxel size must be positive");
    }
    voxel_mm_ = voxel_mm;
    Build(world);
}

void VoxelGeometry::Build(G4VPhysicalVolume* world) {
    if (!world || !world->GetLogicalVolume() || !world->GetLogicalVolume()->GetSolid()) {
        throw std::invalid_argument("VoxelGeometry::Build requires a world volume with a solid");
    }
    ResetGrid();
    world_ = world;

    auto* solid = world->GetLogicalVolume()->GetSolid();
    G4VoxelLimits limits;
    G4AffineTransform transform;
    G4double min_x = 0.0, max_x = 0.0;
    G4double min_y = 0.0, max_y = 0.0;
    G4double min_z = 0.0, max_z = 0.0;
    RequireExtent(solid->CalculateExtent(kXAxis, limits, transform, min_x, max_x), "x");
    RequireExtent(solid->CalculateExtent(kYAxis, limits, transform, min_y, max_y), "y");
    RequireExtent(solid->CalculateExtent(kZAxis, limits, transform, min_z, max_z), "z");

    h_grid_.origin_x = ToMm(min_x);
    h_grid_.origin_y = ToMm(min_y);
    h_grid_.origin_z = ToMm(min_z);
    h_grid_.voxel_size = voxel_mm_;
    h_grid_.nx = static_cast<int>(std::ceil((ToMm(max_x) - h_grid_.origin_x) / voxel_mm_));
    h_grid_.ny = static_cast<int>(std::ceil((ToMm(max_y) - h_grid_.origin_y) / voxel_mm_));
    h_grid_.nz = static_cast<int>(std::ceil((ToMm(max_z) - h_grid_.origin_z) / voxel_mm_));
    if (h_grid_.nx <= 0 || h_grid_.ny <= 0 || h_grid_.nz <= 0) {
        throw std::runtime_error("VoxelGeometry calculated an empty voxel grid");
    }

    const std::size_t n_voxels = static_cast<std::size_t>(h_grid_.nx) *
                                 static_cast<std::size_t>(h_grid_.ny) *
                                 static_cast<std::size_t>(h_grid_.nz);
    host_material_ids_.assign(n_voxels, 0);
    host_volume_ids_.assign(n_voxels, 0);

    G4Navigator navigator;
    navigator.SetWorldVolume(world);
    for (int iz = 0; iz < h_grid_.nz; ++iz) {
        const float z = h_grid_.origin_z + (static_cast<float>(iz) + 0.5f) * voxel_mm_;
        for (int iy = 0; iy < h_grid_.ny; ++iy) {
            const float y = h_grid_.origin_y + (static_cast<float>(iy) + 0.5f) * voxel_mm_;
            for (int ix = 0; ix < h_grid_.nx; ++ix) {
                const float x = h_grid_.origin_x + (static_cast<float>(ix) + 0.5f) * voxel_mm_;
                auto* volume = navigator.LocateGlobalPointAndSetup(
                    G4ThreeVector(x * mm, y * mm, z * mm), nullptr, false, true);
                const auto* material = volume && volume->GetLogicalVolume()
                    ? volume->GetLogicalVolume()->GetMaterial()
                    : nullptr;
                const int mat_id = MaterialIndexFor(material);
                const int vol_id = VolumeIndexFor(volume);
                const int flat = FlatIndex(ix, iy, iz);
                host_material_ids_[flat] = static_cast<std::uint8_t>(mat_id);
                host_volume_ids_[flat] = static_cast<std::uint16_t>(vol_id);
            }
        }
    }

    h_grid_.material_id = host_material_ids_.data();
    h_grid_.volume_id = host_volume_ids_.data();
    CopyToDevice();
    built_ = true;
}

int VoxelGeometry::MaterialIdAtHost(float3 pos) const noexcept {
    if (!built_) return -1;
    const int ix = static_cast<int>(std::floor((pos.x - h_grid_.origin_x) / h_grid_.voxel_size));
    const int iy = static_cast<int>(std::floor((pos.y - h_grid_.origin_y) / h_grid_.voxel_size));
    const int iz = static_cast<int>(std::floor((pos.z - h_grid_.origin_z) / h_grid_.voxel_size));
    if (ix < 0 || iy < 0 || iz < 0 || ix >= h_grid_.nx || iy >= h_grid_.ny || iz >= h_grid_.nz) {
        return -1;
    }
    return host_material_ids_[FlatIndex(ix, iy, iz)];
}

int VoxelGeometry::VolumeIdAtHost(float3 pos) const noexcept {
    if (!built_) return -1;
    const int ix = static_cast<int>(std::floor((pos.x - h_grid_.origin_x) / h_grid_.voxel_size));
    const int iy = static_cast<int>(std::floor((pos.y - h_grid_.origin_y) / h_grid_.voxel_size));
    const int iz = static_cast<int>(std::floor((pos.z - h_grid_.origin_z) / h_grid_.voxel_size));
    if (ix < 0 || iy < 0 || iz < 0 || ix >= h_grid_.nx || iy >= h_grid_.ny || iz >= h_grid_.nz) {
        return -1;
    }
    return host_volume_ids_[FlatIndex(ix, iy, iz)];
}

float VoxelGeometry::DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) {
    next_vol = -1;
    if (!built_ || !d_grid_.material_id) return std::numeric_limits<float>::infinity();
    return LaunchDistanceToNextVoxelBoundary(pos, dir, d_grid_, next_vol);
}

int VoxelGeometry::FlatIndex(int ix, int iy, int iz) const noexcept {
    return (iz * h_grid_.ny + iy) * h_grid_.nx + ix;
}

int VoxelGeometry::MaterialIndexFor(const G4Material* material) {
    if (!material) return 0;
    const auto found = std::find(material_keys_.begin(), material_keys_.end(), material);
    if (found != material_keys_.end()) {
        return static_cast<int>(std::distance(material_keys_.begin(), found));
    }
    if (material_keys_.size() >= 64) {
        throw std::runtime_error("VoxelGeometry supports at most 64 materials per grid");
    }
    material_keys_.push_back(material);
    materials_.push_back(ToMaterialData(*material));
    return static_cast<int>(materials_.size() - 1);
}


int VoxelGeometry::VolumeIndexFor(const G4VPhysicalVolume* volume) {
    if (!volume) return 0;
    const auto found = std::find(volume_keys_.begin(), volume_keys_.end(), volume);
    if (found != volume_keys_.end()) {
        return static_cast<int>(std::distance(volume_keys_.begin(), found));
    }
    if (volume_keys_.size() >= std::numeric_limits<std::uint16_t>::max()) {
        throw std::runtime_error("VoxelGeometry supports at most 65535 volumes per grid");
    }
    volume_keys_.push_back(volume);
    return static_cast<int>(volume_keys_.size() - 1);
}

void VoxelGeometry::CopyToDevice() {
    ReleaseDevice();
    const std::size_t n_voxels = host_material_ids_.size();
    d_grid_ = h_grid_;
    d_grid_.material_id = nullptr;
    d_grid_.volume_id = nullptr;
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_grid_.material_id),
                         n_voxels * sizeof(std::uint8_t)),
              "cudaMalloc voxel material_id");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_grid_.volume_id),
                         n_voxels * sizeof(std::uint16_t)),
              "cudaMalloc voxel volume_id");
    CheckCuda(cudaMemcpy(d_grid_.material_id, host_material_ids_.data(),
                         n_voxels * sizeof(std::uint8_t), cudaMemcpyHostToDevice),
              "cudaMemcpy voxel material_id");
    CheckCuda(cudaMemcpy(d_grid_.volume_id, host_volume_ids_.data(),
                         n_voxels * sizeof(std::uint16_t), cudaMemcpyHostToDevice),
              "cudaMemcpy voxel volume_id");
    UploadVoxelMaterials(materials_.data(), static_cast<int>(materials_.size()));
    UploadActiveVoxelGrid(d_grid_);
}

void VoxelGeometry::ReleaseDevice() noexcept {
    if (d_grid_.material_id) cudaFree(d_grid_.material_id);
    if (d_grid_.volume_id) cudaFree(d_grid_.volume_id);
    d_grid_ = {};
}

void VoxelGeometry::ResetGrid() noexcept {
    ReleaseDevice();
    built_ = false;
    world_ = nullptr;
    h_grid_ = {};
    d_grid_ = {};
    host_material_ids_.clear();
    host_volume_ids_.clear();
    material_keys_.clear();
    volume_keys_.clear();
    materials_.clear();
}

}  // namespace g4gpu
