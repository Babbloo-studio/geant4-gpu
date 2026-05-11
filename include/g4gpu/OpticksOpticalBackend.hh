#pragma once

#include <cstddef>
#include <string>
#include <vector>

class G4VPhysicalVolume;

namespace g4gpu {

// Compact adapter contract for delegating optical photons to Opticks.
// Phase 4 intentionally keeps this API thin and CPU-fallback safe: if the
// project is built without Opticks, every method reports an explicit disabled
// status and leaves Geant4 CPU optical transport responsible for the photons.
struct OpticalGenstep {
    enum class Process {
        kScintillation,
        kCerenkov,
    };

    Process process = Process::kScintillation;
    int photon_count = 0;
    float x_mm = 0.0F;
    float y_mm = 0.0F;
    float z_mm = 0.0F;
    float time_ns = 0.0F;
    float wavelength_min_nm = 0.0F;
    float wavelength_max_nm = 0.0F;
};

struct OpticalHit {
    int detector_id = -1;
    float x_mm = 0.0F;
    float y_mm = 0.0F;
    float z_mm = 0.0F;
    float time_ns = 0.0F;
    float wavelength_nm = 0.0F;
    unsigned flags = 0U;
};

struct OpticksBackendStatus {
    bool requested = false;
    bool compiled_with_opticks = false;
    bool active = false;
    std::string reason;
};

class OpticksOpticalBackend {
  public:
    OpticksOpticalBackend();

    static bool CompiledWithOpticks() noexcept;

    bool Initialize(G4VPhysicalVolume* world);
    void Finalize() noexcept;

    void SetEnabled(bool enabled) noexcept;
    bool IsEnabled() const noexcept { return enabled_; }
    bool IsActive() const noexcept { return status_.active; }
    const OpticksBackendStatus& Status() const noexcept { return status_; }

    bool SubmitGenstep(const OpticalGenstep& genstep);
    std::vector<OpticalHit> Propagate();

    std::size_t PendingGensteps() const noexcept { return pending_gensteps_.size(); }
    int PendingPhotons() const noexcept { return pending_photons_; }

  private:
    void DisableWithReason(std::string reason) noexcept;

    bool enabled_ = true;
    OpticksBackendStatus status_{};
    std::vector<OpticalGenstep> pending_gensteps_;
    int pending_photons_ = 0;
};

}  // namespace g4gpu
