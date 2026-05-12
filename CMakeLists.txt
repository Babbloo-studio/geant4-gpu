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
find_package(Python3 COMPONENTS Interpreter QUIET)
get_target_property(G4GPU_CUDART_INCLUDE_DIRS CUDA::cudart INTERFACE_INCLUDE_DIRECTORIES)
list(GET G4GPU_CUDART_INCLUDE_DIRS 0 G4GPU_CUDART_INCLUDE_DIR)
get_filename_component(G4GPU_CUDA_TOOLKIT_ROOT "${CUDAToolkit_BIN_DIR}/.." REALPATH)
set(G4GPU_CUDA_TARGET_LIB_DIR "${G4GPU_CUDA_TOOLKIT_ROOT}/targets/x86_64-linux/lib")

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
  find_package(OptiX REQUIRED)
endif()

add_library(G4GPU SHARED
  src/core/G4GPUTrackBuffer.cc
  src/core/G4GPUTrackingManager.cc
  src/geometry/VoxelGeometry.cc
  src/geometry/VoxelGeometry.cu
  src/hits/G4GPUHitBuffer.cu
)

target_include_directories(G4GPU
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
    ${Geant4_INCLUDE_DIRS}
    ${CUDAToolkit_INCLUDE_DIRS}
    ${G4GPU_CUDART_INCLUDE_DIRS}
)

target_compile_definitions(G4GPU PUBLIC G4GPU_HAVE_GEANT4=1)
target_compile_options(G4GPU PRIVATE
  $<$<COMPILE_LANGUAGE:CXX>:-I${G4GPU_CUDART_INCLUDE_DIR}>
)
target_link_directories(G4GPU PRIVATE "${G4GPU_CUDA_TARGET_LIB_DIR}")
target_link_options(G4GPU PRIVATE "-L${G4GPU_CUDA_TARGET_LIB_DIR}")
target_link_libraries(G4GPU PUBLIC ${Geant4_LIBRARIES} CUDA::cudart)
if(G4GPU_WITH_MUON)
  target_compile_definitions(G4GPU PUBLIC G4GPU_WITH_MUON=1)
  target_sources(G4GPU PRIVATE src/physics/MuonStepKernel.cu)
elseif(G4GPU_WITH_CURAND)
  target_link_libraries(G4GPU PRIVATE CUDA::curand)
endif()

if(G4GPU_WITH_EM)
  target_compile_definitions(G4GPU PUBLIC G4GPU_WITH_EM=1)
  target_sources(G4GPU PRIVATE src/physics/EMStepKernel.cu)
  target_link_libraries(G4GPU PRIVATE CUDA::curand)
endif()

if(G4GPU_WITH_OPTICAL OR G4GPU_WITH_RTX)
  target_link_libraries(G4GPU PUBLIC ${OptiX_LIBRARIES})
  target_include_directories(G4GPU PRIVATE ${OptiX_INCLUDE_DIRS})
endif()

