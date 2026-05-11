#include "g4gpu/Track.hh"

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

int main() {
    if (alignof(g4gpu::Track) != 64) {
        std::cerr << "FAIL: alignof(Track)=" << alignof(g4gpu::Track) << '\n';
        return 1;
    }
    if (sizeof(g4gpu::Track) % 64 != 0) {
        std::cerr << "FAIL: sizeof(Track)=" << sizeof(g4gpu::Track) << '\n';
        return 1;
    }
    std::vector<g4gpu::Track> aligned(4096);
    std::vector<g4gpu::PackedTrack> packed(4096);
    if (reinterpret_cast<std::uintptr_t>(aligned.data()) % 64 != 0) {
        std::cerr << "FAIL: vector<Track> data is not 64-byte aligned\n";
        return 1;
    }
    for (std::size_t i = 0; i < aligned.size(); ++i) {
        g4gpu::FillTrack(aligned[i], static_cast<int>(i), 0.5f);
        g4gpu::FillPackedTrack(packed[i], static_cast<int>(i), 0.5f);
    }
    const double a = g4gpu::AccumulateAlignedTrackKinematics(aligned.data(), aligned.size());
    const double p = g4gpu::AccumulatePackedTrackKinematics(packed.data(), packed.size());
    const double rel = std::abs(a - p) / std::max(1.0, std::abs(p));
    if (rel > 1.0e-12) {
        std::cerr << "FAIL: aligned/packed accumulation mismatch rel=" << rel << '\n';
        return 1;
    }
    std::cout << "PASS: alignof(Track)=" << alignof(g4gpu::Track)
              << ", sizeof(Track)=" << sizeof(g4gpu::Track)
              << ", backend=" << g4gpu::TrackLayoutBackend() << '\n';
    return 0;
}
