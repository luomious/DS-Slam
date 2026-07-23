"""
关键帧收集器 - 自动保存SLAM关键帧用于3D高斯训练

功能：
1. 监听SLAM帧数据，自动识别关键帧
2. 基于视差和重叠度筛选高质量关键帧
3. 保存关键帧图像和对应位姿
4. 导出COLMAP格式数据供训练使用
"""

import os
import time
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional


class KeyframeCollector:
    """收集SLAM关键帧并保存为3DGS训练格式"""
    
    def __init__(self, output_dir: str, min_keyframe_interval: float = 2.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        self.min_keyframe_interval = min_keyframe_interval
        self.last_keyframe_time = 0.0
        self.keyframes: List[Dict] = []
        self.frame_count = 0
        
        # 视差和重叠度筛选参数
        self.min_parallax_deg = 5.0  # 最小视差角度（度）
        self.min_overlap_ratio = 0.3  # 最小重叠比例
        self.last_pose = None
        
        self.intrinsics = {
            'fx': 517.3, 'fy': 516.5,
            'cx': 318.6, 'cy': 255.3,
            'width': 640, 'height': 480
        }
        
        print(f"[KeyframeCollector] Initialized, output: {self.output_dir}")
        print(f"[KeyframeCollector] Min parallax: {self.min_parallax_deg}°, Min overlap: {self.min_overlap_ratio}")
    
    def set_intrinsics(self, fx, fy, cx, cy, width=640, height=480):
        self.intrinsics = {'fx': fx, 'fy': fy, 'cx': cx, 'cy': cy, 'width': width, 'height': height}
    
    def _compute_parallax(self, pose1: dict, pose2: dict) -> float:
        """计算两个位姿之间的视差角度（度）"""
        try:
            # 提取平移向量
            t1 = np.array([pose1.get('tx', 0), pose1.get('ty', 0), pose1.get('tz', 0)])
            t2 = np.array([pose2.get('tx', 0), pose2.get('ty', 0), pose2.get('tz', 0)])
            
            # 计算位移距离
            displacement = np.linalg.norm(t2 - t1)
            
            # 提取旋转（四元数转旋转矩阵）
            def quat_to_rot(qw, qx, qy, qz):
                return np.array([
                    [1-2*qy*qy-2*qz*qz, 2*qx*qy-2*qz*qw, 2*qx*qz+2*qy*qw],
                    [2*qx*qy+2*qz*qw, 1-2*qx*qx-2*qz*qz, 2*qy*qz-2*qx*qw],
                    [2*qx*qz-2*qy*qw, 2*qy*qz+2*qx*qw, 1-2*qx*qx-2*qy*qy]
                ])
            
            r1 = quat_to_rot(pose1.get('qw', 1), pose1.get('qx', 0), pose1.get('qy', 0), pose1.get('qz', 0))
            r2 = quat_to_rot(pose2.get('qw', 1), pose2.get('qx', 0), pose2.get('qy', 0), pose2.get('qz', 0))
            
            # 相对旋转
            r_rel = r2 @ r1.T
            trace = np.trace(r_rel)
            angle_rad = np.arccos(np.clip((trace - 1) / 2, -1, 1))
            
            return np.degrees(angle_rad)
            
        except Exception as e:
            print(f"[KeyframeCollector] Parallax computation error: {e}")
            return 0.0
    
    def _estimate_overlap(self, pose1: dict, pose2: dict) -> float:
        """估计两个位姿之间的视野重叠比例"""
        try:
            # 简化估计：基于位移距离和相机FOV
            t1 = np.array([pose1.get('tx', 0), pose1.get('ty', 0), pose1.get('tz', 0)])
            t2 = np.array([pose2.get('tx', 0), pose2.get('ty', 0), pose2.get('tz', 0)])
            
            displacement = np.linalg.norm(t2 - t1)
            
            # 假设平均深度为3米，FOV约60度
            avg_depth = 3.0
            fov_rad = np.radians(60)
            
            # 视野宽度
            view_width = 2 * avg_depth * np.tan(fov_rad / 2)
            
            # 重叠比例（简化模型）
            overlap = max(0, 1.0 - displacement / view_width)
            
            return overlap
            
        except Exception as e:
            print(f"[KeyframeCollector] Overlap estimation error: {e}")
            return 0.5
    
    def add_frame(self, frame_data: dict) -> bool:
        self.frame_count += 1
        
        timestamp = frame_data.get('timestamp', time.time())
        if timestamp - self.last_keyframe_time < self.min_keyframe_interval:
            return False
        
        if 'image_base64' not in frame_data or 'pose' not in frame_data:
            return False
        
        pose = frame_data['pose']
        
        # 视差和重叠度筛选
        if self.last_pose is not None:
            parallax = self._compute_parallax(self.last_pose, pose)
            overlap = self._estimate_overlap(self.last_pose, pose)
            
            if parallax < self.min_parallax_deg:
                return False  # 视差不足
            
            if overlap < self.min_overlap_ratio:
                return False  # 重叠不足
        
        try:
            img_bytes = base64.b64decode(frame_data['image_base64'])
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                return False
            
            target_width, target_height = 320, 240
            img_resized = cv2.resize(img, (target_width, target_height))
            
            kf_idx = len(self.keyframes)
            img_path = self.images_dir / f"frame_{kf_idx:04d}.png"
            cv2.imwrite(str(img_path), img_resized)
            
            kf_data = {
                'id': kf_idx,
                'timestamp': timestamp,
                'image_path': str(img_path),
                'pose': pose,
                'image_size': [target_width, target_height]
            }
            
            self.keyframes.append(kf_data)
            self.last_keyframe_time = timestamp
            self.last_pose = pose.copy() if isinstance(pose, dict) else pose
            
            if kf_idx % 10 == 0:
                print(f"[KeyframeCollector] Saved keyframe #{kf_idx}")
            
            return True
            
        except Exception as e:
            print(f"[KeyframeCollector] Error saving keyframe: {e}")
            return False
    
    def export_colmap(self, output_dir: Optional[str] = None) -> Path:
        if not self.keyframes:
            print("[KeyframeCollector] No keyframes to export")
            return self.output_dir
        
        export_dir = Path(output_dir) if output_dir else self.output_dir / "colmap"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        colmap_images_dir = export_dir / "images"
        colmap_images_dir.mkdir(exist_ok=True)
        
        scale_x = 320.0 / self.intrinsics['width']
        scale_y = 240.0 / self.intrinsics['height']
        fx_scaled = self.intrinsics['fx'] * scale_x
        fy_scaled = self.intrinsics['fy'] * scale_y
        cx_scaled = self.intrinsics['cx'] * scale_x
        cy_scaled = self.intrinsics['cy'] * scale_y
        
        with open(export_dir / "cameras.txt", 'w') as f:
            f.write("# Camera list\n")
            f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write(f"1 PINHOLE 320 240 {fx_scaled} {fy_scaled} {cx_scaled} {cy_scaled}\n")
        
        with open(export_dir / "images.txt", 'w') as f:
            f.write("# Image list\n")
            f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("# POINTS2D[] as (X, Y, POINT3D_ID)\n")
            
            for kf in self.keyframes:
                pose = kf['pose']
                
                if isinstance(pose, dict):
                    if 'qw' in pose:
                        qw, qx, qy, qz = pose['qw'], pose['qx'], pose['qy'], pose['qz']
                        tx, ty, tz = pose['tx'], pose['ty'], pose['tz']
                    else:
                        qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
                        tx, ty, tz = 0.0, 0.0, 0.0
                else:
                    qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
                    tx, ty, tz = 0.0, 0.0, 0.0
                
                src_img = Path(kf['image_path'])
                if src_img.exists():
                    dst_img = colmap_images_dir / src_img.name
                    if not dst_img.exists():
                        import shutil
                        shutil.copy2(str(src_img), str(dst_img))
                
                f.write(f"{kf['id'] + 1} {qw} {qx} {qy} {qz} {tx} {ty} {tz} 1 {src_img.name}\n")
                f.write("\n")
        
        with open(export_dir / "points3D.txt", 'w') as f:
            f.write("# 3D point list\n")
            f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n")
            f.write("# Number of points: 0\n")
        
        print(f"[KeyframeCollector] Exported {len(self.keyframes)} keyframes to: {export_dir}")
        return export_dir
    
    def get_stats(self) -> dict:
        return {
            'total_frames': self.frame_count,
            'keyframes': len(self.keyframes),
            'output_dir': str(self.output_dir)
        }
    
    def reset(self):
        self.keyframes.clear()
        self.frame_count = 0
        self.last_keyframe_time = 0.0
        self.last_pose = None
        
        if self.images_dir.exists():
            import shutil
            shutil.rmtree(self.images_dir)
        self.images_dir.mkdir(exist_ok=True)
        
        print("[KeyframeCollector] Reset")
