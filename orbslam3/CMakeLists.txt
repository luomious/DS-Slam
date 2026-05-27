cmake_minimum_required(VERSION 3.10)
project(ORB_SLAM3)

if(WIN32)
    add_definitions(-DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-D_SILENCE_ALL_CXX17_DEPRECATION_WARNINGS)
    # Disable Eigen alignment for MinGW compatibility
    add_definitions(-DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0)
endif()

IF(NOT CMAKE_BUILD_TYPE)
  SET(CMAKE_BUILD_TYPE Release)
ENDIF()

MESSAGE("Build type: " ${CMAKE_BUILD_TYPE})

# Override cached flags to prevent accumulation from previous cmake runs
# Removed -mcmodel=large to fix _GLOBAL_OFFSET_TABLE_ linking error on MinGW
if(WIN32)
    set(CMAKE_CXX_FLAGS "-Wall -Wa,-mbig-obj -frtti -fkeep-inline-functions" CACHE STRING "" FORCE)
else()
    set(CMAKE_CXX_FLAGS "-Wall -frtti -fkeep-inline-functions" CACHE STRING "" FORCE)
endif()
set(CMAKE_C_FLAGS "-Wall" CACHE STRING "" FORCE)
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "" FORCE)
set(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "" FORCE)

# Check C++17 or C++14 support
include(CheckCXXCompilerFlag)
# Force C++17 support for Clang
set(COMPILER_SUPPORTS_CXX17 TRUE)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17" CACHE STRING "" FORCE)
add_definitions(-DCOMPILEDWITHC17)
message(STATUS "Using flag -std=c++17 (required for ONNX Runtime).")

LIST(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake_modules)

find_package(OpenCV 4.4)
   if(NOT OpenCV_FOUND)
      message(FATAL_ERROR "OpenCV > 4.4 not found.")
   endif()

MESSAGE("OPENCV VERSION:")
MESSAGE(${OpenCV_VERSION})

find_path(EIGEN3_INCLUDE_DIR "Eigen/Core"
    HINTS "$ENV{EIGEN3_ROOT}" "$ENV{EIGEN3_ROOT_PATH}"
    PATHS "$ENV{CPACK_RPM_SOURCE_DIR}/include" "/usr/local/include" "/usr/include" "/usr/include/eigen3"
    "E:/msys64/mingw64/include/eigen3"
    "E:/msys64/mingw64/include/eigen3/Eigen"
    "E:/msys64/mingw64/include"
)
if(NOT EIGEN3_INCLUDE_DIR)
    find_path(EIGEN3_INCLUDE_DIR "Eigen/Core"
        PATHS "/usr/include/eigen3"
              "/usr/local/include/eigen3"
              "/usr/include"
              "/usr/local/include"
    )
endif()
if(NOT EIGEN3_INCLUDE_DIR)
    message(FATAL_ERROR "Eigen3 not found!")
endif()
message(STATUS "Eigen3 found at: ${EIGEN3_INCLUDE_DIR}")

# Eigen 5.x: no version check, set dummy vars
set(EIGEN3_VERSION 5.0.1)

# Pangolin - skip if not found (optional)
# For headless WSL2 testing, set DISABLE_PANGOLIN=ON to skip
option(DISABLE_PANGOLIN "Disable Pangolin visualization" ON)
if(DISABLE_PANGOLIN)
    message(STATUS "Pangolin disabled - headless mode")
    add_definitions(-DNO_PANGOLIN=1 -DHAS_PANGOLIN=0)
else()
    find_package(Pangolin QUIET)
    if(NOT Pangolin_FOUND)
        message(STATUS "Pangolin not found - disabling visualization")
        add_definitions(-DNO_PANGOLIN=1 -DHAS_PANGOLIN=0)
    endif()
endif()

# realsense2 - optional
find_package(realsense2 QUIET)

# DS-SLAM M3: ONNX Runtime
find_path(ONNXRUNTIME_INCLUDE_DIR "onnxruntime_cxx_api.h"
    HINTS "${CMAKE_SOURCE_DIR}/../libs/onnxruntime/include"
          "${CMAKE_SOURCE_DIR}/../libs/onnxruntime-linux/include"
          "$ENV{ONNXRUNTIME_ROOT}/include"
          "/usr/include"
          "/usr/local/include"
          "$ENV{HOME}/onnxruntime/include"
)
if(ONNXRUNTIME_INCLUDE_DIR)
    message(STATUS "ONNX Runtime found at: ${ONNXRUNTIME_INCLUDE_DIR}")
