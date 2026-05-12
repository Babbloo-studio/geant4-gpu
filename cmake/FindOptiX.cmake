find_path(OptiX_INCLUDE_DIR
  NAMES optix.h
  HINTS
    ${OptiX_INSTALL_DIR}
    $ENV{OptiX_INSTALL_DIR}
    $ENV{OPTIX_INSTALL_DIR}
    $ENV{OPTIX_PATH}
  PATH_SUFFIXES include
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(OptiX REQUIRED_VARS OptiX_INCLUDE_DIR)

if(OptiX_FOUND)
  set(OptiX_INCLUDE_DIRS ${OptiX_INCLUDE_DIR})
  set(OptiX_LIBRARIES ${CMAKE_DL_LIBS})
  if(NOT TARGET OptiX::OptiX)
    add_library(OptiX::OptiX INTERFACE IMPORTED)
    set_target_properties(OptiX::OptiX PROPERTIES
      INTERFACE_INCLUDE_DIRECTORIES "${OptiX_INCLUDE_DIR}"
      INTERFACE_LINK_LIBRARIES "${CMAKE_DL_LIBS}"
    )
  endif()
endif()
