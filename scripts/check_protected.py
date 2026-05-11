#!/usr/bin/env python3
"""DS-SLAM compiled file protection checker"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROTECTED = {
    "Core Runtime": [
        "orbslam3/Examples/RGB-D/rgbd_tum.exe",
        "orbslam3/Examples/RGB-D/libORB_SLAM3.dll",
        "orbslam3/Examples/RGB-D/libg2o.dll",
        "orbslam3/Examples/RGB-D/TUM1.yaml",
    ],
    "ONNX Runtime": [
        "libs/onnxruntime/bin/onnxruntime.dll",
        "libs/onnxruntime/lib/libonnxruntime.dll.a",
    ],
    "Semantic Segmentation": [
        "slam-system/build/libSemanticSegmentator.a",
        "segmentation/onnx/yolo11n_seg_v2.onnx",
    ],
    "Vocabulary": [
        "orbslam3/Vocabulary/ORBvoc.txt",
    ],
    "Datasets": [
        "datasets/tum/rgbd_dataset_freiburg1_xyz/associations.txt",
        "datasets/tum/rgbd_dataset_freiburg3_walking_xyz/associations.txt",
    ],
    "Scripts": [
        "scripts/eval_ate.py",
        "scripts/associate.py",
    ],
}

def main():
    print("DS-SLAM Build File Protection Check")
    print("Workspace: %s\n" % ROOT)
    all_ok = True
    for cat, files in PROTECTED.items():
        print("[%s]" % cat)
        for f in files:
            full = os.path.join(ROOT, f)
            if os.path.exists(full):
                sz = os.path.getsize(full)
                size = "%.1f MB" % (sz/1e6) if sz > 1e6 else "%d KB" % (sz/1000)
                print("  OK  %s (%s)" % (f, size))
            else:
                print("  MISSING  %s" % f)
                all_ok = False
        print()

    rgbd = os.path.join(ROOT, "orbslam3/Examples/RGB-D")
    if os.path.isdir(rgbd):
        dlls = [f for f in os.listdir(rgbd) if f.endswith(".dll")]
        total = sum(os.path.getsize(os.path.join(rgbd, f)) for f in dlls)
        print("RGB-D DLLs: %d files, %d MB total" % (len(dlls), total/1e6))

    if all_ok:
        print("\nAll required files present.")
    else:
        print("\nMissing files detected!")
        sys.exit(1)

if __name__ == "__main__":
    main()