else()
    message(STATUS "ONNX Runtime headers not found - semantic segmentation disabled")
endif()

# Boost for DBoW2 serialization
find_path(BOOST_INCLUDE_DIR "boost/serialization/serialization.hpp"
    HINTS "$ENV{BOOST_ROOT}/include"
          "/usr/local/include"
          "/usr/include"
          "/usr/include/boost"
)
if(NOT BOOST_INCLUDE_DIR)
    message(FATAL_ERROR "Boost headers not found!")
endif()
message(STATUS "Boost found at: ${BOOST_INCLUDE_DIR}")

# DS-SLAM slam-system integration
set(DS_SLAM_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/../slam-system/include")
set(DS_SLAM_LIB_DIR "${CMAKE_SOURCE_DIR}/../slam-system/build")

# Check if slam-system libraries exist
set(DS_SLAM_AVAILABLE FALSE)
if(EXISTS "${DS_SLAM_LIB_DIR}/libSlamVisualizer.a" OR EXISTS "${DS_SLAM_LIB_DIR}/SlamVisualizer.lib")
    set(DS_SLAM_AVAILABLE TRUE)
    message(STATUS "DS-SLAM SlamVisualizer found - visualization enabled")
else()
    message(STATUS "DS-SLAM SlamVisualizer not found - visualization disabled")
    add_definitions(-DDS_SLAM_DISABLED=1)
endif()

include_directories(
${PROJECT_SOURCE_DIR}
${PROJECT_SOURCE_DIR}/include
${PROJECT_SOURCE_DIR}/include/CameraModels
${PROJECT_SOURCE_DIR}/Thirdparty/Sophus
${EIGEN3_INCLUDE_DIR}
${Pangolin_INCLUDE_DIRS}
${BOOST_INCLUDE_DIR}
)
if(DS_SLAM_AVAILABLE)
    include_directories(${DS_SLAM_INCLUDE_DIR})
endif()
if(ONNXRUNTIME_INCLUDE_DIR)
    include_directories(${ONNXRUNTIME_INCLUDE_DIR})
endif()

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/lib)

add_library(${PROJECT_NAME} STATIC
src/System.cc
src/Tracking.cc
src/LocalMapping.cc
src/LoopClosing.cc
src/ORBextractor.cc
src/ORBmatcher.cc
src/FrameDrawer.cc
src/Converter.cc
src/MapPoint.cc
src/KeyFrame.cc
src/Atlas.cc
src/Map.cc
src/Optimizer.cc
src/Frame.cc
src/KeyFrameDatabase.cc
src/Sim3Solver.cc
src/ImuTypes.cc
src/G2oTypes.cc
src/G2oTypesVertex.cc
src/G2oTypesEdge.cc
src/G2oTypesInertial.cc
src/CameraModels/Pinhole.cpp
src/CameraModels/KannalaBrandt8.cpp
src/OptimizableTypes.cpp
src/MLPnPsolver.cpp
src/GeometricTools.cc
src/TwoViewReconstruction.cc
src/Config.cc
src/Settings.cc
include/System.h
include/Tracking.h
include/LocalMapping.h
include/LoopClosing.h
include/ORBextractor.h
include/ORBmatcher.h
include/FrameDrawer.h
include/Converter.h
include/MapPoint.h
include/KeyFrame.h
include/Atlas.h
include/Map.h
include/Optimizer.h
include/Frame.h
include/KeyFrameDatabase.h
include/Sim3Solver.h
include/ImuTypes.h
include/G2oTypes.h
include/CameraModels/GeometricCamera.h
include/CameraModels/Pinhole.h
include/CameraModels/KannalaBrandt8.h
include/OptimizableTypes.h
include/MLPnPsolver.h
include/GeometricTools.h
include/TwoViewReconstruction.h
include/SerializationUtils.h
include/Config.h
include/Settings.h)

# Conditionally add Pangolin-dependent sources
if(Pangolin_FOUND)
    target_sources(${PROJECT_NAME} PRIVATE
    src/MapDrawer.cc
    src/Viewer.cc
    include/MapDrawer.h
    include/Viewer.h
    )
    target_link_libraries(${PROJECT_NAME} ${Pangolin_LIBRARIES})
endif()

set_target_properties(${PROJECT_NAME} PROPERTIES
  WINDOWS_EXPORT_ALL_SYMBOLS ON
  LINK_FLAGS "-Wl,--export-all-symbols"
)

