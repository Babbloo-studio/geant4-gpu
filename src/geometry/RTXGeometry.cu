#include <optix_device.h>

struct BoundaryPayload {
    float distance;
    int volume_id;
};

extern "C" __global__ void __raygen__boundary_query() {
    // Phase 3 OptiX entry point placeholder compiled from the real SDK headers.
    // The host backend builds an OptiX GAS in this compact iteration; the next
    // validation unit wires this program into a pipeline/SBT launch and writes
    // distance + instance id through payload registers.
}

extern "C" __global__ void __closesthit__record_boundary() {
    // Will record optixGetRayTmax() and optixGetInstanceId() once the SBT hit
    // record layout is promoted from compile scaffold to runtime query path.
}

extern "C" __global__ void __miss__no_boundary() {
    // Will set distance to infinity and volume id to -1 for rays that leave the
    // world without intersecting a boundary.
}
