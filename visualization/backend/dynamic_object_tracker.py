"""
动态物体追踪模块 - 多帧关联动态物体

功能：
1. 跨帧关联动态物体实例
2. 估计动态物体运动轨迹
3. 为动态物体创建独立的高斯模型
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DynamicObject:
    """动态物体实例"""
    id: int
    mask: np.ndarray  # 当前帧掩码
    centroid: np.ndarray  # 质心 [u, v]
    bbox: Tuple[int, int, int, int]  # 边界框 [x, y, w, h]
    area: int
    points_3d: np.ndarray  # 3D点云 [N, 3]
    colors: np.ndarray  # 颜色 [N, 3]
    pose: Dict[str, float]  # 相机位姿
    frame_id: int
    
    # 追踪信息
    track_id: int = -1  # 全局追踪ID
    velocity: np.ndarray = None  # 速度 [vx, vy, vz]
    history: List[Dict] = None  # 历史位置
    
    def __post_init__(self):
        if self.history is None:
            self.history = []


class DynamicObjectTracker:
    """动态物体追踪器"""
    
    def __init__(self,
                 max_distance: float = 50.0,  # 最大关联距离（像素）
                 min_area: int = 100,  # 最小物体面积
                 max_history: int = 30):  # 最大历史长度
        self.max_distance = max_distance
        self.min_area = min_area
        self.max_history = max_history
        
        self.objects: List[DynamicObject] = []
        self.next_track_id = 0
        
        print(f"[DynamicObjectTracker] Initialized: max_dist={max_distance}, min_area={min_area}")
    
    def process_frame(self,
                     dynamic_mask: np.ndarray,
                     points_3d: np.ndarray,
                     colors: np.ndarray,
                     camera_pose: Dict[str, float],
                     intrinsics: Dict[str, float],
                     frame_id: int) -> List[DynamicObject]:
        """
        处理单帧，检测并追踪动态物体
        
        Args:
            dynamic_mask: 动态区域掩码 [H, W]
            points_3d: 3D点云 [N, 3]
            colors: 点云颜色 [N, 3]
            camera_pose: 相机位姿
            intrinsics: 相机内参
            frame_id: 帧ID
        
        Returns:
            检测到的动态物体列表
        """
        # 提取动态物体轮廓
        contours = self._extract_contours(dynamic_mask)
        
        # 创建当前帧物体
        current_objects = []
        for contour in contours:
            obj = self._create_object_from_contour(
                contour, points_3d, colors, camera_pose, intrinsics, frame_id
            )
            if obj is not None:
                current_objects.append(obj)
        
        # 关联追踪
        self._associate_tracks(current_objects)
        
        # 更新历史
        for obj in current_objects:
            obj.history.append({
                'frame_id': frame_id,
                'centroid': obj.centroid.copy(),
                'pose': camera_pose.copy()
            })
            if len(obj.history) > self.max_history:
                obj.history.pop(0)
        
        # 更新速度
        self._update_velocities(current_objects)
        
        self.objects = current_objects
        return current_objects
    
    def get_static_gaussians(self,
                            all_points: np.ndarray,
                            all_colors: np.ndarray,
                            dynamic_mask: np.ndarray,
                            camera_pose: Dict[str, float],
                            intrinsics: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取静态场景的高斯参数（排除动态物体）
        
        Returns:
            (static_means, static_colors)
        """
        if len(all_points) == 0:
            return np.zeros((0, 3)), np.zeros((0, 3))
        
        # 投影点到图像
        R = self._quat_to_rotation_matrix(
            camera_pose.get('qw', 1.0),
            camera_pose.get('qx', 0.0),
            camera_pose.get('qy', 0.0),
            camera_pose.get('qz', 0.0)
        )
        t = np.array([camera_pose.get('tx', 0.0),
                      camera_pose.get('ty', 0.0),
                      camera_pose.get('tz', 0.0)])
        
        points_cam = (R @ all_points.T).T + t
        valid = points_cam[:, 2] > 0.1
        
        if not np.any(valid):
            return np.zeros((0, 3)), np.zeros((0, 3))
        
        fx = intrinsics.get('fx', 517.3)
        fy = intrinsics.get('fy', 516.5)
        cx = intrinsics.get('cx', 318.6)
        cy = intrinsics.get('cy', 255.3)
        
        u = (fx * points_cam[valid, 0] / points_cam[valid, 2] + cx).astype(int)
        v = (fy * points_cam[valid, 1] / points_cam[valid, 2] + cy).astype(int)
        
        # 检查是否在动态区域
        H, W = dynamic_mask.shape
        is_static = np.ones(len(u), dtype=bool)
        
        for i, (ui, vi) in enumerate(zip(u, v)):
            if 0 <= ui < W and 0 <= vi < H:
                if dynamic_mask[vi, ui] > 0.5:
                    is_static[i] = False
        
        valid_indices = np.where(valid)[0]
        static_indices = valid_indices[is_static]
        
        static_means = all_points[static_indices]
        static_colors = all_colors[static_indices]
        
        return static_means, static_colors
    
    def get_dynamic_gaussians(self) -> Dict[int, Dict]:
        """
        获取动态物体的高斯参数
        
        Returns:
            {track_id: {'means': ..., 'colors': ..., 'velocity': ...}}
        """
        result = {}
        for obj in self.objects:
            if obj.track_id >= 0 and len(obj.points_3d) > 0:
                result[obj.track_id] = {
                    'means': obj.points_3d,
                    'colors': obj.colors,
                    'velocity': obj.velocity,
                    'history': obj.history[-10:]  # 最近10帧
                }
        return result
    
    def _extract_contours(self, dynamic_mask: np.ndarray) -> List[np.ndarray]:
        """提取动态物体轮廓"""
        binary = (dynamic_mask > 0.5).astype(np.uint8)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤小轮廓
        valid_contours = []
        for contour in contours:
            if cv2.contourArea(contour) >= self.min_area:
                valid_contours.append(contour)
        
        return valid_contours
    
    def _create_object_from_contour(self,
                                   contour: np.ndarray,
                                   points_3d: np.ndarray,
                                   colors: np.ndarray,
                                   camera_pose: Dict[str, float],
                                   intrinsics: Dict[str, float],
                                   frame_id: int) -> Optional[DynamicObject]:
        """从轮廓创建动态物体"""
        # 计算边界框
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        
        # 计算质心
        M = cv2.moments(contour)
        if M['m00'] == 0:
            return None
        
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        centroid = np.array([cx, cy])
        
        # 创建掩码
        mask = np.zeros((intrinsics.get('height', 480), intrinsics.get('width', 640)), dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        mask = (mask > 0).astype(np.float32)
        
        # 提取3D点（简化：使用轮廓内的点）
        # 实际应用中需要更精确的点云提取
        obj_id = self.next_track_id
        self.next_track_id += 1
        
        return DynamicObject(
            id=obj_id,
            mask=mask,
            centroid=centroid,
            bbox=(x, y, w, h),
            area=int(area),
            points_3d=np.zeros((0, 3)),  # 简化：实际需要从点云提取
            colors=np.zeros((0, 3)),
            pose=camera_pose.copy(),
            frame_id=frame_id
        )
    
    def _associate_tracks(self, current_objects: List[DynamicObject]):
        """关联当前帧物体与历史追踪"""
        if not self.objects:
            # 首次检测，分配新ID
            for obj in current_objects:
                obj.track_id = self.next_track_id
                self.next_track_id += 1
            return
        
        # 基于质心距离的简单关联
        used_tracks = set()
        
        for curr_obj in current_objects:
            best_match = None
            best_distance = self.max_distance
            
            for prev_obj in self.objects:
                if prev_obj.track_id in used_tracks:
                    continue
                
                distance = np.linalg.norm(curr_obj.centroid - prev_obj.centroid)
                if distance < best_distance:
                    best_distance = distance
                    best_match = prev_obj
            
            if best_match is not None:
                curr_obj.track_id = best_match.track_id
                used_tracks.add(best_match.track_id)
            else:
                curr_obj.track_id = self.next_track_id
                self.next_track_id += 1
    
    def _update_velocities(self, objects: List[DynamicObject]):
        """更新物体速度"""
        for obj in objects:
            if len(obj.history) >= 2:
                prev = obj.history[-2]
                curr = obj.history[-1]
                
                # 简化速度估计（像素/帧）
                velocity = curr['centroid'] - prev['centroid']
                obj.velocity = velocity
    
    def _quat_to_rotation_matrix(self, qw, qx, qy, qz) -> np.ndarray:
        """四元数转旋转矩阵"""
        return np.array([
            [1-2*qy*qy-2*qz*qz, 2*qx*qy-2*qz*qw, 2*qx*qz+2*qy*qw],
            [2*qx*qy+2*qz*qw, 1-2*qx*qx-2*qz*qz, 2*qy*qz-2*qx*qw],
            [2*qx*qz-2*qy*qw, 2*qy*qz+2*qx*qw, 1-2*qx*qx-2*qy*qy]
        ])
