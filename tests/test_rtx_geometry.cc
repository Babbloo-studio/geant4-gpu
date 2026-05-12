#include <iostream>

#if defined(G4GPU_WITH_RTX)
#include "g4gpu/RTXGeometry.hh"

int main() {
    g4gpu::RTXGeometry geometry;
    if (geometry.built() || geometry.triangleCount() != 0) {
        std::cerr << "FAIL: fresh RTXGeometry should be unbuilt and empty\n";
        return 1;
    }
    std::cout << "PASS: RTX backend compiled with OptiX headers; runtime build "
                 "requires a Geant4 world on a GPU node\n";
    return 0;
}
#else
int main() {
    std::cout << "SKIP: RTX backend not compiled\n";
    return 0;
}
#endif
