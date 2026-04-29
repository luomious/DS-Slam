# DS-SLAM Progress

Project path: `E:\VSCode\VSCode-Workspace\DS-Slam`

Last reviewed: 2026-04-29

## Current Stage

The project is between M0 and M1.

- M0 project skeleton exists, but the folder is not currently a Git repository.
- M1 source preparation is partly done: `orbslam3/` is present and its CMake file already contains MinGW-oriented changes.
- ORB vocabulary is recorded as present in the previous progress notes, but the RGB-D executable and TUM datasets still need local verification.
- M2 and later stages have not been confirmed.

## Milestone Status

| Milestone | Status | Notes |
| --- | --- | --- |
| M0 Environment precheck | Partial | Scripts and requirements exist. Git repository still needs `git init`. |
| M1 ORB-SLAM3 build/run | In progress | Source tree exists. Build and `fr1_xyz` runtime test are next. |
| M2 Semantic segmentation | Not started | UIB/DWR/LSCD files not confirmed. |
| M3 ONNX + C++ interface | Not started | ONNX model and `SemanticSegmentator` not confirmed. |
| M4 Dynamic feature filtering | Not started | Tracking integration not confirmed. |
| M5 Static dense mapping | Not started | StaticMapping not confirmed. |
| M6 Visualization | Not started | FastAPI/Three.js visualizer not confirmed. |
| M7 Integration | Not started | Full pipeline not confirmed. |

## Immediate Next Steps

1. Run `scripts\check_progress.ps1` to verify files on this machine.
2. If `.git` is missing, run `git init` or `scripts\0_init_project.bat`.
3. Build ORB-SLAM3 with `scripts\3_build_orbslam3.bat`.
4. Download/extract `fr1_xyz`, then run `python scripts\associate.py data\tum-rgbd_dataset_freiburg1_xyz`.
5. Run `scripts\4_run_test.bat` and choose `fr1_xyz`.
6. After the M1 runtime test passes, commit and tag `milestone-1`.

## Optimization Log

- Rewrote batch scripts with ASCII messages to avoid Windows console mojibake.
- Added prompts before dependency installation.
- Corrected the expected ORB-SLAM3 RGB-D executable path to `orbslam3\Examples\RGB-D\rgbd_tum.exe`.
- Added preflight checks to the RGB-D test runner.
- Rewrote `scripts\associate.py` to emit ORB-SLAM3-friendly relative paths such as `rgb/<file>.png` and `depth/<file>.png`.
- Added `scripts\check_progress.ps1` for repeatable milestone checks.
