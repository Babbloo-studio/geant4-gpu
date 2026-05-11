#include "g4gpu/OpticksOpticalBackend.hh"

#include <exception>
#include <string>
#include <utility>

#ifdef G4GPU_WITH_OPTICKS
#include "G4CXOpticks.hh"
#endif

namespace g4gpu {

OpticksOpticalBackend::OpticksOpticalBackend() {
    status_.requested = false;
    status_.compiled_with_opticks = CompiledWithOpticks();
    status_.active = false;
    status_.reason = CompiledWithOpticks()
                         ? "Opticks backend compiled; initialize with Geant4 world"
                         : "G4GPU_WITH_OPTICKS=OFF; CPU Geant4 optical fallback required";
}

bool OpticksOpticalBackend::CompiledWithOpticks() noexcept {
#ifdef G4GPU_WITH_OPTICKS
    return true;
#else
    return false;
#endif
}

bool OpticksOpticalBackend::Initialize(G4VPhysicalVolume* world) {
    status_.requested = true;
    status_.compiled_with_opticks = CompiledWithOpticks();
    if (!enabled_) {
        DisableWithReason("Opticks backend disabled at runtime; CPU fallback required");
        return false;
    }
    if (world == nullptr) {
        DisableWithReason("Opticks initialization requires a non-null Geant4 world volume");
        return false;
    }

#ifdef G4GPU_WITH_OPTICKS
    try {
        G4CXOpticks* opticks = G4CXOpticks::SetGeometry(world);
        if (opticks == nullptr) {
            DisableWithReason("G4CXOpticks::SetGeometry returned null; CPU fallback required");
            return false;
        }
        status_.active = true;
        status_.reason = "Opticks geometry initialized";
        return true;
    } catch (const std::exception& e) {
        DisableWithReason(std::string("Opticks initialization threw: ") + e.what());
        return false;
    } catch (...) {
        DisableWithReason("Opticks initialization threw an unknown exception");
        return false;
    }
#else
    DisableWithReason("G4GPU_WITH_OPTICKS=OFF; CPU Geant4 optical fallback required");
    return false;
#endif
}

void OpticksOpticalBackend::Finalize() noexcept {
    pending_gensteps_.clear();
    pending_photons_ = 0;
    status_.active = false;
    if (status_.reason.empty()) {
        status_.reason = "Opticks backend finalized";
    }
}

void OpticksOpticalBackend::SetEnabled(bool enabled) noexcept {
    enabled_ = enabled;
    if (!enabled_) {
        DisableWithReason("Opticks backend disabled at runtime; CPU fallback required");
    }
}

bool OpticksOpticalBackend::SubmitGenstep(const OpticalGenstep& genstep) {
    if (!status_.active || !enabled_) {
        return false;
    }
    if (genstep.photon_count <= 0) {
        return false;
    }
    pending_gensteps_.push_back(genstep);
    pending_photons_ += genstep.photon_count;
    return true;
}

std::vector<OpticalHit> OpticksOpticalBackend::Propagate() {
    if (!status_.active || pending_gensteps_.empty()) {
        return {};
    }

#ifdef G4GPU_WITH_OPTICKS
    // TODO Phase 4.2: translate OpticalGenstep records to Opticks genstep
    // buffers, call the Opticks event simulation entry point, and map returned
    // hits back to OpticalHit. Until that validation exists, keep the adapter
    // fail-closed and require CPU Geant4 optical transport for physics output.
    pending_gensteps_.clear();
    pending_photons_ = 0;
    status_.active = false;
    status_.reason = "Opticks propagation bridge is not validated; CPU fallback required";
    return {};
#else
    return {};
#endif
}

void OpticksOpticalBackend::DisableWithReason(std::string reason) noexcept {
    status_.active = false;
    status_.compiled_with_opticks = CompiledWithOpticks();
    status_.reason = std::move(reason);
}

}  // namespace g4gpu
