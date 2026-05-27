@echo off
set PATH=E:\msys64\mingw64\bin;E:\msys64\usr\bin;%PATH%
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D

echo ============================================ > run_output.log
echo DS-SLAM Walking XYZ Test >> run_output.log
echo Start: %DATE% %TIME% >> run_output.log
echo ============================================ >> run_output.log

rgbd_tum.exe ../../Vocabulary/ORBvoc.txt TUM3.yaml ../../../datasets/tum/rgbd_dataset_freiburg3_walking_xyz ../../../datasets/tum/rgbd_dataset_freiburg3_walking_xyz/associations.txt ../../../segmentation/onnx/yolo11n_seg_v2.onnx >> run_output.log 2>&1

echo. >> run_output.log
echo ============================================ >> run_output.log
echo End: %DATE% %TIME% >> run_output.log
echo Exit Code: %ERRORLEVEL% >> run_output.log
echo ============================================ >> run_output.log
