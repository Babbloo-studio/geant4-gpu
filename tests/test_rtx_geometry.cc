#include <cmath>
#include <iostream>
#include <limits>

#include "g4gpu/RTXGeometry.hh"

#if defined(G4GPU_WITH_RTX)
#include <G4Box.hh>
#include <G4GeometryManager.hh>
#include <G4LogicalVolume.hh>
#include <G4Material.hh>
#include <G4PVPlacement.hh>
#include <G4SystemOfUnits.hh>

namespace {

G4VPhysicalVolume* BuildBoxWorld() {
    G4GeometryManager::GetInstance()->OpenGeometry();
    auto* vacuum = new G4Material("rtx_vacuum", 1.0, 1.01 * g / mole,
                                  1.0e-25 * g / cm3, kStateGas,
                                  2.73 * kelvin, 3.0e-18 * pascal);
    auto* solid = new G4Box("rtx_world", 10.0 * mm, 10.0 * mm, 10.0 * mm);
    auto* logical = new G4LogicalVolume(solid, vacuum, "rtx_world_log");
    auto* world = new G4PVPlacement(nullptr, {}, logical, "rtx_world_phys",
                                    nullptr, false, 0, true);
    G4GeometryManager::GetInstance()->CloseGeometry();
    return world;
}

bool Nearly(float actual, float expected, float tolerance) {
    return std::isfinite(actual) && std::fabs(actual - expected) <= tolerance;
}

}  // namespace
#endif

int main() {
#if !defined(G4GPU_WITH_RTX)
    std::cout << "SKIP: RTX backend not compiled\n";
    return 0;
#else
    g4gpu::RTXGeometry geometry;
    geometry.Build(BuildBoxWorld());

    if (!geometry.built()) {
        std::cerr << "FAIL: RTXGeometry did not report built() after Build()\n";
        return 1;
    }
    if (geometry.TriangleCount() != 12) {
        std::cerr << "FAIL: expected 12 world-box triangles, got "
                  << geometry.TriangleCount() << '\n';
        return 1;
    }

    int next_volume = -99;
    const float d = geometry.DistanceToNextBoundary(float3{0.0f, 0.0f, 0.0f},
                                                    float3{1.0f, 0.0f, 0.0f},
                                                    next_volume);
    if (!Nearly(d, 10.0f, 1.0e-2f)) {
        std::cerr << "FAIL: +x boundary distance expected 10 mm, got " << d
                  << ", next_volume=" << next_volume << '\n';
        return 1;
    }
    if (next_volume < 0) {
        std::cerr << "FAIL: next_volume was not populated\n";
        return 1;
    }

    std::cout << "PASS: RTX box boundary distance=" << d
              << " mm, next_volume=" << next_volume << '\n';
    return 0;
#endif
}
