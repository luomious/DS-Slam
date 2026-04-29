@echo off
chcp 65001 >nul 2>&1

echo ================================================
echo  DS-SLAM dataset links
echo ================================================
echo.
echo ORB vocabulary (required by ORB-SLAM3, about 2.1 GB):
echo   GitHub mirror:
echo   https://github.com/raulmur/ORB_SLAM3/releases/download/1.0/ORBvoc.bin.tar.gz
echo.
echo TUM RGB-D datasets:
echo   fr1_xyz:
echo   https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz
echo.
echo   fr3_walking_xyz:
echo   https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_walking_xyz.tgz
echo.
echo   fr3_sitting_xyz:
echo   https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_sitting_xyz.tgz
echo.
echo Extract datasets into:
echo   E:\VSCode\VSCode-Workspace\DS-Slam\data\
echo.
echo After extraction, generate associations with:
echo   python scripts\associate.py data\tum-rgbd_dataset_freiburg1_xyz
echo.
pause
