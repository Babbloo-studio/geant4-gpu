cmake_minimum_required(VERSION 3.18)
project(G4GPU LANGUAGES CXX CUDA)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_EXTENSIONS OFF)

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES 80 86)
endif()

option(G4GPU_WITH_EM      "Enable EM shower kernels"       ON)
option(G4GPU_WITH_MUON    "Enable muon physics kernels"    ON)
option(G4GPU_WITH_NEUTRON "Enable neutron elastic kernels" ON)
option(G4GPU_WITH_CURAND  "Link cuRAND for stochastic physics kernels" OFF)
option(G4GPU_WITH_OPTICAL "Enable OptiX optical transport" OFF)
option(G4GPU_WITH_RTX     "Enable RTX geometry backend"    OFF)
set(G4GPU_BENCHMARK_PYTHON "/projects/hep/fs10/shared/nnbar/billy/packages/hibeam_env/bin/python"
    CACHE STRING "Python interpreter with pyarrow for benchmark Parquet output")

if(DEFINED Geant4_DIR)
  get_filename_component(_g4gpu_geant4_prefix "${Geant4_DIR}/../../.." REALPATH)
  if(EXISTS "${_g4gpu_geant4_prefix}")
    list(PREPEND CMAKE_PREFIX_PATH "${_g4gpu_geant4_prefix}")
    if(EXISTS "${_g4gpu_geant4_prefix}/lib/libz.so")
      set(ZLIB_ROOT "${_g4gpu_geant4_prefix}" CACHE PATH "Geant4 dependency prefix" FORCE)
      set(ZLIB_LIBRARY "${_g4gpu_geant4_prefix}/lib/libz.so" CACHE FILEPATH "Geant4 zlib" FORCE)
      set(ZLIB_INCLUDE_DIR "${_g4gpu_geant4_prefix}/include" CACHE PATH "Geant4 zlib include" FORCE)
    endif()
  endif()
endif()

find_package(Geant4 REQUIRED CONFIG)
if(DEFINED Geant4_USE_FILE)
  include(${Geant4_USE_FILE})
endif()
find_package(CUDAToolkit REQUIRED)

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
  find_package(OptiX REQUIRED)
endif()

add_library(G4GPU SHARED
  src/core/G4GPUTrackBuffer.cc
  src/core/G4GPUTrackingManager.cc
  src/core/Track.cc
  src/geometry/VoxelGeometry.cc
  src/geometry/VoxelGeometry.cu
  src/hits/G4GPUHitBuffer.cu
  src/physics/CrossSectionInterpolator.cc
  src/geometry/branchless_solids.cc
  src/geometry/navigation_prefetch.cc
)
set_source_files_properties(
  src/physics/CrossSectionInterpolator.cc
  src/geometry/branchless_solids.cc
  src/core/Track.cc
  src/geometry/navigation_prefetch.cc
  PROPERTIES COMPILE_OPTIONS "-O3"
)

target_include_directories(G4GPU
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
    ${Geant4_INCLUDE_DIRS}
)

target_compile_definitions(G4GPU PUBLIC G4GPU_HAVE_GEANT4=1)
target_link_libraries(G4GPU PUBLIC ${Geant4_LIBRARIES} CUDA::cudart)
if(G4GPU_WITH_MUON)
  target_compile_definitions(G4GPU PUBLIC G4GPU_WITH_MUON=1)
  target_sources(G4GPU PRIVATE src/physics/MuonStepKernel.cu)
elseif(G4GPU_WITH_CURAND)
  target_link_libraries(G4GPU PRIVATE CUDA::curand)
endif()

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
  target_link_libraries(G4GPU PUBLIC ${OptiX_LIBRARIES})
  target_include_directories(G4GPU PUBLIC ${OptiX_INCLUDE_DIRS})
endif()

if(G4GPU_WITH_RTX)
  target_compile_definitions(G4GPU PUBLIC G4GPU_WITH_RTX=1)
  target_sources(G4GPU PRIVATE src/geometry/RTXGeometry.cc)
  list(GET CMAKE_CUDA_ARCHITECTURES 0 G4GPU_RTX_CUDA_ARCH)
  set(G4GPU_RTX_PTX "${CMAKE_CURRENT_BINARY_DIR}/RTXGeometry.ptx")
  add_custom_command(
    OUTPUT "${G4GPU_RTX_PTX}"
    COMMAND ${CMAKE_CUDA_COMPILER} --ptx -std=c++17
            -arch=sm_${G4GPU_RTX_CUDA_ARCH}
            -DG4GPU_WITH_RTX=1
            -I${CMAKE_CURRENT_SOURCE_DIR}/include
            -I${OptiX_INCLUDE_DIRS}
            ${CMAKE_CURRENT_SOURCE_DIR}/src/geometry/RTXGeometry.cu
            -o "${G4GPU_RTX_PTX}"
    DEPENDS src/geometry/RTXGeometry.cu include/g4gpu/RTXGeometry.hh
    VERBATIM)
  add_custom_target(g4gpu_rtx_ptx DEPENDS "${G4GPU_RTX_PTX}")
  add_dependencies(G4GPU g4gpu_rtx_ptx)
  target_compile_definitions(G4GPU PRIVATE G4GPU_RTX_PTX_PATH="${G4GPU_RTX_PTX}")
endif()

set_target_properties(G4GPU PROPERTIES
  CUDA_SEPARABLE_COMPILATION ON
  POSITION_INDEPENDENT_CODE ON
)

