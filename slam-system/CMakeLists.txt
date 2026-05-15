cmake_minimum_required(VERSION 3.10)
project(DS-Slam-M3 VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(WIN32)
    add_definitions(-DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# ONNX Runtime (prebuilt CPU package)
if(WIN32)
    set(ORT_ROOT "${CMAKE_SOURCE_DIR}/../libs/onnxruntime" CACHE PATH "ONNX Runtime root")
    set(ORT_INCLUDE "${ORT_ROOT}/include")
    set(ORT_LIB_DIR "${ORT_ROOT}/lib")
else()
    # Linux: use ORT_ROOT from cmake parameter or default path
    if(NOT ORT_ROOT)
        set(ORT_ROOT "${CMAKE_SOURCE_DIR}/../libs/onnxruntime-linux" CACHE PATH "ONNX Runtime root")
    endif()
    set(ORT_INCLUDE "${ORT_ROOT}/include")
    set(ORT_LIB_DIR "${ORT_ROOT}/lib")
endif()

# Try MinGW .dll.a first, then fall back to .lib
find_library(ORT_LIB onnxruntime
    HINTS ${ORT_LIB_DIR})
if(NOT ORT_LIB)
    if(WIN32)
        # MinGW may need explicit .dll.a - create it
        set(ORT_DLL_A "${ORT_LIB_DIR}/libonnxruntime.dll.a")
        if(NOT EXISTS ${ORT_DLL_A})
            execute_process(COMMAND gendef - ${ORT_LIB_DIR}/onnxruntime.dll OUTPUT_FILE ${CMAKE_BINARY_DIR}/onnxruntime.def ERROR_QUIET)
            execute_process(COMMAND dlltool -d ${CMAKE_BINARY_DIR}/onnxruntime.def -l ${ORT_DLL_A} -D ${ORT_LIB_DIR}/onnxruntime.dll ERROR_QUIET)
        endif()
        set(ORT_LIB ${ORT_DLL_A})
    else()
        # Linux: try .so then .a
        find_library(ORT_LIB onnxruntime HINTS ${ORT_LIB_DIR})
    endif()
endif()

if(EXISTS "${ORT_INCLUDE}/onnxruntime_cxx_api.h")
    set(ORT_AVAILABLE TRUE)
    message(STATUS "ONNX Runtime found at ${ORT_ROOT}")
else()
    set(ORT_AVAILABLE FALSE)
    message(STATUS "ONNX Runtime not found - SemanticSegmentator disabled, SlamVisualizer still available")
endif()

# OpenCV (from MSYS2)
find_package(OpenCV REQUIRED)

# Copy ORT DLL to build dir (Windows only)
if(WIN32)
    set(ORT_DLL "${ORT_LIB_DIR}/onnxruntime.dll")
endif()

# Static library for SemanticSegmentator (requires ONNX Runtime)
if(ORT_AVAILABLE)
add_library(SemanticSegmentator STATIC
    src/SemanticSegmentator.cpp
)
target_include_directories(SemanticSegmentator PUBLIC
    ${CMAKE_SOURCE_DIR}/include
    ${ORT_INCLUDE}
)
target_link_libraries(SemanticSegmentator PUBLIC
    ${OpenCV_LIBS}
    ${ORT_LIB}
)
endif()

# Static library for StaticMapper (M5)
add_library(StaticMapper STATIC
    src/StaticMapper.cpp
)
target_include_directories(StaticMapper PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)
target_link_libraries(StaticMapper PUBLIC
    ${OpenCV_LIBS}
)

# Static library for SlamVisualizer (M6)
add_library(SlamVisualizer STATIC
    src/SlamVisualizer.cpp
)
target_include_directories(SlamVisualizer PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

# Platform-specific libraries
if(WIN32)
    target_link_libraries(SlamVisualizer PUBLIC
        ${OpenCV_LIBS}
        winhttp  # Windows HTTP
    )
else()
    target_link_libraries(SlamVisualizer PUBLIC
        ${OpenCV_LIBS}
        curl  # Linux curl
    )
endif()

# Test program (requires ONNX Runtime)
if(ORT_AVAILABLE)
add_executable(test_segmentator test_segmentator.cpp)
target_include_directories(test_segmentator PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${ORT_INCLUDE}
)
target_link_libraries(test_segmentator PRIVATE
    SemanticSegmentator
    ${OpenCV_LIBS}
    ${ORT_LIB}
)
endif()

# Copy ORT DLL next to test exe after build (Windows only)
if(ORT_AVAILABLE AND WIN32)
    add_custom_command(TARGET test_segmentator POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different ${ORT_DLL} $<TARGET_FILE_DIR:test_segmentator>
        COMMAND ${CMAKE_COMMAND} -E copy_if_different ${ORT_LIB_DIR}/onnxruntime_providers_shared.dll $<TARGET_FILE_DIR:test_segmentator>
    )
endif()