set_target_properties(G4GPU PROPERTIES
  CUDA_SEPARABLE_COMPILATION ON
  POSITION_INDEPENDENT_CODE ON
  BUILD_RPATH "${G4GPU_CUDA_TARGET_LIB_DIR}"
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

if(G4GPU_WITH_EM)
  add_executable(test_em_klein_nishina tests/test_em_klein_nishina.cu)
  target_link_libraries(test_em_klein_nishina PRIVATE G4GPU)
  set_target_properties(test_em_klein_nishina
    PROPERTIES
      CUDA_SEPARABLE_COMPILATION ON
      BUILD_RPATH "${G4GPU_CUDA_TARGET_LIB_DIR}"
      RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests
  )
  add_test(NAME g4gpu_em_klein_nishina COMMAND ${CMAKE_BINARY_DIR}/tests/test_em_klein_nishina)
  set_tests_properties(g4gpu_em_klein_nishina PROPERTIES SKIP_RETURN_CODE 77)
  if(Python3_Interpreter_FOUND)
    add_test(
      NAME g4gpu_em_deferred_process_gap
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_deferred_process_gap.py
    )
    add_test(
      NAME g4gpu_em_static_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_static_contract.py
    )
    add_test(
      NAME g4gpu_em_stub_fail_closed
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_stub_fail_closed.py
    )
    add_test(
      NAME g4gpu_em_publication_audit
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_publication_audit.py
    )
    add_test(
      NAME g4gpu_em_publication_artifacts
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_publication_artifacts.py
    )
    add_test(
      NAME g4gpu_em_publication_transcript
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_publication_transcript.py
    )
    add_test(
      NAME g4gpu_em_publication_patch_id
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_publication_patch_id.py
    )
    add_test(
      NAME g4gpu_em_source_boundary
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_source_boundary.py
    )
    add_test(
      NAME g4gpu_em_ctest_execution_boundary
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_ctest_execution_boundary.py
    )
    add_test(
      NAME g4gpu_em_report_coverage
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_report_coverage.py
    )
    add_test(
      NAME g4gpu_em_lane_objective_audit
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_lane_objective_audit.py
    )
    add_test(
      NAME g4gpu_em_claim_boundary
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_claim_boundary.py
    )
    add_test(
      NAME g4gpu_em_verifier_script_boundary
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_verifier_script_boundary.py
    )
    add_test(
      NAME g4gpu_em_runtime_sbatch_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_runtime_sbatch.py
    )
    add_test(
      NAME g4gpu_em_runtime_gpu_report
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_runtime_gpu_report.py
    )
    add_test(
      NAME g4gpu_em_photoelectric_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_photoelectric_contract.py
    )
    add_test(
      NAME g4gpu_em_pair_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_pair_contract.py
    )
    add_test(
      NAME g4gpu_em_bremsstrahlung_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_bremsstrahlung_contract.py
    )
    add_test(
      NAME g4gpu_em_deferred_contract_index
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_deferred_contract_index.py
    )
    add_test(
      NAME g4gpu_em_implementation_roadmap
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_implementation_roadmap.py
    )
    add_test(
      NAME g4gpu_em_validation_fixture_contract
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_validation_fixture_contract.py
    )
    add_test(
      NAME g4gpu_em_table_owner_preflight
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_table_owner_preflight.py
    )
    add_test(
      NAME g4gpu_em_secondary_buffer_preflight
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_secondary_buffer_preflight.py
    )
    add_test(
      NAME g4gpu_em_rng_stream_preflight
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_rng_stream_preflight.py
    )
    add_test(
      NAME g4gpu_em_process_selector_preflight
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_process_selector_preflight.py
    )
    add_test(
      NAME g4gpu_em_status_code_preflight
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_status_code_preflight.py
    )
    add_test(
      NAME g4gpu_em_preflight_contract_index
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_preflight_contract_index.py
    )
    add_test(
      NAME g4gpu_em_preflight_chain_audit
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_preflight_chain_audit.py
    )
    add_test(
      NAME g4gpu_em_option_boundary
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_option_boundary.py
    )
    add_test(
      NAME g4gpu_em_option_off_config
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_option_off_config.py
    )
    add_test(
      NAME g4gpu_em_line_caps
      COMMAND ${Python3_EXECUTABLE}
              ${CMAKE_CURRENT_SOURCE_DIR}/scripts/verify_em_gamma_line_caps.py
    )
  endif()
endif()

add_executable(test_benchmark_manifest tests/test_benchmark_manifest.cc)
target_include_directories(test_benchmark_manifest PRIVATE benchmarks/events benchmarks/geometries)
set_target_properties(test_benchmark_manifest PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/tests)
add_test(NAME g4gpu_benchmark_manifest COMMAND ${CMAKE_BINARY_DIR}/tests/test_benchmark_manifest)

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
