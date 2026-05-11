#include <cassert>
#include <iostream>
#include <string>

#include "g4gpu/OpticksOpticalBackend.hh"

int main() {
    g4gpu::OpticksOpticalBackend backend;
    assert(!backend.IsActive());
    assert(backend.PendingGensteps() == 0U);
    assert(backend.PendingPhotons() == 0);

#ifndef G4GPU_WITH_OPTICKS
    assert(!g4gpu::OpticksOpticalBackend::CompiledWithOpticks());
    assert(!backend.Status().compiled_with_opticks);
    const bool initialized = backend.Initialize(nullptr);
    assert(!initialized);
    assert(!backend.IsActive());
    assert(backend.Status().requested);
    assert(backend.Status().reason.find("CPU") != std::string::npos ||
           backend.Status().reason.find("Geant4") != std::string::npos);

    g4gpu::OpticalGenstep genstep;
    genstep.photon_count = 10;
    assert(!backend.SubmitGenstep(genstep));
    assert(backend.Propagate().empty());
#else
    assert(g4gpu::OpticksOpticalBackend::CompiledWithOpticks());
    assert(backend.Status().compiled_with_opticks);
    assert(!backend.Initialize(nullptr));
    assert(!backend.IsActive());
#endif

    backend.SetEnabled(false);
    assert(!backend.IsEnabled());
    assert(!backend.IsActive());

    std::cout << "PASS opticks fallback path\n";
    return 0;
}
