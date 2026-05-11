#include "g4gpu/VoxelGeometry.hh"

#include <cmath>
#include <limits>

#include <cuda_runtime.h>
#include <math_constants.h>

namespace g4gpu {

__constant__ VoxelGrid d_active_voxel_grid;

namespace {

constexpr float kEps = 1.0e-7f;
constexpr int kNoMaterial = -1;

__host__ __device__ float3 VoxelVec(float x, float y, float z) {
    return float3{x, y, z};
}

__device__ float Dot(float3 a, float3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

__device__ float3 Normalize(float3 v) {
    const float n2 = Dot(v, v);
    if (n2 <= 0.0f) return VoxelVec(0.0f, 0.0f, 1.0f);
    const float inv = rsqrtf(n2);
    return VoxelVec(v.x * inv, v.y * inv, v.z * inv);
}

__device__ int FlatIndex(const VoxelGrid grid, int ix, int iy, int iz) {
    return (iz * grid.ny + iy) * grid.nx + ix;
}

__device__ bool Inside(const VoxelGrid grid, int ix, int iy, int iz) {
    return ix >= 0 && iy >= 0 && iz >= 0 &&
           ix < grid.nx && iy < grid.ny && iz < grid.nz;
}

__device__ void InitAxis(float pos, float origin, float dir, int idx,
                         float voxel, int& step, float& t_max, float& t_delta) {
    if (dir > kEps) {
        step = 1;
        t_max = (origin + (static_cast<float>(idx) + 1.0f) * voxel - pos) / dir;
        t_delta = voxel / dir;
    } else if (dir < -kEps) {
        step = -1;
        t_max = (origin + static_cast<float>(idx) * voxel - pos) / dir;
        t_delta = -voxel / dir;
    } else {
        step = 0;
        t_max = CUDART_INF_F;
        t_delta = CUDART_INF_F;
    }
    if (t_max < 0.0f && t_max > -kEps) t_max = 0.0f;
}

__global__ void DistanceKernel(float3 pos, float3 dir, VoxelGrid grid,
                               float* distance, int* material_id) {
    *distance = DistanceToNextVoxelBoundary(pos, dir, grid, *material_id);
}

}  // namespace

__device__ bool ActiveVoxelGridAvailable() {
    return d_active_voxel_grid.material_id != nullptr &&
           d_active_voxel_grid.voxel_size > 0.0f &&
           d_active_voxel_grid.nx > 0 && d_active_voxel_grid.ny > 0 &&
           d_active_voxel_grid.nz > 0;
}

__device__ float DistanceToNextVoxelBoundary(
    float3 pos, float3 dir, const VoxelGrid grid, int& out_material_id) {
    out_material_id = kNoMaterial;
    if (!grid.material_id || grid.voxel_size <= 0.0f ||
        grid.nx <= 0 || grid.ny <= 0 || grid.nz <= 0) {
        return CUDART_INF_F;
    }

    dir = Normalize(dir);
    int ix = static_cast<int>(floorf((pos.x - grid.origin_x) / grid.voxel_size));
    int iy = static_cast<int>(floorf((pos.y - grid.origin_y) / grid.voxel_size));
    int iz = static_cast<int>(floorf((pos.z - grid.origin_z) / grid.voxel_size));
    if (!Inside(grid, ix, iy, iz)) return CUDART_INF_F;

    const int start_material = grid.material_id[FlatIndex(grid, ix, iy, iz)];
    out_material_id = start_material;

    int step_x, step_y, step_z;
    float t_max_x, t_max_y, t_max_z;
    float t_delta_x, t_delta_y, t_delta_z;
    InitAxis(pos.x, grid.origin_x, dir.x, ix, grid.voxel_size, step_x, t_max_x, t_delta_x);
    InitAxis(pos.y, grid.origin_y, dir.y, iy, grid.voxel_size, step_y, t_max_y, t_delta_y);
    InitAxis(pos.z, grid.origin_z, dir.z, iz, grid.voxel_size, step_z, t_max_z, t_delta_z);

    const int max_steps = grid.nx + grid.ny + grid.nz + 3;
    for (int step = 0; step < max_steps; ++step) {
        float t = t_max_x;
        int axis = 0;
        if (t_max_y < t) { t = t_max_y; axis = 1; }
        if (t_max_z < t) { t = t_max_z; axis = 2; }
        if (!isfinite(t)) return CUDART_INF_F;

        if (axis == 0) { ix += step_x; t_max_x += t_delta_x; }
        else if (axis == 1) { iy += step_y; t_max_y += t_delta_y; }
        else { iz += step_z; t_max_z += t_delta_z; }

        if (!Inside(grid, ix, iy, iz)) {
            out_material_id = kNoMaterial;
            return fmaxf(0.0f, t);
        }
        const int mat = grid.material_id[FlatIndex(grid, ix, iy, iz)];
        if (mat != start_material) {
            out_material_id = mat;
            return fmaxf(0.0f, t);
        }
    }

    return CUDART_INF_F;
}

void UploadActiveVoxelGrid(const VoxelGrid& grid, cudaStream_t stream) {
    CheckCuda(cudaMemcpyToSymbolAsync(d_active_voxel_grid, &grid, sizeof(VoxelGrid),
                                      0, cudaMemcpyHostToDevice, stream),
              "cudaMemcpyToSymbolAsync d_active_voxel_grid");
}

float LaunchDistanceToNextVoxelBoundary(float3 pos, float3 dir,
                                        const VoxelGrid& grid,
                                        int& out_material_id,
                                        cudaStream_t stream) {
    float* d_distance = nullptr;
    int* d_material = nullptr;
    CheckCuda(cudaMalloc(&d_distance, sizeof(float)), "cudaMalloc voxel distance");
    CheckCuda(cudaMalloc(&d_material, sizeof(int)), "cudaMalloc voxel material");
    CheckCuda(cudaMemsetAsync(d_material, 0xff, sizeof(int), stream),
              "cudaMemsetAsync voxel material");
    DistanceKernel<<<1, 1, 0, stream>>>(pos, dir, grid, d_distance, d_material);
    CheckCuda(cudaGetLastError(), "DistanceKernel launch");
    float distance = std::numeric_limits<float>::infinity();
    CheckCuda(cudaMemcpyAsync(&distance, d_distance, sizeof(float),
                              cudaMemcpyDeviceToHost, stream),
              "cudaMemcpyAsync voxel distance");
    CheckCuda(cudaMemcpyAsync(&out_material_id, d_material, sizeof(int),
                              cudaMemcpyDeviceToHost, stream),
              "cudaMemcpyAsync voxel material");
    CheckCuda(cudaStreamSynchronize(stream), "cudaStreamSynchronize voxel distance");
    CheckCuda(cudaFree(d_distance), "cudaFree voxel distance");
    CheckCuda(cudaFree(d_material), "cudaFree voxel material");
    return distance;
}

}  // namespace g4gpu
