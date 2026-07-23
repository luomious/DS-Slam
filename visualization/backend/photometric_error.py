"""
光度误差计算模块 - 用于3D高斯辅助SLAM位姿优化

功能：
1. 从高斯模型渲染合成图像
2. 计算与真实图像的光度误差
3. 提供误差梯度用于位姿优化
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional


class PhotometricErrorCalculator:
    """计算高斯模型渲染图像与真实图像之间的光度误差"""
    
    def __init__(self, width: int = 320, height: int = 240):
        self.width = width
        self.height = height
        self.fx = 517.3 * (width / 640.0)
        self.fy = 516.5 * (height / 480.0)
        self.cx = 318.6 * (width / 640.0)
        self.cy = 255.3 * (height / 480.0)
        
        # 预计算像素坐标网格
        self.pixel_coords = self._compute_pixel_grid()
        
        print(f"[PhotometricError] Initialized: {width}x{height}, fx={self.fx:.1f}, fy={self.fy:.1f}")
    
    def _compute_pixel_grid(self) -> np.ndarray:
        """计算像素坐标网格"""
        x = np.arange(self.width)
        y = np.arange(self.height)
        xx, yy = np.meshgrid(x, y)
        return np.stack([xx, yy], axis=-1).reshape(-1, 2)
    
    def render_gaussian_image(self, 
                              means: np.ndarray, 
                              colors: np.ndarray, 
                              scales: np.ndarray, 
                              opacities: np.ndarray,
                              pose: Dict[str, float]) -> np.ndarray:
        """
        从高斯模型渲染合成图像
        
        Args:
            means: 高斯中心位置 [N, 3]
            colors: 高斯颜色 [N, 3]
            scales: 高斯尺度 [N, 3]
            opacities: 高斯不透明度 [N]
            pose: 相机位姿 {qw, qx, qy, qz, tx, ty, tz}
        
        Returns:
            渲染图像 [H, W, 3]
        """
        # 简化渲染：投影高斯中心到图像平面
        image = np.zeros((self.height, self.width, 3), dtype=np.float32)
        weight_sum = np.zeros((self.height, self.width), dtype=np.float32)
        
        # 提取相机位姿
        R = self._quat_to_rotation_matrix(
            pose.get('qw', 1.0), 
            pose.get('qx', 0.0), 
            pose.get('qy', 0.0), 
            pose.get('qz', 0.0)
        )
        t = np.array([pose.get('tx', 0.0), pose.get('ty', 0.0), pose.get('tz', 0.0)])
        
        # 转换到相机坐标系
        means_cam = (R @ means.T).T + t  # [N, 3]
        
        # 投影到图像平面
        depths = means_cam[:, 2]
        valid = depths > 0.1  # 过滤太近的点
        
        if not np.any(valid):
            return image
        
        means_cam_valid = means_cam[valid]
        colors_valid = colors[valid]
        scales_valid = scales[valid]
        opacities_valid = opacities[valid]
        
        # 投影坐标
        u = (self.fx * means_cam_valid[:, 0] / means_cam_valid[:, 2] + self.cx).astype(int)
        v = (self.fy * means_cam_valid[:, 1] / means_cam_valid[:, 2] + self.cy).astype(int)
        
        # 过滤在图像范围内的点
        in_bounds = (u >= 0) & (u < self.width) & (v >= 0) & (v < self.height)
        
        u_valid = u[in_bounds]
        v_valid = v[in_bounds]
        colors_valid = colors_valid[in_bounds]
        opacities_valid = opacities_valid[in_bounds]
        depths_valid = depths[valid][in_bounds]
        
        # 按深度排序（远的先渲染）
        sort_idx = np.argsort(-depths_valid)
        u_valid = u_valid[sort_idx]
        v_valid = v_valid[sort_idx]
        colors_valid = colors_valid[sort_idx]
        opacities_valid = opacities_valid[sort_idx]
        
        # 累积渲染
        for i in range(len(u_valid)):
            uu, vv = u_valid[i], v_valid[i]
            alpha = opacities_valid[i]
            
            # 混合颜色
            image[vv, uu] = image[vv, uu] * (1 - alpha) + colors_valid[i] * alpha
            weight_sum[vv, uu] += alpha
        
        return image
    
    def compute_photometric_error(self, 
                                  rendered_image: np.ndarray, 
                                  real_image: np.ndarray,
                                  mask: Optional[np.ndarray] = None) -> Tuple[float, np.ndarray]:
        """
        计算光度误差
        
        Args:
            rendered_image: 渲染图像 [H, W, 3]
            real_image: 真实图像 [H, W, 3]
            mask: 可选掩码，用于忽略动态区域
        
        Returns:
            (误差值, 误差图 [H, W])
        """
        # 确保图像范围在[0, 1]
        rendered = np.clip(rendered_image, 0, 1)
        real = np.clip(real_image, 0, 1)
        
        # 计算像素级误差
        error_map = np.mean(np.abs(rendered - real), axis=2)  # [H, W]
        
        # 应用掩码（如果有）
        if mask is not None:
            error_map = error_map * mask
        
        # 计算平均误差
        if mask is not None:
            valid_pixels = np.sum(mask > 0)
            if valid_pixels > 0:
                error_value = np.sum(error_map) / valid_pixels
            else:
                error_value = 0.0
        else:
            error_value = np.mean(error_map)
        
        return error_value, error_map
    
    def compute_pose_gradient(self,
                             means: np.ndarray,
                             colors: np.ndarray,
                             scales: np.ndarray,
                             opacities: np.ndarray,
                             pose: Dict[str, float],
                             real_image: np.ndarray,
                             delta: float = 0.01) -> Dict[str, float]:
        """
        计算位姿梯度（数值微分）
        
        Args:
            means, colors, scales, opacities: 高斯参数
            pose: 当前相机位姿
            real_image: 真实图像
            delta: 微分步长
        
        Returns:
            位姿梯度 {tx, ty, tz, rx, ry, rz}
        """
        # 基准误差
        rendered_base = self.render_gaussian_image(means, colors, scales, opacities, pose)
        error_base, _ = self.compute_photometric_error(rendered_base, real_image)
        
        gradients = {}
        
        # 平移梯度
        for axis, key in [(0, 'tx'), (1, 'ty'), (2, 'tz')]:
            pose_plus = pose.copy()
            pose_plus[key] = pose.get(key, 0.0) + delta
            
            rendered_plus = self.render_gaussian_image(means, colors, scales, opacities, pose_plus)
            error_plus, _ = self.compute_photometric_error(rendered_plus, real_image)
            
            gradients[key] = (error_plus - error_base) / delta
        
        # 旋转梯度（绕各轴小角度旋转）
        for axis, key in [(0, 'rx'), (1, 'ry'), (2, 'rz')]:
            pose_rot = pose.copy()
            angle = delta
            
            # 创建小旋转矩阵
            R_small = np.eye(3)
            if axis == 0:  # 绕X轴
                R_small = np.array([
                    [1, 0, 0],
                    [0, np.cos(angle), -np.sin(angle)],
                    [0, np.sin(angle), np.cos(angle)]
                ])
            elif axis == 1:  # 绕Y轴
                R_small = np.array([
                    [np.cos(angle), 0, np.sin(angle)],
                    [0, 1, 0],
                    [-np.sin(angle), 0, np.cos(angle)]
                ])
            else:  # 绕Z轴
                R_small = np.array([
                    [np.cos(angle), -np.sin(angle), 0],
                    [np.sin(angle), np.cos(angle), 0],
                    [0, 0, 1]
                ])
            
            # 应用旋转到当前位姿
            R_curr = self._quat_to_rotation_matrix(
                pose.get('qw', 1.0), 
                pose.get('qx', 0.0), 
                pose.get('qy', 0.0), 
                pose.get('qz', 0.0)
            )
            R_new = R_small @ R_curr
            
            # 转换回四元数
            qw, qx, qy, qz = self._rotation_matrix_to_quat(R_new)
            pose_rot['qw'], pose_rot['qx'], pose_rot['qy'], pose_rot['qz'] = qw, qx, qy, qz
            
            rendered_rot = self.render_gaussian_image(means, colors, scales, opacities, pose_rot)
            error_rot, _ = self.compute_photometric_error(rendered_rot, real_image)
            
            gradients[key] = (error_rot - error_base) / delta
        
        return gradients
    
    def _quat_to_rotation_matrix(self, qw, qx, qy, qz) -> np.ndarray:
        """四元数转旋转矩阵"""
        return np.array([
            [1-2*qy*qy-2*qz*qz, 2*qx*qy-2*qz*qw, 2*qx*qz+2*qy*qw],
            [2*qx*qy+2*qz*qw, 1-2*qx*qx-2*qz*qz, 2*qy*qz-2*qx*qw],
            [2*qx*qz-2*qy*qw, 2*qy*qz+2*qx*qw, 1-2*qx*qx-2*qy*qy]
        ])
    
    def _rotation_matrix_to_quat(self, R: np.ndarray) -> Tuple[float, float, float, float]:
        """旋转矩阵转四元数"""
        trace = np.trace(R)
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            qw = 0.25 / s
            qx = (R[2, 1] - R[1, 2]) * s
            qy = (R[0, 2] - R[2, 0]) * s
            qz = (R[1, 0] - R[0, 1]) * s
        else:
            if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
                qw = (R[2, 1] - R[1, 2]) / s
                qx = 0.25 * s
                qy = (R[0, 1] + R[1, 0]) / s
                qz = (R[0, 2] + R[2, 0]) / s
            elif R[1, 1] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
                qw = (R[0, 2] - R[2, 0]) / s
                qx = (R[0, 1] + R[1, 0]) / s
                qy = 0.25 * s
                qz = (R[1, 2] + R[2, 1]) / s
            else:
                s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
                qw = (R[1, 0] - R[0, 1]) / s
                qx = (R[0, 2] + R[2, 0]) / s
                qy = (R[1, 2] + R[2, 1]) / s
                qz = 0.25 * s
        
        # 归一化
        norm = np.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
        return qw/norm, qx/norm, qy/norm, qz/norm
