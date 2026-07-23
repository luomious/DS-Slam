"""
动静分离模块 - 利用YOLO分割结果区分静态/动态区域

功能：
1. 基于YOLO分割掩码识别动态物体
2. 分离静态场景和动态物体的点云
3. 为高斯重建提供动静标签
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional


class DynamicStaticSeparator:
    """基于YOLO分割的动静分离器"""
    
    def __init__(self, 
                 dynamic_threshold: float = 0.5,
                 min_dynamic_area: int = 100,
                 erosion_kernel: int = 5):
        self.dynamic_threshold = dynamic_threshold
        self.min_dynamic_area = min_dynamic_area
        self.erosion_kernel = erosion_kernel
        
        # 创建形态学操作核
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erosion_kernel, erosion_kernel))
        
        print(f"[DynamicStaticSeparator] Initialized: threshold={dynamic_threshold}, min_area={min_dynamic_area}")
    
    def separate_points(self,
                       points: np.ndarray,  # [N, 3] 点云坐标
                       colors: np.ndarray,  # [N, 3] 点云颜色
                       dynamic_mask: np.ndarray,  # [H, W] 动态掩码
                       camera_pose: Dict[str, float],
                       intrinsics: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        分离静态和动态点云
        
        Args:
            points: 点云坐标 [N, 3]
            colors: 点云颜色 [N, 3]
            dynamic_mask: 动态区域掩码 [H, W]，值范围[0, 1]
            camera_pose: 相机位姿
            intrinsics: 相机内参
        
        Returns:
            (static_points, static_colors, dynamic_points, dynamic_colors)
        """
        if len(points) == 0:
            return (np.zeros((0, 3)), np.zeros((0, 3)), 
                    np.zeros((0, 3)), np.zeros((0, 3)))
        
        # 将点云投影到图像平面
        projected_pixels = self._project_points_to_image(points, camera_pose, intrinsics)
        
        # 查询每个点对应的掩码值
        mask_values = self._query_mask_values(projected_pixels, dynamic_mask)
        
        # 分类点
        static_mask = mask_values < self.dynamic_threshold
        dynamic_mask_points = mask_values >= self.dynamic_threshold
        
        static_points = points[static_mask]
        static_colors = colors[static_mask]
        dynamic_points = points[dynamic_mask_points]
        dynamic_colors = colors[dynamic_mask_points]
        
        print(f"[DynamicStaticSeparator] Separated: {len(static_points)} static, {len(dynamic_points)} dynamic points")
        
        return static_points, static_colors, dynamic_points, dynamic_colors
    
    def create_gaussian_labels(self,
                              points: np.ndarray,
                              dynamic_mask: np.ndarray,
                              camera_pose: Dict[str, float],
                              intrinsics: Dict[str, float]) -> np.ndarray:
        """
        为点云创建高斯标签（静态=0，动态=1）
        
        Returns:
            labels [N] 每个点的动静标签
        """
        if len(points) == 0:
            return np.array([])
        
        projected_pixels = self._project_points_to_image(points, camera_pose, intrinsics)
        mask_values = self._query_mask_values(projected_pixels, dynamic_mask)
        
        labels = (mask_values >= self.dynamic_threshold).astype(np.float32)
        return labels
    
    def _project_points_to_image(self,
                                 points: np.ndarray,
                                 camera_pose: Dict[str, float],
                                 intrinsics: Dict[str, float]) -> np.ndarray:
        """将3D点投影到图像平面"""
        # 提取相机位姿
        R = self._quat_to_rotation_matrix(
            camera_pose.get('qw', 1.0),
            camera_pose.get('qx', 0.0),
            camera_pose.get('qy', 0.0),
            camera_pose.get('qz', 0.0)
        )
        t = np.array([camera_pose.get('tx', 0.0), 
                      camera_pose.get('ty', 0.0), 
                      camera_pose.get('tz', 0.0)])
        
        # 转换到相机坐标系
        points_cam = (R @ points.T).T + t  # [N, 3]
        
        # 过滤相机后面的点
        valid = points_cam[:, 2] > 0.1
        if not np.any(valid):
            return np.zeros((0, 2))
        
        points_cam_valid = points_cam[valid]
        
        # 投影到图像平面
        fx = intrinsics.get('fx', 517.3)
        fy = intrinsics.get('fy', 516.5)
        cx = intrinsics.get('cx', 318.6)
        cy = intrinsics.get('cy', 255.3)
        
        u = (fx * points_cam_valid[:, 0] / points_cam_valid[:, 2] + cx).astype(int)
        v = (fy * points_cam_valid[:, 1] / points_cam_valid[:, 2] + cy).astype(int)
        
        pixels = np.stack([u, v], axis=-1)
        return pixels
    
    def _query_mask_values(self,
                          pixels: np.ndarray,
                          dynamic_mask: np.ndarray) -> np.ndarray:
        """查询像素位置对应的掩码值"""
        H, W = dynamic_mask.shape
        values = np.zeros(len(pixels), dtype=np.float32)
        
        for i, (u, v) in enumerate(pixels):
            if 0 <= u < W and 0 <= v < H:
                values[i] = dynamic_mask[v, u]
        
        return values
    
    def _quat_to_rotation_matrix(self, qw, qx, qy, qz) -> np.ndarray:
        """四元数转旋转矩阵"""
        return np.array([
            [1-2*qy*qy-2*qz*qz, 2*qx*qy-2*qz*qw, 2*qx*qz+2*qy*qw],
            [2*qx*qy+2*qz*qw, 1-2*qx*qx-2*qz*qz, 2*qy*qz-2*qx*qw],
            [2*qx*qz-2*qy*qw, 2*qy*qz+2*qx*qw, 1-2*qx*qx-2*qy*qy]
        ])
    
    def refine_dynamic_mask(self, dynamic_mask: np.ndarray) -> np.ndarray:
        """优化动态掩码（形态学操作）"""
        # 二值化
        binary_mask = (dynamic_mask > self.dynamic_threshold).astype(np.uint8)
        
        # 形态学开运算（去噪）
        refined = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, self.kernel)
        
        # 形态学闭运算（填充空洞）
        refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, self.kernel)
        
        # 过滤小区域
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(refined, connectivity=8)
        filtered = np.zeros_like(refined)
        
        for i in range(1, num_labels):  # 跳过背景
            if stats[i, cv2.CC_STAT_AREA] >= self.min_dynamic_area:
                filtered[labels == i] = 1
        
        return filtered.astype(np.float32)
