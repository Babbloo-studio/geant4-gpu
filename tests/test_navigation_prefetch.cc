#include "g4gpu/NavigationPrefetch.hh"

#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    constexpr int nx = 24;
    constexpr int ny = 20;
    constexpr int nz = 18;
    std::vector<std::uint8_t> material(static_cast<std::size_t>(nx * ny * nz));
    std::vector<std::uint16_t> volume(material.size());
    for (int iz = 0; iz < nz; ++iz) {
        for (int iy = 0; iy < ny; ++iy) {
            for (int ix = 0; ix < nx; ++ix) {
                const auto flat = static_cast<std::size_t>((iz * ny + iy) * nx + ix);
                material[flat] = static_cast<std::uint8_t>((ix + 3 * iy + 5 * iz) & 0x3f);
                volume[flat] = static_cast<std::uint16_t>(1 + ix / 4 + 16 * (iy / 5) + 96 * (iz / 6));
            }
        }
    }
    const g4gpu::NavigationGrid grid{nx, ny, nz, material.data(), volume.data()};
    std::vector<g4gpu::NavigationRay> rays;
    for (int i = 0; i < 512; ++i) {
        rays.push_back({
            1.5f + static_cast<float>((i * 7) % (nx - 3)),
            1.5f + static_cast<float>((i * 5) % (ny - 3)),
            1.5f + static_cast<float>((i * 3) % (nz - 3)),
            0.19f + 0.01f * static_cast<float>(i % 11),
            -0.13f + 0.02f * static_cast<float>(i % 7),
            0.29f + 0.01f * static_cast<float>(i % 5),
        });
    }
    std::vector<int> reference(rays.size());
    std::vector<int> prefetch(rays.size());
    for (std::size_t i = 0; i < rays.size(); ++i) {
        reference[i] = g4gpu::WalkTouchableReference(grid, rays[i], 96);
        prefetch[i] = g4gpu::WalkTouchablePrefetch(grid, rays[i], 96);
    }
    assert(reference == prefetch);
    g4gpu::WalkTouchableBatch(grid, rays.data(), prefetch.data(), rays.size(), 96);
    assert(reference == prefetch);
    std::cout << "PASS: navigation prefetch backend="
              << g4gpu::NavigationPrefetchBackend()
              << ", rays=" << rays.size() << '\n';
    return 0;
}
