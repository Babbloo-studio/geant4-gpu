#pragma once

#include <cstddef>

namespace g4gpu {

struct alignas(64) Track {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float dx = 0.0f;
    float dy = 0.0f;
    float dz = 1.0f;
    float ekin = 0.0f;
    float time = 0.0f;
    int pdg = 0;
    int material_idx = -1;
    int volume_idx = -1;
    int track_id = 0;
    int parent_id = 0;
    int status = 0;
    float weight = 1.0f;
    float padding = 0.0f;
};

struct PackedTrack {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float dx = 0.0f;
    float dy = 0.0f;
    float dz = 1.0f;
    float ekin = 0.0f;
    float time = 0.0f;
    int pdg = 0;
    int material_idx = -1;
    int volume_idx = -1;
    int track_id = 0;
    int parent_id = 0;
    int status = 0;
} __attribute__((packed));

static_assert(alignof(Track) == 64, "Track must be cache-line aligned");
static_assert(sizeof(Track) % 64 == 0, "Track size must be a cache-line multiple");

void FillTrack(Track& out, int index, float seed) noexcept;
void FillPackedTrack(PackedTrack& out, int index, float seed) noexcept;

double AccumulateAlignedTrackKinematics(const Track* tracks, std::size_t count) noexcept;
double AccumulatePackedTrackKinematics(const PackedTrack* tracks, std::size_t count) noexcept;

const char* TrackLayoutBackend() noexcept;

}  // namespace g4gpu
