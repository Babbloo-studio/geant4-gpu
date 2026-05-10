#pragma once

#include <cstddef>
#include <stdexcept>
#include <string>

#if defined(__has_include)
#  if __has_include(<cuda_runtime_api.h>)
#    include <cuda_runtime_api.h>
#    include <vector_types.h>
#    define G4GPU_HAS_CUDA_RUNTIME 1
#  else
#    define G4GPU_HAS_CUDA_RUNTIME 0
#  endif
#else
#  include <cuda_runtime_api.h>
#  include <vector_types.h>
#  define G4GPU_HAS_CUDA_RUNTIME 1
#endif

#if !G4GPU_HAS_CUDA_RUNTIME
using cudaError_t = int;
using cudaStream_t = void*;
constexpr cudaError_t cudaSuccess = 0;
struct float3 { float x; float y; float z; };
#endif

namespace g4gpu {

inline void CheckCuda(cudaError_t err, const char* what) {
#if G4GPU_HAS_CUDA_RUNTIME
    if (err != cudaSuccess) {
        throw std::runtime_error(std::string(what) + ": " + cudaGetErrorString(err));
    }
#else
    (void)err;
    throw std::runtime_error(std::string(what) + ": CUDA runtime headers are unavailable");
#endif
}

}  // namespace g4gpu
