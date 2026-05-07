@echo off
set PATH=E:\msys64\mingw64\bin;E:\msys64\usr\bin;%PATH%
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D
rgbd_tum.exe ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/TUM_RGB-D.yaml ../../../datasets/tum/rgbd_dataset_freiburg3_walking_xyz ../../../datasets/tum/rgbd_dataset_freiburg3_walking_xyz/associations.txt ../../../segmentation/onnx/yolo11n_seg.onnx