enable_testing()
add_executable(test_stub tests/test_stub.cc)
target_link_libraries(test_stub PRIVATE G4GPU)
set_target_properties(test_stub PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_stub COMMAND ${CMAKE_BINARY_DIR}/tests/test_stub)

add_executable(test_voxel_geometry tests/test_voxel_geometry.cc)
target_link_libraries(test_voxel_geometry PRIVATE G4GPU)
set_target_properties(test_voxel_geometry PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_voxel_geometry COMMAND ${CMAKE_BINARY_DIR}/tests/test_voxel_geometry)

if(G4GPU_WITH_MUON)
  add_executable(test_muon_range tests/test_muon_range.cc)
  set_source_files_properties(tests/test_muon_range.cc PROPERTIES LANGUAGE CUDA)
  target_link_libraries(test_muon_range PRIVATE G4GPU)
  set_target_properties(test_muon_range PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
  add_test(NAME g4gpu_muon_range COMMAND ${CMAKE_BINARY_DIR}/tests/test_muon_range)

  add_executable(test_mcs tests/test_mcs.cc)
  set_source_files_properties(tests/test_mcs.cc PROPERTIES LANGUAGE CUDA)
  target_link_libraries(test_mcs PRIVATE G4GPU)
  set_target_properties(test_mcs PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
  add_test(NAME g4gpu_mcs COMMAND ${CMAKE_BINARY_DIR}/tests/test_mcs)
endif()

add_executable(test_cross_section_interpolator tests/test_cross_section_interpolator.cc)
target_link_libraries(test_cross_section_interpolator PRIVATE G4GPU)
set_target_properties(test_cross_section_interpolator PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_cross_section_interpolator COMMAND ${CMAKE_BINARY_DIR}/tests/test_cross_section_interpolator)

add_executable(test_branchless_solids tests/test_branchless_solids.cc)
target_link_libraries(test_branchless_solids PRIVATE G4GPU)
set_target_properties(test_branchless_solids PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_branchless_solids COMMAND ${CMAKE_BINARY_DIR}/tests/test_branchless_solids)

add_executable(test_track_alignment tests/test_track_alignment.cc)
target_link_libraries(test_track_alignment PRIVATE G4GPU)
set_target_properties(test_track_alignment PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_track_alignment COMMAND ${CMAKE_BINARY_DIR}/tests/test_track_alignment)


add_executable(test_navigation_prefetch tests/test_navigation_prefetch.cc)
target_link_libraries(test_navigation_prefetch PRIVATE G4GPU)
set_target_properties(test_navigation_prefetch PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_navigation_prefetch COMMAND ${CMAKE_BINARY_DIR}/tests/test_navigation_prefetch)

add_executable(test_rtx_geometry tests/test_rtx_geometry.cc)
target_link_libraries(test_rtx_geometry PRIVATE G4GPU)
set_target_properties(test_rtx_geometry PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_rtx_geometry COMMAND ${CMAKE_BINARY_DIR}/tests/test_rtx_geometry)

add_executable(test_benchmark_manifest tests/test_benchmark_manifest.cc)
target_link_libraries(test_benchmark_manifest PRIVATE G4GPU)
target_include_directories(test_benchmark_manifest
  PRIVATE
    benchmarks/canonical
    benchmarks/events
    benchmarks/geometries
)
set_target_properties(test_benchmark_manifest PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_benchmark_manifest COMMAND ${CMAKE_BINARY_DIR}/tests/test_benchmark_manifest)
add_test(
  NAME g4gpu_benchmark_script_syntax
  COMMAND bash -lc
    "bash -n '${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/run_baseline.sh' && bash -n '${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/profile_cpu.sh' && bash -n '${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/profile_gpu.sh'"
)
add_test(
  NAME g4gpu_validate_harness
  COMMAND ${G4GPU_BENCHMARK_PYTHON}
    ${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/tools/validate_self_test.py
    ${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/validate.py
    ${CMAKE_BINARY_DIR}/benchmarks/validate-self
)

set(G4GPU_BENCHMARK_EVENTS
  gamma_100mev
  muon_10gev
  nbar_carbon
  cosmic_shower
  optical_scintillator
  beam_neutron
)

foreach(_g4gpu_benchmark_event IN LISTS G4GPU_BENCHMARK_EVENTS)
  add_executable(benchmark_${_g4gpu_benchmark_event}
    benchmarks/events/${_g4gpu_benchmark_event}.cc
  )
  target_include_directories(benchmark_${_g4gpu_benchmark_event}
    PRIVATE
      benchmarks/events
      benchmarks/geometries
  )
  target_compile_definitions(benchmark_${_g4gpu_benchmark_event}
    PRIVATE
      G4GPU_BENCHMARK_WRITER_PATH="${CMAKE_CURRENT_SOURCE_DIR}/benchmarks/tools/write_parquet.py"
      G4GPU_BENCHMARK_DEFAULT_PYTHON="${G4GPU_BENCHMARK_PYTHON}"
  )
  target_link_libraries(benchmark_${_g4gpu_benchmark_event} PRIVATE G4GPU)
  set_target_properties(benchmark_${_g4gpu_benchmark_event}
    PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/benchmarks
  )
  add_test(
    NAME g4gpu_benchmark_${_g4gpu_benchmark_event}_smoke
    COMMAND ${CMAKE_BINARY_DIR}/benchmarks/benchmark_${_g4gpu_benchmark_event}
      --events 3
      --commit smoke
      --output ${CMAKE_BINARY_DIR}/benchmarks/results/${_g4gpu_benchmark_event}_smoke.parquet
  )
endforeach()
