cmake_minimum_required(VERSION 3.18)
project(G4GPU LANGUAGES CXX CUDA)

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
  src/geometry/VoxelGeometry.cc
  src/hits/G4GPUHitBuffer.cu
)

target_include_directories(G4GPU
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
    ${Geant4_INCLUDE_DIRS}
)

target_compile_definitions(G4GPU PUBLIC G4GPU_HAVE_GEANT4=1)
target_link_libraries(G4GPU PUBLIC ${Geant4_LIBRARIES} CUDA::cudart)
if(G4GPU_WITH_CURAND)
  target_link_libraries(G4GPU PRIVATE CUDA::curand)
endif()

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
  target_link_libraries(G4GPU PUBLIC ${OptiX_LIBRARIES})
  target_include_directories(G4GPU PRIVATE ${OptiX_INCLUDE_DIRS})
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
