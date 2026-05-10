#pragma once

#include "g4gpu/G4GPUCudaCompat.hh"

namespace g4gpu {

struct MaterialData {
    float Z_over_A;    // Z/A (dimensionless)
    float I;           // mean excitation energy (MeV)
    float density;     // g/cm^3
    float X0;          // radiation length (mm)
    char name[32];     // human-readable
};

#if defined(__CUDACC__) && defined(G4GPU_DEFINE_MATERIAL_CONSTANTS)
__constant__ MaterialData d_materials[64];
#endif

MaterialData MakeIronMaterial() noexcept;
void UploadDefaultMaterials(cudaStream_t stream = nullptr);

}  // namespace g4gpu
