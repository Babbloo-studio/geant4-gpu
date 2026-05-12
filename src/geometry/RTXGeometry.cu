#include "g4gpu/RTXGeometry.hh"

#if defined(G4GPU_WITH_RTX)
#include <cuda_runtime.h>
#include <math_constants.h>
#include <optix.h>

extern "C" {
__constant__ g4gpu::RTXLaunchParams params;
}

extern "C" __global__ void __raygen__boundary_query() {
    unsigned int distance_bits = __float_as_uint(CUDART_INF_F);
    unsigned int volume_bits = 0xffffffffu;
    optixTrace(params.handle, params.origin, params.direction,
               1.0e-4f, 1.0e20f, 0.0f,
               OptixVisibilityMask(255), OPTIX_RAY_FLAG_NONE,
               0, 1, 0, distance_bits, volume_bits);
    *params.distance = __uint_as_float(distance_bits);
    *params.volume_id = static_cast<int>(volume_bits);
}

extern "C" __global__ void __closesthit__record_boundary() {
    const auto* data = reinterpret_cast<const g4gpu::RTXHitGroupData*>(optixGetSbtDataPointer());
    optixSetPayload_0(__float_as_uint(optixGetRayTmax()));
    optixSetPayload_1(static_cast<unsigned int>(data->volume_id));
}

extern "C" __global__ void __miss__no_boundary() {
    optixSetPayload_0(__float_as_uint(CUDART_INF_F));
    optixSetPayload_1(0xffffffffu);
}
#endif
