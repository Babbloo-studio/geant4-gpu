#include "g4gpu/RTXGeometry.hh"
#if defined(G4GPU_WITH_RTX)
#include <array>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
#include <cuda_runtime_api.h>
#include <optix_function_table_definition.h>
#include <optix_stack_size.h>
#include <optix_stubs.h>
#include <G4AffineTransform.hh>
#include <G4Box.hh>
#include <G4LogicalVolume.hh>
#include <G4SystemOfUnits.hh>
#include <G4VPhysicalVolume.hh>
#include <G4VSolid.hh>
#include <G4VoxelLimits.hh>
#include <geomdefs.hh>
namespace g4gpu { namespace {
template <typename T> struct alignas(OPTIX_SBT_RECORD_ALIGNMENT) SbtRecord { char header[OPTIX_SBT_RECORD_HEADER_SIZE]{}; T data{}; };
struct EmptyData {};
void CheckOptix(OptixResult result, const char* what) {
    if (result != OPTIX_SUCCESS) throw std::runtime_error(std::string(what) + ": OptiX error " + std::to_string(result));
}
float ToMm(G4double value) { return static_cast<float>(value / mm); }
std::string ReadTextFile(const char* path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error(std::string("failed to open RTX PTX file: ") + path);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
std::array<float, 6> SolidBoundsMm(const G4VSolid& solid) {
    G4VoxelLimits limits;
    G4AffineTransform transform;
    G4double min_x = 0, max_x = 0, min_y = 0, max_y = 0, min_z = 0, max_z = 0;
    if (!solid.CalculateExtent(kXAxis, limits, transform, min_x, max_x) || !solid.CalculateExtent(kYAxis, limits, transform, min_y, max_y) ||
        !solid.CalculateExtent(kZAxis, limits, transform, min_z, max_z)) throw std::runtime_error("RTXGeometry failed to calculate solid extent");
    return {ToMm(min_x), ToMm(max_x), ToMm(min_y), ToMm(max_y), ToMm(min_z), ToMm(max_z)};
}
void AddBoxTriangles(const std::array<float, 6>& b, std::vector<float3>& v) {
    const float x0 = b[0], x1 = b[1], y0 = b[2], y1 = b[3], z0 = b[4], z1 = b[5];
    const std::array<float3, 8> p{{{x0,y0,z0},{x1,y0,z0},{x1,y1,z0},{x0,y1,z0},
                                  {x0,y0,z1},{x1,y0,z1},{x1,y1,z1},{x0,y1,z1}}};
    const int f[12][3] = {{0,1,2},{0,2,3},{4,6,5},{4,7,6},{0,4,5},{0,5,1},
                          {1,5,6},{1,6,2},{2,6,7},{2,7,3},{3,7,4},{3,4,0}};
    for (const auto& t : f) { v.push_back(p[t[0]]); v.push_back(p[t[1]]); v.push_back(p[t[2]]); }
}
std::vector<float3> MeshWorldSolid(G4VPhysicalVolume* world) {
    if (!world || !world->GetLogicalVolume() || !world->GetLogicalVolume()->GetSolid()) throw std::invalid_argument("RTXGeometry::Build requires a world volume with a solid");
    const auto* solid = world->GetLogicalVolume()->GetSolid();
    std::vector<float3> vertices;
    if (const auto* box = dynamic_cast<const G4Box*>(solid)) {
        AddBoxTriangles({-ToMm(box->GetXHalfLength()), ToMm(box->GetXHalfLength()),
                         -ToMm(box->GetYHalfLength()), ToMm(box->GetYHalfLength()),
                         -ToMm(box->GetZHalfLength()), ToMm(box->GetZHalfLength())}, vertices);
    } else {
        AddBoxTriangles(SolidBoundsMm(*solid), vertices);
    }
    return vertices;
}
} }
namespace g4gpu {
RTXGeometry::RTXGeometry() { InitContext(); }
RTXGeometry::~RTXGeometry() { Reset(); if (context_) optixDeviceContextDestroy(context_); }
void RTXGeometry::Build(G4VPhysicalVolume* world) {
    Reset(); BuildGas(world); BuildPipeline(); BuildSbt(); built_ = true;
}
float RTXGeometry::DistanceToNextBoundary(float3 pos, float3 dir, int& next_vol) {
    next_vol = -1;
    if (!built_) return std::numeric_limits<float>::infinity();
    return LaunchRTXDistanceToNextBoundary(pipeline_, sbt_, gas_handle_, pos, dir, next_vol);
}
void RTXGeometry::InitContext() {
    CheckCuda(cudaFree(nullptr), "cuda runtime init");
    CheckOptix(optixInit(), "optixInit");
    OptixDeviceContextOptions options{};
    options.logCallbackLevel = 2;
    CheckOptix(optixDeviceContextCreate(nullptr, &options, &context_), "optixDeviceContextCreate");
}
void RTXGeometry::BuildGas(G4VPhysicalVolume* world) {
    auto vertices = MeshWorldSolid(world);
    triangle_count_ = vertices.size() / 3;
    CUdeviceptr d_vertices = 0;
    const auto bytes = vertices.size() * sizeof(float3);
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_vertices), bytes), "cudaMalloc RTX vertices");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_vertices), vertices.data(), bytes, cudaMemcpyHostToDevice),
              "cudaMemcpy RTX vertices");
    const uint32_t flags[1] = {OPTIX_GEOMETRY_FLAG_NONE};
    OptixBuildInput input{};
    input.type = OPTIX_BUILD_INPUT_TYPE_TRIANGLES;
    input.triangleArray.vertexFormat = OPTIX_VERTEX_FORMAT_FLOAT3;
    input.triangleArray.numVertices = static_cast<uint32_t>(vertices.size());
    input.triangleArray.vertexBuffers = &d_vertices;
    input.triangleArray.flags = flags;
    input.triangleArray.numSbtRecords = 1;
    OptixAccelBuildOptions options{};
    options.buildFlags = OPTIX_BUILD_FLAG_NONE;
    options.operation = OPTIX_BUILD_OPERATION_BUILD;
    OptixAccelBufferSizes sizes{};
    CheckOptix(optixAccelComputeMemoryUsage(context_, &options, &input, 1, &sizes), "optixAccelComputeMemoryUsage");
    CUdeviceptr d_temp = 0;
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_temp), sizes.tempSizeInBytes), "cudaMalloc RTX temp");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_gas_buffer_), sizes.outputSizeInBytes), "cudaMalloc RTX GAS");
    CheckOptix(optixAccelBuild(context_, nullptr, &options, &input, 1, d_temp, sizes.tempSizeInBytes,
                               d_gas_buffer_, sizes.outputSizeInBytes, &gas_handle_, nullptr, 0), "optixAccelBuild");
    cudaFree(reinterpret_cast<void*>(d_temp));
    cudaFree(reinterpret_cast<void*>(d_vertices));
}
void RTXGeometry::BuildPipeline() {
    OptixModuleCompileOptions module_options{};
    module_options.optLevel = OPTIX_COMPILE_OPTIMIZATION_DEFAULT;
    module_options.debugLevel = OPTIX_COMPILE_DEBUG_LEVEL_MINIMAL;
    OptixPipelineCompileOptions compile_options{};
    compile_options.traversableGraphFlags = OPTIX_TRAVERSABLE_GRAPH_FLAG_ALLOW_SINGLE_GAS;
    compile_options.numPayloadValues = 2;
    compile_options.numAttributeValues = 2;
    compile_options.pipelineLaunchParamsVariableName = "params";
    compile_options.usesPrimitiveTypeFlags = OPTIX_PRIMITIVE_TYPE_FLAGS_TRIANGLE;
    auto ptx = ReadTextFile(G4GPU_RTX_PTX_PATH);
    char log[2048]; size_t log_size = sizeof(log);
    CheckOptix(optixModuleCreate(context_, &module_options, &compile_options, ptx.data(), ptx.size(),
                                 log, &log_size, &module_), "optixModuleCreate");
    OptixProgramGroupOptions pg_options{};
    OptixProgramGroupDesc rg{}; rg.kind = OPTIX_PROGRAM_GROUP_KIND_RAYGEN;
    rg.raygen.module = module_; rg.raygen.entryFunctionName = "__raygen__boundary_query";
    CheckOptix(optixProgramGroupCreate(context_, &rg, 1, &pg_options, log, &log_size, &raygen_group_), "create raygen");
    OptixProgramGroupDesc ms{}; ms.kind = OPTIX_PROGRAM_GROUP_KIND_MISS;
    ms.miss.module = module_; ms.miss.entryFunctionName = "__miss__no_boundary";
    CheckOptix(optixProgramGroupCreate(context_, &ms, 1, &pg_options, log, &log_size, &miss_group_), "create miss");
    OptixProgramGroupDesc hg{}; hg.kind = OPTIX_PROGRAM_GROUP_KIND_HITGROUP;
    hg.hitgroup.moduleCH = module_; hg.hitgroup.entryFunctionNameCH = "__closesthit__record_boundary";
    CheckOptix(optixProgramGroupCreate(context_, &hg, 1, &pg_options, log, &log_size, &hit_group_), "create hit");
    OptixProgramGroup groups[] = {raygen_group_, miss_group_, hit_group_};
    OptixPipelineLinkOptions link_options{}; link_options.maxTraceDepth = 1;
    CheckOptix(optixPipelineCreate(context_, &compile_options, &link_options, groups, 3, log, &log_size, &pipeline_),
               "optixPipelineCreate");
    OptixStackSizes stack{};
    for (auto* group : groups) CheckOptix(optixUtilAccumulateStackSizes(group, &stack, pipeline_), "stack sizes");
    uint32_t dc_trav = 0, dc_state = 0, cont = 0;
    CheckOptix(optixUtilComputeStackSizes(&stack, 1, 0, 0, &dc_trav, &dc_state, &cont), "compute stack");
    CheckOptix(optixPipelineSetStackSize(pipeline_, dc_trav, dc_state, cont, 1), "set stack");
}
void RTXGeometry::BuildSbt() {
    SbtRecord<EmptyData> rg{}; SbtRecord<EmptyData> ms{}; SbtRecord<RTXHitGroupData> hg{};
    hg.data.volume_id = 0;
    CheckOptix(optixSbtRecordPackHeader(raygen_group_, &rg), "pack raygen");
    CheckOptix(optixSbtRecordPackHeader(miss_group_, &ms), "pack miss");
    CheckOptix(optixSbtRecordPackHeader(hit_group_, &hg), "pack hit");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_raygen_record_), sizeof(rg)), "malloc raygen SBT");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_miss_record_), sizeof(ms)), "malloc miss SBT");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_hit_record_), sizeof(hg)), "malloc hit SBT");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_raygen_record_), &rg, sizeof(rg), cudaMemcpyHostToDevice), "copy raygen SBT");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_miss_record_), &ms, sizeof(ms), cudaMemcpyHostToDevice), "copy miss SBT");
    CheckCuda(cudaMemcpy(reinterpret_cast<void*>(d_hit_record_), &hg, sizeof(hg), cudaMemcpyHostToDevice), "copy hit SBT");
    sbt_.raygenRecord = d_raygen_record_;
    sbt_.missRecordBase = d_miss_record_; sbt_.missRecordStrideInBytes = sizeof(ms); sbt_.missRecordCount = 1;
    sbt_.hitgroupRecordBase = d_hit_record_; sbt_.hitgroupRecordStrideInBytes = sizeof(hg); sbt_.hitgroupRecordCount = 1;
}
void RTXGeometry::Reset() noexcept {
    built_ = false; triangle_count_ = 0; gas_handle_ = 0; sbt_ = {};
    if (pipeline_) optixPipelineDestroy(pipeline_); pipeline_ = nullptr;
    if (raygen_group_) optixProgramGroupDestroy(raygen_group_); raygen_group_ = nullptr;
    if (miss_group_) optixProgramGroupDestroy(miss_group_); miss_group_ = nullptr;
    if (hit_group_) optixProgramGroupDestroy(hit_group_); hit_group_ = nullptr;
    if (module_) optixModuleDestroy(module_); module_ = nullptr;
    if (d_raygen_record_) cudaFree(reinterpret_cast<void*>(d_raygen_record_)); d_raygen_record_ = 0;
    if (d_miss_record_) cudaFree(reinterpret_cast<void*>(d_miss_record_)); d_miss_record_ = 0;
    if (d_hit_record_) cudaFree(reinterpret_cast<void*>(d_hit_record_)); d_hit_record_ = 0;
    if (d_gas_buffer_) cudaFree(reinterpret_cast<void*>(d_gas_buffer_)); d_gas_buffer_ = 0;
}
float LaunchRTXDistanceToNextBoundary(OptixPipeline pipeline, const OptixShaderBindingTable& sbt,
                                      OptixTraversableHandle handle, float3 pos, float3 dir,
                                      int& next_vol, cudaStream_t stream) {
    float* d_distance = nullptr; int* d_volume = nullptr; RTXLaunchParams* d_params = nullptr;
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_distance), sizeof(float)), "malloc RTX distance");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_volume), sizeof(int)), "malloc RTX volume");
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&d_params), sizeof(RTXLaunchParams)), "malloc RTX params");
    float inf = std::numeric_limits<float>::infinity(); int miss = -1;
    CheckCuda(cudaMemcpyAsync(d_distance, &inf, sizeof(float), cudaMemcpyHostToDevice, stream), "seed RTX distance");
    CheckCuda(cudaMemcpyAsync(d_volume, &miss, sizeof(int), cudaMemcpyHostToDevice, stream), "seed RTX volume");
    RTXLaunchParams params{handle, pos, dir, d_distance, d_volume};
    CheckCuda(cudaMemcpyAsync(d_params, &params, sizeof(params), cudaMemcpyHostToDevice, stream), "copy RTX params");
    CheckOptix(optixLaunch(pipeline, stream, reinterpret_cast<CUdeviceptr>(d_params), sizeof(params), &sbt, 1, 1, 1),
               "optixLaunch RTX distance");
    float distance = inf;
    CheckCuda(cudaMemcpyAsync(&distance, d_distance, sizeof(float), cudaMemcpyDeviceToHost, stream), "read RTX distance");
    CheckCuda(cudaMemcpyAsync(&next_vol, d_volume, sizeof(int), cudaMemcpyDeviceToHost, stream), "read RTX volume");
    CheckCuda(cudaStreamSynchronize(stream), "sync RTX distance");
    cudaFree(d_params); cudaFree(d_volume); cudaFree(d_distance);
    return distance;
}
}  // namespace g4gpu
#endif
