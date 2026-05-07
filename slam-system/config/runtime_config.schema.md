# DS-SLAM Runtime Config Schema

`build/runtime_config.json` is generated from YAML by:

```powershell
python scripts/print_config.py --profile dev --write-runtime build/runtime_config.json
```

The file is intentionally JSON so future C++ modules can read it without adding
`yaml-cpp` during the current ORB-SLAM3 baseline stage.

## Top-level fields

- `project`: project name, active profile, and resolved root.
- `orbslam3`: resolved ORB-SLAM3 paths, including vocabulary, camera YAML files,
  RGB-D executable, source root, and build directory.
- `datasets`: resolved dataset roots, camera configs, and association files.
- `segmentation`: resolved ONNX model path.
- `visualization`: host, port, WebSocket path, and static directory.
- `output`: resolved logs, trajectories, and maps directories.

Each path entry uses this shape:

```json
{
  "raw": "orbslam3/Vocabulary/ORBvoc.txt",
  "win": "E:\\VSCode\\VSCode-Workspace\\DS-Slam\\orbslam3\\Vocabulary\\ORBvoc.txt",
  "msys": "/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Vocabulary/ORBvoc.txt"
}
```
