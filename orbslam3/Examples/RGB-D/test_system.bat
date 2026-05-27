@echo off
echo ========================================
echo   DS-SLAM System Test
echo ========================================
echo.

set PASS=0
set FAIL=0

REM Test 1: Check vocabulary file
echo [Test 1] Checking vocabulary file...
if exist "..\..\Vocabulary\ORBvoc.txt" (
    echo   [PASS] ORBvoc.txt found
    set /a PASS+=1
) else (
    echo   [FAIL] ORBvoc.txt not found
    set /a FAIL+=1
)

REM Test 2: Check camera config
echo [Test 2] Checking camera config...
if exist "Astra_Pro.yaml" (
    echo   [PASS] Astra_Pro.yaml found
    set /a PASS+=1
) else (
    echo   [FAIL] Astra_Pro.yaml not found
    set /a FAIL+=1
)

REM Test 3: Check rgbd_camera.exe
echo [Test 3] Checking rgbd_camera.exe...
if exist "rgbd_camera.exe" (
    echo   [PASS] rgbd_camera.exe found
    set /a PASS+=1
) else (
    echo   [FAIL] rgbd_camera.exe not found
    set /a FAIL+=1
)

REM Test 4: Check rgbd_tum.exe
echo [Test 4] Checking rgbd_tum.exe...
if exist "rgbd_tum.exe" (
    echo   [PASS] rgbd_tum.exe found
    set /a PASS+=1
) else (
    echo   [FAIL] rgbd_tum.exe not found
    set /a FAIL+=1
)

REM Test 5: Check slam-system libraries
echo [Test 5] Checking slam-system libraries...
if exist "..\..\slam-system\build\libSemanticSegmentator.a" (
    echo   [PASS] libSemanticSegmentator.a found
    set /a PASS+=1
) else (
    echo   [FAIL] libSemanticSegmentator.a not found
    set /a FAIL+=1
)

REM Test 6: Check ONNX model
echo [Test 6] Checking ONNX model...
if exist "..\..\segmentation\onnx\yolo11n_seg_v2.onnx" (
    echo   [PASS] yolo11n_seg_v2.onnx found
    set /a PASS+=1
) else (
    echo   [FAIL] yolo11n_seg_v2.onnx not found
    set /a FAIL+=1
)

REM Test 7: Check OpenCV DLLs
echo [Test 7] Checking OpenCV DLLs...
set OPENCV_OK=1
for %%f in (libopencv_core-413.dll libopencv_highgui-413.dll libopencv_imgproc-413.dll) do (
    if not exist "E:\msys64\mingw64\bin\%%f" (
        echo   [FAIL] %%f not found
        set OPENCV_OK=0
        set /a FAIL+=1
    )
)
if %OPENCV_OK%==1 (
    echo   [PASS] OpenCV DLLs found
    set /a PASS+=1
)

REM Test 8: Check Boost DLL
echo [Test 8] Checking Boost DLL...
if exist "E:\msys64\mingw64\bin\libboost_serialization-mt.dll" (
    echo   [PASS] libboost_serialization-mt.dll found
    set /a PASS+=1
) else (
    echo   [FAIL] libboost_serialization-mt.dll not found
    set /a FAIL+=1
)

echo.
echo ========================================
echo   Test Results
echo ========================================
echo   Passed: %PASS%
echo   Failed: %FAIL%
echo   Total:  %PASS%+%FAIL%
echo ========================================
echo.

if %FAIL%==0 (
    echo [OK] All tests passed!
) else (
    echo [WARNING] Some tests failed. Please check the missing files.
)

echo.
pause