add_subdirectory(Thirdparty/g2o)

# Resolve library paths to absolute
# DBoW2 is STATIC - link directly to .a file to avoid picking up stale .dll.a
set(DBOW2_LIB "${PROJECT_SOURCE_DIR}/Thirdparty/DBoW2/lib/libDBoW2.a")

if(DS_SLAM_AVAILABLE)
    find_library(SEGMENTATOR_LIB SemanticSegmentator PATHS "${DS_SLAM_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(STATICMAPPER_LIB StaticMapper PATHS "${DS_SLAM_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(VISUALIZER_LIB SlamVisualizer PATHS "${DS_SLAM_LIB_DIR}" NO_DEFAULT_PATH)
    find_library(ORT_LIB onnxruntime PATHS "${PROJECT_SOURCE_DIR}/../libs/onnxruntime/lib" "${PROJECT_SOURCE_DIR}/../libs/onnxruntime-linux/lib" NO_DEFAULT_PATH)
    
    if(NOT SEGMENTATOR_LIB)
        message(WARNING "SemanticSegmentator library not found, using fallback path")
        set(SEGMENTATOR_LIB "${DS_SLAM_LIB_DIR}/libSemanticSegmentator.a")
    endif()
    if(NOT STATICMAPPER_LIB)
        message(WARNING "StaticMapper library not found, using fallback path")
        set(STATICMAPPER_LIB "${DS_SLAM_LIB_DIR}/libStaticMapper.a")
    endif()
    if(NOT VISUALIZER_LIB)
        message(WARNING "SlamVisualizer library not found, using fallback path")
        set(VISUALIZER_LIB "${DS_SLAM_LIB_DIR}/libSlamVisualizer.a")
    endif()
    if(NOT ORT_LIB)
        message(WARNING "onnxruntime library not found, using fallback path")
        set(ORT_LIB "${PROJECT_SOURCE_DIR}/../libs/onnxruntime/lib/libonnxruntime.so")
    endif()
endif()

target_link_libraries(${PROJECT_NAME}
${EIGEN3_LIBS}
${DBOW2_LIB}
g2o
-lboost_serialization-mt
-lcrypto
${OpenCV_LIBS}
)

if(DS_SLAM_AVAILABLE)
    target_link_libraries(${PROJECT_NAME}
    ${SEGMENTATOR_LIB}
    ${STATICMAPPER_LIB}
    ${VISUALIZER_LIB}
    )
    # Only link ONNX Runtime if available
    if(EXISTS "${ORT_LIB}")
        target_link_libraries(${PROJECT_NAME} ${ORT_LIB})
    endif()
    if(WIN32)
        target_link_libraries(${PROJECT_NAME} winhttp)
    else()
        target_link_libraries(${PROJECT_NAME} curl)
    endif()
endif()

# If RealSense SDK is found the library is added and its examples compiled
if(realsense2_FOUND)
    include_directories(${PROJECT_NAME}
    ${realsense_INCLUDE_DIR}
    )
    target_link_libraries(${PROJECT_NAME}
    ${realsense2_LIBRARY}
    )
endif()


# Build examples

# RGB-D examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/RGB-D)

add_executable(rgbd_tum
        Examples/RGB-D/rgbd_tum.cc)
if(WIN32)
    target_link_libraries(rgbd_tum ${PROJECT_NAME} g2o ${OpenCV_LIBS} winhttp)
else()
    target_link_libraries(rgbd_tum ${PROJECT_NAME} g2o ${OpenCV_LIBS} curl)
endif()
if(DS_SLAM_AVAILABLE)
    target_link_libraries(rgbd_tum ${SEGMENTATOR_LIB} ${STATICMAPPER_LIB} ${VISUALIZER_LIB} ${OpenCV_LIBS})
    if(EXISTS "${ORT_LIB}")
        target_link_libraries(rgbd_tum ${ORT_LIB})
    endif()
endif()

if(realsense2_FOUND)
    add_executable(rgbd_realsense_D435i
            Examples/RGB-D/rgbd_realsense_D435i.cc)
    target_link_libraries(rgbd_realsense_D435i ${PROJECT_NAME})
endif()


# RGB-D inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/RGB-D-Inertial)

if(realsense2_FOUND)
    add_executable(rgbd_inertial_realsense_D435i
            Examples/RGB-D-Inertial/rgbd_inertial_realsense_D435i.cc)
    target_link_libraries(rgbd_inertial_realsense_D435i ${PROJECT_NAME})
endif()

#Stereo examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/Stereo)

add_executable(stereo_kitti
        Examples/Stereo/stereo_kitti.cc)
target_link_libraries(stereo_kitti ${PROJECT_NAME})

add_executable(stereo_euroc
        Examples/Stereo/stereo_euroc.cc)
target_link_libraries(stereo_euroc ${PROJECT_NAME})

add_executable(stereo_tum_vi
        Examples/Stereo/stereo_tum_vi.cc)
target_link_libraries(stereo_tum_vi ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(stereo_realsense_t265
            Examples/Stereo/stereo_realsense_t265.cc)
    target_link_libraries(stereo_realsense_t265 ${PROJECT_NAME})

    add_executable(stereo_realsense_D435i
            Examples/Stereo/stereo_realsense_D435i.cc)
    target_link_libraries(stereo_realsense_D435i ${PROJECT_NAME})
endif()

#Monocular examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/Monocular)

add_executable(mono_tum
        Examples/Monocular/mono_tum.cc)
target_link_libraries(mono_tum ${PROJECT_NAME})

add_executable(mono_kitti
        Examples/Monocular/mono_kitti.cc)
target_link_libraries(mono_kitti ${PROJECT_NAME})

add_executable(mono_euroc
        Examples/Monocular/mono_euroc.cc)
target_link_libraries(mono_euroc ${PROJECT_NAME})

add_executable(mono_tum_vi
        Examples/Monocular/mono_tum_vi.cc)
target_link_libraries(mono_tum_vi ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(mono_realsense_t265
            Examples/Monocular/mono_realsense_t265.cc)
    target_link_libraries(mono_realsense_t265 ${PROJECT_NAME})

    add_executable(mono_realsense_D435i
            Examples/Monocular/mono_realsense_D435i.cc)
    target_link_libraries(mono_realsense_D435i ${PROJECT_NAME})
endif()

#Monocular inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/Monocular-Inertial)

add_executable(mono_inertial_euroc
        Examples/Monocular-Inertial/mono_inertial_euroc.cc)
target_link_libraries(mono_inertial_euroc ${PROJECT_NAME})

add_executable(mono_inertial_tum_vi
        Examples/Monocular-Inertial/mono_inertial_tum_vi.cc)
target_link_libraries(mono_inertial_tum_vi ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(mono_inertial_realsense_t265
            Examples/Monocular-Inertial/mono_inertial_realsense_t265.cc)
    target_link_libraries(mono_inertial_realsense_t265 ${PROJECT_NAME})

    add_executable(mono_inertial_realsense_D435i
            Examples/Monocular-Inertial/mono_inertial_realsense_D435i.cc)
    target_link_libraries(mono_inertial_realsense_D435i ${PROJECT_NAME})
endif()

#Stereo Inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/Stereo-Inertial)

add_executable(stereo_inertial_euroc
        Examples/Stereo-Inertial/stereo_inertial_euroc.cc)
target_link_libraries(stereo_inertial_euroc ${PROJECT_NAME})

add_executable(stereo_inertial_tum_vi
        Examples/Stereo-Inertial/stereo_inertial_tum_vi.cc)
target_link_libraries(stereo_inertial_tum_vi ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(stereo_inertial_realsense_t265
            Examples/Stereo-Inertial/stereo_inertial_realsense_t265.cc)
    target_link_libraries(stereo_inertial_realsense_t265 ${PROJECT_NAME})

    add_executable(stereo_inertial_realsense_D435i
            Examples/Stereo-Inertial/stereo_inertial_realsense_D435i.cc)
    target_link_libraries(stereo_inertial_realsense_D435i ${PROJECT_NAME})
endif()

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples/Calibration)
if(realsense2_FOUND)
    add_executable(recorder_realsense_D435i
            Examples/Calibration/recorder_realsense_D435i.cc)
    target_link_libraries(recorder_realsense_D435i ${PROJECT_NAME})

    add_executable(recorder_realsense_T265
            Examples/Calibration/recorder_realsense_T265.cc)
    target_link_libraries(recorder_realsense_T265 ${PROJECT_NAME})
endif()

#Old examples

# RGB-D examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/RGB-D)

# add_executable(rgbd_tum_old
#         Examples_old/RGB-D/rgbd_tum.cc)
# target_link_libraries(rgbd_tum_old ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(rgbd_realsense_D435i_old
            Examples_old/RGB-D/rgbd_realsense_D435i.cc)
    target_link_libraries(rgbd_realsense_D435i_old ${PROJECT_NAME})
endif()


# RGB-D inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/RGB-D-Inertial)

if(realsense2_FOUND)
    add_executable(rgbd_inertial_realsense_D435i_old
            Examples_old/RGB-D-Inertial/rgbd_inertial_realsense_D435i.cc)
    target_link_libraries(rgbd_inertial_realsense_D435i_old ${PROJECT_NAME})
endif()

#Stereo examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/Stereo)

# add_executable(stereo_kitti_old
#         Examples_old/Stereo/stereo_kitti.cc)
# target_link_libraries(stereo_kitti_old ${PROJECT_NAME})

# add_executable(stereo_euroc_old
#         Examples_old/Stereo/stereo_euroc.cc)
# target_link_libraries(stereo_euroc_old ${PROJECT_NAME})

# add_executable(stereo_tum_vi_old
#         Examples_old/Stereo/stereo_tum_vi.cc)
# target_link_libraries(stereo_tum_vi_old ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(stereo_realsense_t265_old
            Examples_old/Stereo/stereo_realsense_t265.cc)
    target_link_libraries(stereo_realsense_t265_old ${PROJECT_NAME})

    add_executable(stereo_realsense_D435i_old
            Examples_old/Stereo/stereo_realsense_D435i.cc)
    target_link_libraries(stereo_realsense_D435i_old ${PROJECT_NAME})
endif()

#Monocular examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/Monocular)

# add_executable(mono_tum_old
#         Examples_old/Monocular/mono_tum.cc)
# target_link_libraries(mono_tum_old ${PROJECT_NAME})

# add_executable(mono_kitti_old
#         Examples_old/Monocular/mono_kitti.cc)
# target_link_libraries(mono_kitti_old ${PROJECT_NAME})

# add_executable(mono_euroc_old
#         Examples_old/Monocular/mono_euroc.cc)
# target_link_libraries(mono_euroc_old ${PROJECT_NAME})

# add_executable(mono_tum_vi_old
#         Examples_old/Monocular/mono_tum_vi.cc)
# target_link_libraries(mono_tum_vi_old ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(mono_realsense_t265_old
            Examples_old/Monocular/mono_realsense_t265.cc)
    target_link_libraries(mono_realsense_t265_old ${PROJECT_NAME})

    add_executable(mono_realsense_D435i_old
            Examples_old/Monocular/mono_realsense_D435i.cc)
    target_link_libraries(mono_realsense_D435i_old ${PROJECT_NAME})
endif()

#Monocular inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/Monocular-Inertial)

# add_executable(mono_inertial_euroc_old
#         Examples_old/Monocular-Inertial/mono_inertial_euroc.cc)
# target_link_libraries(mono_inertial_euroc_old ${PROJECT_NAME})

# add_executable(mono_inertial_tum_vi_old
#         Examples_old/Monocular-Inertial/mono_inertial_tum_vi.cc)
# target_link_libraries(mono_inertial_tum_vi_old ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(mono_inertial_realsense_t265_old
            Examples_old/Monocular-Inertial/mono_inertial_realsense_t265.cc)
    target_link_libraries(mono_inertial_realsense_t265_old ${PROJECT_NAME})

    add_executable(mono_inertial_realsense_D435i_old
            Examples_old/Monocular-Inertial/mono_inertial_realsense_D435i.cc)
    target_link_libraries(mono_inertial_realsense_D435i_old ${PROJECT_NAME})
endif()

#Stereo Inertial examples
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/Examples_old/Stereo-Inertial)

# add_executable(stereo_inertial_euroc_old
#         Examples_old/Stereo-Inertial/stereo_inertial_euroc.cc)
# target_link_libraries(stereo_inertial_euroc_old ${PROJECT_NAME})

# add_executable(stereo_inertial_tum_vi_old
#         Examples_old/Stereo-Inertial/stereo_inertial_tum_vi.cc)
# target_link_libraries(stereo_inertial_tum_vi_old ${PROJECT_NAME})

if(realsense2_FOUND)
    add_executable(stereo_inertial_realsense_t265_old
            Examples_old/Stereo-Inertial/stereo_inertial_realsense_t265.cc)
    target_link_libraries(stereo_inertial_realsense_t265_old ${PROJECT_NAME})

    add_executable(stereo_inertial_realsense_D435i_old
            Examples_old/Stereo-Inertial/stereo_inertial_realsense_D435i.cc)
    target_link_libraries(stereo_inertial_realsense_D435i_old ${PROJECT_NAME})
endif()
