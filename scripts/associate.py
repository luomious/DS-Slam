#!/usr/bin/env python3
"""Generate ORB-SLAM3 association files for TUM RGB-D datasets.

Usage:
    python scripts/associate.py data/tum-rgbd_dataset_freiburg1_xyz

Output:
    <dataset>/associations/<dataset-name>.txt
"""

from __future__ import annotations

import glob
import os
import sys


def associate(first_list, second_list, offset=0.0, max_offset=0.02):
    """Match each RGB timestamp to the nearest depth timestamp."""
    matches = []
    depth_index = 0

    for rgb_ts, rgb_path in first_list:
        rgb_time = float(rgb_ts)
        best = None
        best_delta = None

        while depth_index < len(second_list):
            depth_ts, depth_path = second_list[depth_index]
            delta = float(depth_ts) - rgb_time - offset
            abs_delta = abs(delta)

            if best_delta is None or abs_delta < best_delta:
                best = (depth_ts, depth_path)
                best_delta = abs_delta

            if delta > 0:
                break

            depth_index += 1

        if best is not None and best_delta is not None and best_delta <= max_offset:
            matches.append((rgb_ts, rgb_path, best[0], best[1]))

    return matches


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/associate.py <dataset_dir>")
        sys.exit(1)

    dataset = os.path.abspath(sys.argv[1])
    if not os.path.isdir(dataset):
        print(f"Dataset directory not found: {dataset}")
        sys.exit(1)

    assoc_dir = os.path.join(dataset, "associations")
    os.makedirs(assoc_dir, exist_ok=True)

    rgb_files = sorted(glob.glob(os.path.join(dataset, "rgb", "*.png")))
    depth_files = sorted(glob.glob(os.path.join(dataset, "depth", "*.png")))

    if not rgb_files or not depth_files:
        print("No rgb/depth PNG files found. Check the extracted TUM dataset layout.")
        sys.exit(1)

    rgb_list = [(os.path.basename(f).replace(".png", ""), f"rgb/{os.path.basename(f)}") for f in rgb_files]
    depth_list = [(os.path.basename(f).replace(".png", ""), f"depth/{os.path.basename(f)}") for f in depth_files]

    matches = associate(rgb_list, depth_list, offset=0, max_offset=0.02)

    out_name = os.path.basename(dataset.rstrip("/\\")) + ".txt"
    out_path = os.path.join(assoc_dir, out_name)

    with open(out_path, "w") as f:
        for m in matches:
            f.write(f"{m[0]} {m[1]} {m[2]} {m[3]}\n")

    print(f"Generated {out_path} with {len(matches)} associations")


if __name__ == "__main__":
    main()
