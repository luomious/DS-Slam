# DS-SLAM Progress

Project path: `E:\VSCode\VSCode-Workspace\DS-Slam`

Last reviewed: 2026-05-07

## Current Stage

The project is past the original M0 checkpoint and is functionally at the M3 ONNX-export boundary.

- M0 is complete in practice: the repository exists, scripts and requirements are present, and the project skeleton is in place.
- M1 ORB-SLAM3 baseline is mostly complete: ORBvoc exists, `rgbd_tum.exe` exists, `fr1_xyz` and `fr3_walking_xyz` datasets are available, and RGB-D trajectory files were generated on 2026-05-06.
- M1 is not formally closed yet because there is no `milestone-1` tag and the latest ORB-SLAM3 build fixes remain uncommitted.
- M2 segmentation source files exist (`UIB`, `DWR`, `LSCD`, test/export scripts), and CPU fallback inference passes in the clean `.venv`.
- M3 is partially complete: `segmentation/onnx/yolo11n_seg.onnx` exists and runs in ONNX Runtime CPU mode, but the C++ `SemanticSegmentator` interface is not present.
- M4/M5 are not started: no dynamic feature filtering integration or static dense mapping module is confirmed.
- M6 has a minimal config-aware Web visualizer scaffold, but not the full 4-panel Three.js SLAM UI yet.

## Milestone Status

| Milestone | Status | Notes |
| --- | --- | --- |
| M0 Environment precheck | Complete | Git repository, scripts, requirements, and skeleton are present. |
| M1 ORB-SLAM3 build/run | Nearly complete | ORBvoc, RGB-D exe, `fr1_xyz`, `fr3_walking_xyz`, and trajectory outputs exist. Needs final verification, commit, and tag. |
| M2 Semantic segmentation | Verified on CPU | Python model modules exist; `test_inference.py` passes with 80x80 head outputs and CPU fallback. |
| M3 ONNX + C++ interface | Partial | ONNX model exports and runs in ONNX Runtime CPU mode; `SemanticSegmentator` is still missing. |
| M4 Dynamic feature filtering | Not started | No Tracking integration confirmed. |
| M5 Static dense mapping | Not started | No `StaticMapping` implementation confirmed. |
| M6 Visualization | Scaffolded | Minimal FastAPI backend and simple frontend exist; full Three.js visualizer remains. |
| M7 Integration | Not started | Full pipeline not confirmed. |

## Configuration System Changes

- Added shared YAML configuration:
  - `config/default.yaml`
  - `config/profiles/dev.yaml`
  - `config/profiles/portable.yaml`
  - `config/local.yaml.example`
- Added config tooling:
  - `scripts/config_loader.py` for merge order `default -> profile -> local -> env`.
  - `scripts/print_config.py` for JSON/YAML output and runtime config generation.
  - `scripts/check_config.ps1` for deployment preflight checks.
  - `scripts/package_runtime.ps1` for non-destructive runtime packaging into `dist/ds-slam/`.
- Updated config-driven scripts:
  - `scripts/3_build_orbslam3.bat`
  - `scripts/4_run_test.bat`
  - `scripts/check_progress.ps1`
- Added GUI/runtime scaffolding:
  - `visualization/backend/main.py`
  - `visualization/frontend/index.html`
  - `slam-system/config/runtime_config.schema.md`
- Updated `.gitignore` for local config, runtime config, package output, local venv, and troubleshooting artifacts.

## Python Environment Status

- Standard project environment: `.venv` created with Python 3.12.10.
- Old environment retained: `venv-py312` is untouched and should be treated as legacy/reference only.
- `.venv` is isolated: `ENABLE_USER_SITE=False`, no `PYTHONPATH`, no `CONDA_PREFIX`.
- `pip check` passes with no broken requirements.
- Installed core packages include `torch 2.11.0+cpu`, `torchvision 0.26.0+cpu`, `numpy 2.4.3`, `opencv-python 4.13.0`, `onnx 1.21.0`, `onnxruntime-gpu 1.25.1`, `fastapi 0.136.1`, `uvicorn 0.46.0`, `websockets 16.0`, `evo 1.36.3`, and `ultralytics 8.4.47`.
- CUDA 12.8 PyTorch install was attempted but timed out before installing anything; the clean standard environment currently uses CPU fallback.
- RTX 5060 GPU support remains a separate follow-up: avoid reinstalling old `cu121` wheels because they do not support `sm_120`.

## Latest Config Check

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_progress.ps1 -Profile dev
```

Observed status:

- OK: project root, MSYS2 MinGW64 shell, ORB-SLAM3 source, ORB vocabulary, RGB-D executable.
- OK: `fr1_xyz` dataset, association file, and TUM1 camera config.
- OK: `fr3_walking_xyz` dataset, association file, and TUM3 camera config.
- Missing: `fr3_sitting_xyz` dataset and association file.
- OK: `segmentation/onnx/yolo11n_seg.onnx`.
- Missing: output directories `output/logs`, `output/trajectories`, `output/maps`.
- OK: visualizer port `127.0.0.1:8000` is available.
- OK: minimal visualizer static directory exists.

## Latest M2/M3 Checks

Commands:

```powershell
.\.venv\Scripts\python.exe segmentation\python\test_inference.py --iters 3 --warmup 1
.\.venv\Scripts\python.exe segmentation\python\export_onnx.py --cpu
.\.venv\Scripts\python.exe -m pip check
```

Observed status:

- OK: M2 inference runs on CPU fallback, average time about 90 ms for the short check.
- OK: model outputs `bbox [1,4,80,80]`, `cls [1,2,80,80]`, `proto [1,32,80,80]`, and mask `[1,1,640,640]`.
- OK: ONNX model exports to `segmentation/onnx/yolo11n_seg.onnx`, validates with ONNX checker, and runs in ONNX Runtime CPU mode.
- Note: ONNX export now uses opset 18 because PyTorch 2.11 cannot reliably down-convert the Resize path to opset 14.

## Immediate Next Steps

1. Review and commit the current configuration-system, Python-environment, and M2/M3 ONNX changes separately if clean history matters.
2. Finalize M1 by running the config-driven `scripts\4_run_test.bat` on `fr1_xyz`, confirming trajectory output, then commit and tag `milestone-1`.
3. Decide whether to retry PyTorch CUDA 12.8 installation for RTX 5060 or keep CPU fallback until C++ ONNX Runtime GPU integration.
4. Add the C++ `SemanticSegmentator` wrapper now that the ONNX artifact is present.
5. Keep M4 dynamic feature filtering blocked until `SemanticSegmentator` has a passing C++ test.

## Notes

- Current working tree includes unrelated/uncommitted ORB-SLAM3 build changes:
  - `orbslam3/CMakeLists.txt`
  - `orbslam3/Thirdparty/g2o/CMakeLists.txt`
  - `orbslam3/evaluation/associate.py`
- Generated/local artifacts are present and ignored or should remain untracked:
  - `build/runtime_config.json`
  - `dist/`
  - `venv-py312/`
  - `_out*.txt`
  - `_gen_assoc.py`
  - `orbslam3/_build_dll_log.txt`
