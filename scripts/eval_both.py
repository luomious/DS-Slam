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

# SE3 alignment (no scale)
s_se3, R_se3, t_se3 = umeyama_alignment(est_pos, ref_pos, with_scale=False)
aligned_se3 = s_se3 * (R_se3 @ est_pos.T).T + t_se3
errors_se3 = np.linalg.norm(aligned_se3 - ref_pos, axis=1)
rmse_se3 = np.sqrt(np.mean(errors_se3**2))
print(f'SE3 (no scale): RMSE={rmse_se3:.6f} m, Scale={s_se3:.6f}')

# Sim3 alignment (with scale)
s_sim3, R_sim3, t_sim3 = umeyama_alignment(est_pos, ref_pos, with_scale=True)
aligned_sim3 = s_sim3 * (R_sim3 @ est_pos.T).T + t_sim3
errors_sim3 = np.linalg.norm(aligned_sim3 - ref_pos, axis=1)
rmse_sim3 = np.sqrt(np.mean(errors_sim3**2))
print(f'Sim3 (with scale): RMSE={rmse_sim3:.6f} m, Scale={s_sim3:.6f}')
