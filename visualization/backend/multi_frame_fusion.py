"""
多帧高斯融合模块 - 时序一致性的高斯重建

功能：
1. 多帧高斯参数融合
2. 时序一致性约束
3. 动态场景的完整重建
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dynamic_object_tracker import DynamicObjectTracker, DynamicObject


class MultiFrameGaussianFusion:
    """多帧高斯融合器"""
    
    def __init__(self,
                 temporal_weight: float = 0.3,  # 时序权重
                 spatial_threshold: float = 0.1,  # 空间阈值（米）
                 max_frames: int = 30):  # 最大融合帧数
        self.temporal_weight = temporal_weight
        self.spatial_threshold = spatial_threshold
        self.max_frames = max_frames
        
        # 历史高斯参数
        self.gaussian_history: List[Dict] = []
        
        # 融合后的高斯模型
        self.fused_means: np.ndarray = np.zeros((0, 3))
        self.fused_colors: np.ndarray = np.zeros((0, 3))
        self.fused_scales: np.ndarray = np.zeros((0, 3))
        self.fused_opacities: np.ndarray = np.zeros(0)
        
        print(f"[MultiFrameGaussianFusion] Initialized: temporal_weight={temporal_weight}")
    
    def add_frame_gaussians(self,
                           means: np.ndarray,
                           colors: np.ndarray,
                           scales: np.ndarray,
                           opacities: np.ndarray,
                           frame_id: int,
                           is_static: bool = True):
        """
        添加单帧高斯参数
        
        Args:
            means: 高斯中心 [N, 3]
            colors: 高斯颜色 [N, 3]
            scales: 高斯尺度 [N, 3]
            opacities: 高斯不透明度 [N]
            frame_id: 帧ID
            is_static: 是否为静态场景
        """
        frame_data = {
            'frame_id': frame_id,
            'means': means,
            'colors': colors,
            'scales': scales,
            'opacities': opacities,
            'is_static': is_static
        }
        
        self.gaussian_history.append(frame_data)
        
        # 限制历史长度
        if len(self.gaussian_history) > self.max_frames:
            self.gaussian_history.pop(0)
        
        print(f"[MultiFrameGaussianFusion] Added frame {frame_id}: {len(means)} gaussians")
    
    def fuse_gaussians(self) -> Dict[str, np.ndarray]:
        """
        融合多帧高斯参数
        
        Returns:
            融合后的高斯参数
        """
        if not self.gaussian_history:
            return {
                'means': np.zeros((0, 3)),
                'colors': np.zeros((0, 3)),
                'scales': np.zeros((0, 3)),
                'opacities': np.zeros(0)
            }
        
        # 分离静态和动态帧
        static_frames = [f for f in self.gaussian_history if f['is_static']]
        dynamic_frames = [f for f in self.gaussian_history if not f['is_static']]
        
        # 融合静态高斯（累积）
        if static_frames:
            self.fused_means, self.fused_colors, self.fused_scales, self.fused_opacities = \
                self._fuse_static_gaussians(static_frames)
        
        # 融合动态高斯（时序追踪）
        if dynamic_frames:
            dynamic_means, dynamic_colors, dynamic_scales, dynamic_opacities = \
                self._fuse_dynamic_gaussians(dynamic_frames)
            
            # 合并静态和动态
            if len(dynamic_means) > 0:
                self.fused_means = np.vstack([self.fused_means, dynamic_means])
                self.fused_colors = np.vstack([self.fused_colors, dynamic_colors])
                self.fused_scales = np.vstack([self.fused_scales, dynamic_scales])
                self.fused_opacities = np.concatenate([self.fused_opacities, dynamic_opacities])
        
        print(f"[MultiFrameGaussianFusion] Fused: {len(self.fused_means)} total gaussians")
        
        return {
            'means': self.fused_means,
            'colors': self.fused_colors,
            'scales': self.fused_scales,
            'opacities': self.fused_opacities
        }
    
    def _fuse_static_gaussians(self, frames: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """融合静态场景高斯（多帧累积）"""
        all_means = []
        all_colors = []
        all_scales = []
        all_opacities = []
        
        for i, frame in enumerate(frames):
            # 时序权重（越新的帧权重越高）
            weight = 1.0 - (len(frames) - 1 - i) * self.temporal_weight / len(frames)
            weight = max(0.1, weight)
            
            # 应用权重到不透明度
            weighted_opacities = frame['opacities'] * weight
            
            all_means.append(frame['means'])
            all_colors.append(frame['colors'])
            all_scales.append(frame['scales'])
            all_opacities.append(weighted_opacities)
        
        # 合并所有帧
        fused_means = np.vstack(all_means) if all_means else np.zeros((0, 3))
        fused_colors = np.vstack(all_colors) if all_colors else np.zeros((0, 3))
        fused_scales = np.vstack(all_scales) if all_scales else np.zeros((0, 3))
        fused_opacities = np.concatenate(all_opacities) if all_opacities else np.zeros(0)
        
        # 去重（空间相近的高斯合并）
        if len(fused_means) > 1000:
            fused_means, fused_colors, fused_scales, fused_opacities = \
                self._deduplicate_gaussians(fused_means, fused_colors, fused_scales, fused_opacities)
        
        return fused_means, fused_colors, fused_scales, fused_opacities
    
    def _fuse_dynamic_gaussians(self, frames: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """融合动态场景高斯（时序追踪）"""
        # 简化实现：直接使用最新帧的动态高斯
        if frames:
            latest_frame = frames[-1]
            return (latest_frame['means'], latest_frame['colors'],
                    latest_frame['scales'], latest_frame['opacities'])
        
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0)
    
    def _deduplicate_gaussians(self,
                              means: np.ndarray,
                              colors: np.ndarray,
                              scales: np.ndarray,
                              opacities: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """去重空间相近的高斯"""
        if len(means) == 0:
            return means, colors, scales, opacities
        
        # 使用网格哈希去重
        grid_size = self.spatial_threshold
        grid_coords = np.floor(means / grid_size).astype(int)
        
        # 创建唯一网格ID
        grid_ids = grid_coords[:, 0] * 1000000 + grid_coords[:, 1] * 1000 + grid_coords[:, 2]
        
        # 保留每个网格中不透明度最高的高斯
        unique_ids, indices = np.unique(grid_ids, return_index=True)
        
        # 对于重复的网格，选择不透明度最高的
        final_indices = []
        for uid in unique_ids:
            mask = grid_ids == uid
            indices_in_grid = np.where(mask)[0]
            if len(indices_in_grid) == 1:
                final_indices.append(indices_in_grid[0])
            else:
                # 选择不透明度最高的
                best_idx = indices_in_grid[np.argmax(opacities[indices_in_grid])]
                final_indices.append(best_idx)
        
        final_indices = np.array(final_indices)
        
        return (means[final_indices], colors[final_indices],
                scales[final_indices], opacities[final_indices])
    
    def get_fused_model(self) -> Dict[str, np.ndarray]:
        """获取融合后的高斯模型"""
        return {
            'means': self.fused_means,
            'colors': self.fused_colors,
            'scales': self.fused_scales,
            'opacities': self.fused_opacities,
            'num_gaussians': len(self.fused_means)
        }
    
    def reset(self):
        """重置融合器"""
        self.gaussian_history.clear()
        self.fused_means = np.zeros((0, 3))
        self.fused_colors = np.zeros((0, 3))
        self.fused_scales = np.zeros((0, 3))
        self.fused_opacities = np.zeros(0)
        print("[MultiFrameGaussianFusion] Reset")
