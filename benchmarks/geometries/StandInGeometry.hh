#pragma once

#include <stdexcept>
#include <string>
#include <vector>

namespace g4gpu::benchmarks {

struct StandInGeometry {
    std::string id;
    std::string material;
    std::string extent;
    double density_g_cm3;
    double radiation_length_cm;
};

inline std::vector<StandInGeometry> AllStandInGeometries() {
    return {
        {"lead_block_1m3", "Pb", "1 m x 1 m x 1 m block", 11.34, 0.56},
        {"mip_tunnel_10m", "mixed_detector", "10 m straight detector stack", 1.20, 30420.0},
        {"carbon_12_target", "C12", "thin annihilation target at rest", 2.20, 18.8},
        {"cosmic_veto_stack", "plastic_scintillator", "cosmic-veto slab stack", 1.03, 42.0},
        {"scintillator_cell", "plastic_scintillator", "10 cm optical cell", 1.03, 42.0},
        {"b4c_beampipe", "B4C", "low-energy neutron absorber sleeve", 2.52, 19.9},
    };
}

inline const StandInGeometry& GeometryById(const std::string& id) {
    static const auto geometries = AllStandInGeometries();
    for (const auto& geometry : geometries) {
        if (geometry.id == id) {
            return geometry;
        }
    }
    throw std::invalid_argument("unknown G4GPU benchmark stand-in geometry: " + id);
}

}  // namespace g4gpu::benchmarks
