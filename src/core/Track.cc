#include "g4gpu/Track.hh"

#include <cmath>
#include <cstdlib>

namespace g4gpu {
namespace {

bool DisableAlignedTracks() noexcept {
    return std::getenv("G4GPU_TRACK_DISABLE_ALIGNED") != nullptr;
}

float TrackValue(int index, float seed) noexcept {
    return seed + 0.001f * static_cast<float>((index * 1103515245u + 12345u) & 0xffffu);
}

}  // namespace

void FillTrack(Track& out, int index, float seed) noexcept {
    const float v = TrackValue(index, seed);
    out.x = 0.1f * v;
    out.y = 0.2f * v;
    out.z = 0.3f * v;
    out.dx = std::sin(v);
    out.dy = std::cos(v);
    out.dz = 1.0f;
    out.ekin = 100.0f + v;
    out.time = 0.01f * v;
    out.pdg = (index & 1) ? 13 : -13;
    out.material_idx = index & 7;
    out.volume_idx = index & 15;
    out.track_id = index + 1;
    out.parent_id = 0;
    out.status = 0;
    out.weight = 1.0f;
    out.padding = 0.0f;
}

void FillPackedTrack(PackedTrack& out, int index, float seed) noexcept {
    Track tmp;
    FillTrack(tmp, index, seed);
    out.x = tmp.x;
    out.y = tmp.y;
    out.z = tmp.z;
    out.dx = tmp.dx;
    out.dy = tmp.dy;
    out.dz = tmp.dz;
    out.ekin = tmp.ekin;
    out.time = tmp.time;
    out.pdg = tmp.pdg;
    out.material_idx = tmp.material_idx;
    out.volume_idx = tmp.volume_idx;
    out.track_id = tmp.track_id;
    out.parent_id = tmp.parent_id;
    out.status = tmp.status;
}

__attribute__((noinline))
double AccumulatePackedTrackKinematics(const PackedTrack* tracks, std::size_t count) noexcept {
    if (!tracks) return 0.0;
    double sum = 0.0;
    for (std::size_t i = 0; i < count; ++i) {
        const auto& t = tracks[i];
        sum += static_cast<double>(t.ekin) * (0.25 + 0.001 * static_cast<double>(t.material_idx));
        sum += static_cast<double>(t.x * t.dx + t.y * t.dy + t.z * t.dz) * 1.0e-3;
        sum += static_cast<double>(t.time) * 0.01;
    }
    return sum;
}

double AccumulateAlignedTrackKinematics(const Track* tracks, std::size_t count) noexcept {
    if (!tracks) return 0.0;
#if defined(__GNUC__)
    tracks = static_cast<const Track*>(__builtin_assume_aligned(tracks, 64));
#endif
    double s0 = 0.0;
    double s1 = 0.0;
    double s2 = 0.0;
    double s3 = 0.0;
    std::size_t i = 0;
    for (; i + 4 <= count; i += 4) {
        const Track& a = tracks[i + 0];
        const Track& b = tracks[i + 1];
        const Track& c = tracks[i + 2];
        const Track& d = tracks[i + 3];
        s0 += static_cast<double>(a.ekin) * (0.25 + 0.001 * static_cast<double>(a.material_idx)) +
              static_cast<double>(a.x * a.dx + a.y * a.dy + a.z * a.dz) * 1.0e-3 +
              static_cast<double>(a.time) * 0.01;
        s1 += static_cast<double>(b.ekin) * (0.25 + 0.001 * static_cast<double>(b.material_idx)) +
              static_cast<double>(b.x * b.dx + b.y * b.dy + b.z * b.dz) * 1.0e-3 +
              static_cast<double>(b.time) * 0.01;
        s2 += static_cast<double>(c.ekin) * (0.25 + 0.001 * static_cast<double>(c.material_idx)) +
              static_cast<double>(c.x * c.dx + c.y * c.dy + c.z * c.dz) * 1.0e-3 +
              static_cast<double>(c.time) * 0.01;
        s3 += static_cast<double>(d.ekin) * (0.25 + 0.001 * static_cast<double>(d.material_idx)) +
              static_cast<double>(d.x * d.dx + d.y * d.dy + d.z * d.dz) * 1.0e-3 +
              static_cast<double>(d.time) * 0.01;
    }
    double sum = s0 + s1 + s2 + s3;
    for (; i < count; ++i) {
        const Track& t = tracks[i];
        sum += static_cast<double>(t.ekin) * (0.25 + 0.001 * static_cast<double>(t.material_idx));
        sum += static_cast<double>(t.x * t.dx + t.y * t.dy + t.z * t.dz) * 1.0e-3;
        sum += static_cast<double>(t.time) * 0.01;
    }
    return sum;
}

const char* TrackLayoutBackend() noexcept {
    return DisableAlignedTracks() ? "packed-reference" : "alignas64-track";
}

}  // namespace g4gpu
