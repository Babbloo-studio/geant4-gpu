#include "g4gpu/RTXGeometry.hh"

#if defined(G4GPU_WITH_RTX)
#include "g4gpu/G4GPUCudaCompat.hh"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

#include <cuda_runtime_api.h>
#include <vector_types.h>

#include <G4Box.hh>
#include <G4LogicalVolume.hh>
#include <G4SystemOfUnits.hh>
#include <G4Tubs.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VSolid.hh>

#include <optix_function_table_definition.h>
#include <optix_stubs.h>

namespace g4gpu {
namespace {

float3 V(float x, float y, float z) { return float3{x, y, z}; }
float3 Sub(float3 a, float3 b) { return V(a.x - b.x, a.y - b.y, a.z - b.z); }
float Dot(float3 a, float3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
float3 Cross(float3 a, float3 b) {
    return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z,
             a.x * b.y - a.y * b.x);
}

bool Intersect(float3 o, float3 d, const RTXTriangle& t, float& dist) {
    const float3 e1 = Sub(t.v1, t.v0);
    const float3 e2 = Sub(t.v2, t.v0);
    const float3 p = Cross(d, e2);
    const float det = Dot(e1, p);
    if (std::fabs(det) < 1.0e-7f) return false;
    const float inv = 1.0f / det;
    const float3 s = Sub(o, t.v0);
    const float u = inv * Dot(s, p);
    if (u < 0.0f || u > 1.0f) return false;
    const float3 q = Cross(s, e1);
    const float v = inv * Dot(d, q);
    if (v < 0.0f || u + v > 1.0f) return false;
    dist = inv * Dot(e2, q);
    return dist > 1.0e-5f;
}

}  // namespace

RTXGeometry::RTXGeometry() = default;
RTXGeometry::~RTXGeometry() { Reset(); }

void RTXGeometry::Reset() noexcept {
    if (d_vertices_) cudaFree(reinterpret_cast<void*>(d_vertices_));
    if (d_indices_) cudaFree(reinterpret_cast<void*>(d_indices_));
    if (d_gas_buffer_) cudaFree(reinterpret_cast<void*>(d_gas_buffer_));
    if (context_) optixDeviceContextDestroy(context_);
    d_vertices_ = d_indices_ = d_gas_buffer_ = 0;
    gas_handle_ = 0;
    context_ = nullptr;
    built_ = false;
}

void RTXGeometry::InitOptiX() {
    CheckCuda(cudaFree(nullptr), "cuda context initialization");
    const OptixResult init = optixInit();
    if (init != OPTIX_SUCCESS) throw std::runtime_error("optixInit failed");
    OptixDeviceContextOptions options{};
    options.logCallbackLevel = 2;
    if (optixDeviceContextCreate(nullptr, &options, &context_) != OPTIX_SUCCESS) {
        throw std::runtime_error("optixDeviceContextCreate failed");
    }
}

void RTXGeometry::AddTriangle(float3 a, float3 b, float3 c, int volume_id) {
    triangles_.push_back(RTXTriangle{a, b, c, volume_id});
}

void RTXGeometry::CollectVolume(const G4VPhysicalVolume* volume, int depth) {
    if (!volume || !volume->GetLogicalVolume()) return;
    const int volume_id = static_cast<int>(triangles_.size() + depth + 1);
    const auto* solid = volume->GetLogicalVolume()->GetSolid();
    const auto tr = volume->GetObjectTranslation() / mm;
    auto make = [&](G4double x, G4double y, G4double z) {
        return V(static_cast<float>(x / mm + tr.x()),
                 static_cast<float>(y / mm + tr.y()),
                 static_cast<float>(z / mm + tr.z()));
    };
    if (const auto* box = dynamic_cast<const G4Box*>(solid)) {
        const G4double x = box->GetXHalfLength(), y = box->GetYHalfLength();
        const G4double z = box->GetZHalfLength();
        const float3 p[8] = {make(-x,-y,-z), make(x,-y,-z), make(x,y,-z), make(-x,y,-z),
                             make(-x,-y,z), make(x,-y,z), make(x,y,z), make(-x,y,z)};
        const int f[12][3] = {{0,1,2},{0,2,3},{4,6,5},{4,7,6},{0,4,5},{0,5,1},
                              {1,5,6},{1,6,2},{2,6,7},{2,7,3},{3,7,4},{3,4,0}};
        for (auto& tri : f) AddTriangle(p[tri[0]], p[tri[1]], p[tri[2]], volume_id);
    } else if (const auto* tubs = dynamic_cast<const G4Tubs*>(solid)) {
        constexpr int n = 32;
        const G4double r = tubs->GetOuterRadius(), hz = tubs->GetZHalfLength();
        for (int i = 0; i < n; ++i) {
            const double a0 = 2.0 * M_PI * i / n, a1 = 2.0 * M_PI * (i + 1) / n;
            const float3 b0 = make(r * std::cos(a0), r * std::sin(a0), -hz);
            const float3 b1 = make(r * std::cos(a1), r * std::sin(a1), -hz);
            const float3 t0 = make(r * std::cos(a0), r * std::sin(a0), hz);
            const float3 t1 = make(r * std::cos(a1), r * std::sin(a1), hz);
            AddTriangle(b0, b1, t1, volume_id); AddTriangle(b0, t1, t0, volume_id);
            AddTriangle(make(0,0,-hz), b1, b0, volume_id);
            AddTriangle(make(0,0,hz), t0, t1, volume_id);
        }
    }
    for (int i = 0; i < volume->GetLogicalVolume()->GetNoDaughters(); ++i) {
        CollectVolume(volume->GetLogicalVolume()->GetDaughter(i), depth + 1);
    }
}

void RTXGeometry::BuildGAS() {
    if (triangles_.empty()) return;
    InitOptiX();
    std::vector<float3> vertices;
    std::vector<uint3> indices;
    vertices.reserve(triangles_.size() * 3);
    for (const auto& tri : triangles_) {
        const unsigned int base = static_cast<unsigned int>(vertices.size());
        vertices.push_back(tri.v0); vertices.push_back(tri.v1); vertices.push_back(tri.v2);
        indices.push_back(uint3{base, base + 1, base + 2});
    }
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_vertices_),
                         vertices.size() * sizeof(float3)), "cudaMalloc RTX vertices");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_indices_),
                         indices.size() * sizeof(uint3)), "cudaMalloc RTX indices");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_vertices_), vertices.data(),
                         vertices.size() * sizeof(float3), cudaMemcpyHostToDevice),
              "cudaMemcpy RTX vertices");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_indices_), indices.data(),
                         indices.size() * sizeof(uint3), cudaMemcpyHostToDevice),
              "cudaMemcpy RTX indices");
    uint32_t flags = OPTIX_GEOMETRY_FLAG_NONE;
    OptixBuildInput input{};
    input.type = OPTIX_BUILD_INPUT_TYPE_TRIANGLES;
    input.triangleArray.vertexFormat = OPTIX_VERTEX_FORMAT_FLOAT3;
    input.triangleArray.vertexStrideInBytes = sizeof(float3);
    input.triangleArray.numVertices = static_cast<unsigned int>(vertices.size());
    input.triangleArray.vertexBuffers = &d_vertices_;
    input.triangleArray.indexFormat = OPTIX_INDICES_FORMAT_UNSIGNED_INT3;
    input.triangleArray.indexStrideInBytes = sizeof(uint3);
    input.triangleArray.numIndexTriplets = static_cast<unsigned int>(indices.size());
    input.triangleArray.indexBuffer = d_indices_;
    input.triangleArray.flags = &flags;
    input.triangleArray.numSbtRecords = 1;
    OptixAccelBuildOptions options{};
    options.buildFlags = OPTIX_BUILD_FLAG_ALLOW_COMPACTION;
    options.operation = OPTIX_BUILD_OPERATION_BUILD;
    OptixAccelBufferSizes sizes{};
    optixAccelComputeMemoryUsage(context_, &options, &input, 1, &sizes);
    CUdeviceptr temp = 0;
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&temp), sizes.tempSizeInBytes),
              "cudaMalloc RTX GAS temp");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_gas_buffer_), sizes.outputSizeInBytes),
              "cudaMalloc RTX GAS output");
    optixAccelBuild(context_, 0, &options, &input, 1, temp, sizes.tempSizeInBytes,
                    d_gas_buffer_, sizes.outputSizeInBytes, &gas_handle_, nullptr, 0);
    cudaFree(reinterpret_cast<void*>(temp));
}

void RTXGeometry::Build(G4VPhysicalVolume* world) {
    Reset();
    if (!world) throw std::invalid_argument("RTXGeometry::Build requires world volume");
    triangles_.clear();
    CollectVolume(world, 0);
    BuildGAS();
    built_ = true;
}

float RTXGeometry::DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) {
    next_vol = -1;
    float best = std::numeric_limits<float>::infinity();
    for (const auto& tri : triangles_) {
        float t = 0.0f;
        if (Intersect(pos, dir, tri, t) && t < best) { best = t; next_vol = tri.volume_id; }
    }
    return best;
}

}  // namespace g4gpu
#endif
