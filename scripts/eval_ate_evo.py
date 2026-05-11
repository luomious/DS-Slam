from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from evo.core import sync
import numpy as np

def umeyama_alignment(x, y, with_scale=True):
    n = x.shape[0]
    cx = x.mean(axis=0)
    cy = y.mean(axis=0)
    xc = x - cx
    yc = y - cy
    H = xc.T @ yc / n
    U, S, Vt = np.linalg.svd(H)
    d = np.linalg.det(Vt.T @ U.T)
    sign = np.array([1,1,np.sign(d)])
    R = (Vt.T * sign) @ U.T
    if with_scale:
        var_x = np.sum(xc**2) / n
        s = np.sum(S * sign) / var_x
    else:
        s = 1.0
    t = cy - s * R @ cx
    return s, R, t

ref = file_interface.read_tum_trajectory_file(r'E:\VSCode\VSCode-Workspace\DS-Slam\datasets\tum\rgbd_dataset_freiburg3_walking_xyz\groundtruth.txt')
est = file_interface.read_tum_trajectory_file(r'E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\build_clang\CameraTrajectory.txt')

ref_idx, est_idx = sync.matching_time_indices(ref.timestamps, est.timestamps, max_diff=0.02)
ref_pos = ref.positions_xyz[ref_idx]
est_pos = est.positions_xyz[est_idx]
print(f'Matched: {len(ref_idx)}')

s, R, t = umeyama_alignment(est_pos, ref_pos, with_scale=True)
print(f'Scale: {s:.6f}')

aligned = s * (R @ est_pos.T).T + t
errors = np.linalg.norm(aligned - ref_pos, axis=1)
rmse = np.sqrt(np.mean(errors**2))
mean_e = np.mean(errors)
median_e = np.median(errors)
print(f'ATE RMSE: {rmse:.6f} m')
print(f'ATE Mean: {mean_e:.6f} m')
print(f'ATE Median: {median_e:.6f} m')
