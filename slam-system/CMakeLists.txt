cmake_minimum_required(VERSION 3.10)
project(DS-Slam-M3 VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(WIN32)
    add_definitions(-DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# ONNX Runtime (prebuilt CPU package)
set(ORT_ROOT "${CMAKE_SOURCE_DIR}/../libs/onnxruntime" CACHE PATH "ONNX Runtime root")

# Headers in include/, DLL and .lib both in lib/
set(ORT_INCLUDE "${ORT_ROOT}/include")
set(ORT_LIB_DIR "${ORT_ROOT}/lib")

# Try MinGW .dll.a first, then fall back to .lib
find_library(ORT_LIB onnxruntime
    HINTS ${ORT_LIB_DIR})
if(NOT ORT_LIB)
    # MinGW may need explicit .dll.a - create it
    set(ORT_DLL_A "${ORT_LIB_DIR}/libonnxruntime.dll.a")
    if(NOT EXISTS ${ORT_DLL_A})
        execute_process(COMMAND gendef - ${ORT_LIB_DIR}/onnxruntime.dll OUTPUT_FILE ${CMAKE_BINARY_DIR}/onnxruntime.def ERROR_QUIET)
        execute_process(COMMAND dlltool -d ${CMAKE_BINARY_DIR}/onnxruntime.def -l ${ORT_DLL_A} -D ${ORT_LIB_DIR}/onnxruntime.dll ERROR_QUIET)
    endif()
    set(ORT_LIB ${ORT_DLL_A})
endif()

if(NOT EXISTS "${ORT_INCLUDE}/onnxruntime_cxx_api.h")
    message(FATAL_ERROR "ONNX Runtime headers not found at ${ORT_INCLUDE}")
endif()

# OpenCV (from MSYS2)
find_package(OpenCV REQUIRED)

# Copy ORT DLL to build dir
set(ORT_DLL "${ORT_LIB_DIR}/onnxruntime.dll")

# Static library for SemanticSegmentator
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

# Test program
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

# Copy ORT DLL next to test exe after build
add_custom_command(TARGET test_segmentator POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${ORT_DLL} $<TARGET_FILE_DIR:test_segmentator>
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${ORT_LIB_DIR}/onnxruntime_providers_shared.dll $<TARGET_FILE_DIR:test_segmentator>
)
