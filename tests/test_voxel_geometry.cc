#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>
#include <random>

#include "g4gpu/VoxelGeometry.hh"

#include <G4Box.hh>
#include <G4GeometryManager.hh>
#include <G4LogicalVolume.hh>
#include <G4Material.hh>
#include <G4Navigator.hh>
#include <G4Orb.hh>
#include <G4PVPlacement.hh>
#include <G4SystemOfUnits.hh>
#include <G4ThreeVector.hh>

namespace {

constexpr float kWorldHalfMm = 50.0f;
constexpr float kSphereRadiusMm = 10.0f;
constexpr float kVoxelMm = 2.0f;
constexpr int kSamples = 10000;

bool SameMaterialName(const g4gpu::VoxelGeometry& geometry,
                      int material_id,
                      const G4Material* expected) {
    if (!expected || material_id < 0) return false;
    const auto& materials = geometry.materials();
    if (static_cast<std::size_t>(material_id) >= materials.size()) return false;
    return std::strncmp(materials[material_id].name,
                        expected->GetName().c_str(),
                        sizeof(materials[material_id].name)) == 0;
}

bool BoundarySample(float x, float y, float z) {
    const float r = std::sqrt(x * x + y * y + z * z);
    const float sphere_band = std::abs(r - kSphereRadiusMm);
    const float world_band = kWorldHalfMm - std::max({std::abs(x), std::abs(y), std::abs(z)});
    return sphere_band <= kVoxelMm || world_band <= kVoxelMm;
}

G4VPhysicalVolume* BuildWorld() {
    G4GeometryManager::GetInstance()->OpenGeometry();
    auto* vacuum = new G4Material("voxel_vacuum", 1.0, 1.01 * g / mole,
                                  1.0e-25 * g / cm3, kStateGas,
                                  2.73 * kelvin, 3.0e-18 * pascal);
    auto* iron = new G4Material("voxel_iron", 26.0, 55.845 * g / mole,
                                7.874 * g / cm3);
    auto* world_solid = new G4Box("world", kWorldHalfMm * mm,
                                  kWorldHalfMm * mm, kWorldHalfMm * mm);
    auto* world_log = new G4LogicalVolume(world_solid, vacuum, "world_log");
    auto* world = new G4PVPlacement(nullptr, {}, world_log, "world_phys",
                                    nullptr, false, 0, true);
    auto* sphere = new G4Orb("iron_sphere", kSphereRadiusMm * mm);
    auto* sphere_log = new G4LogicalVolume(sphere, iron, "iron_log");
    new G4PVPlacement(nullptr, {}, sphere_log, "iron_phys",
                      world_log, false, 0, true);
    G4GeometryManager::GetInstance()->CloseGeometry();
    return world;
}

}  // namespace

int main() {
    auto* world = BuildWorld();
    g4gpu::VoxelGeometry geometry(kVoxelMm);
    geometry.Build(world);

    G4Navigator navigator;
    navigator.SetWorldVolume(world);
    std::mt19937 rng(12345);
    std::uniform_real_distribution<float> uniform(-kWorldHalfMm + 0.5f,
                                                  kWorldHalfMm - 0.5f);

    int disagreements = 0;
    int boundary_disagreements = 0;
    int boundary_samples = 0;
    for (int i = 0; i < kSamples; ++i) {
        const float x = uniform(rng);
        const float y = uniform(rng);
        const float z = uniform(rng);
        const bool boundary = BoundarySample(x, y, z);
        boundary_samples += boundary ? 1 : 0;
        auto* exact_volume = navigator.LocateGlobalPointAndSetup(
            G4ThreeVector(x * mm, y * mm, z * mm), nullptr, false, true);
        const int material_id = geometry.MaterialIdAtHost(float3{x, y, z});
        if (!SameMaterialName(geometry, material_id, exact_volume->GetLogicalVolume()->GetMaterial())) {
            if (boundary) {
                ++boundary_disagreements;
            } else {
                ++disagreements;
            }
        }
    }

    if (disagreements != 0) {
        std::cerr << "FAIL: interior disagreements=" << disagreements
                  << ", boundary disagreements=" << boundary_disagreements
                  << ", boundary samples=" << boundary_samples << '\n';
        return 1;
    }
    std::cout << "PASS: interior disagreements=0, boundary disagreements="
              << boundary_disagreements << ", samples=" << kSamples << '\n';
    return 0;
}
