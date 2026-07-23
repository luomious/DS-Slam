"""
实时高斯更新器 - SLAM运行时自动增量更新高斯模型

功能：
1. 监听SLAM帧数据，自动增量更新高斯模型
2. 基于关键帧质量自动筛选
3. 渐进式高斯优化（新帧增量添加）
4. 自动触发后台训练
"""

import numpy as np
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from keyframe_collector import KeyframeCollector


class RealtimeGaussianUpdater:
    """实时高斯模型更新器"""
    
    def __init__(self,
                 output_dir: str,
                 update_interval: float = 5.0,  # 更新间隔（秒）
                 min_keyframes_for_update: int = 10,  # 最小关键帧数
                 max_gaussians: int = 50000):  # 最大高斯数
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_interval = update_interval
        self.min_keyframes_for_update = min_keyframes_for_update
        self.max_gaussians = max_gaussians
        
        # 关键帧收集器
        self.keyframe_collector = KeyframeCollector(
            output_dir=str(self.output_dir / "realtime_keyframes"),
            min_keyframe_interval=2.0
        )
        
        # 当前高斯模型
        self.current_means: np.ndarray = np.zeros((0, 3))
        self.current_colors: np.ndarray = np.zeros((0, 3))
        self.current_scales: np.ndarray = np.zeros((0, 3))
        self.current_opacities: np.ndarray = np.zeros(0)
        
        # 更新状态
        self.last_update_time = 0.0
        self.update_count = 0
        self.is_updating = False
        
        # 模型路径
        self.model_path = self.output_dir / "realtime_gaussian_model.json"
        
        print(f"[RealtimeGaussianUpdater] Initialized: interval={update_interval}s, min_kf={min_keyframes_for_update}")
    
    def add_frame(self, frame_data: dict) -> bool:
        """
        添加SLAM帧数据
        
        Args:
            frame_data: SLAM帧数据，包含image_base64, pose, dense_points等
        
        Returns:
            是否成功添加
        """
        # 收集关键帧
        added = self.keyframe_collector.add_frame(frame_data)
        
        if added:
            # 检查是否需要更新高斯模型
            if self._should_update():
                self._trigger_update(frame_data)
        
        return added
    
    def _should_update(self) -> bool:
        """检查是否应该更新高斯模型"""
        now = time.time()
        stats = self.keyframe_collector.get_stats()
        
        # 条件1：距离上次更新超过间隔时间
        time_condition = (now - self.last_update_time) >= self.update_interval
        
        # 条件2：有足够的关键帧
        kf_condition = stats['keyframes'] >= self.min_keyframes_for_update
        
        # 条件3：当前不在更新中
        not_updating = not self.is_updating
        
        return time_condition and kf_condition and not_updating
    
    def _trigger_update(self, current_frame: dict):
        """触发高斯模型更新"""
        self.is_updating = True
        self.last_update_time = time.time()
        self.update_count += 1
        
        print(f"[RealtimeGaussianUpdater] Triggering update #{self.update_count}")
        
        try:
            # 增量更新高斯模型
            self._incremental_update(current_frame)
            
            # 保存模型
            self._save_model()
            
            print(f"[RealtimeGaussianUpdater] Update #{self.update_count} complete: {len(self.current_means)} gaussians")
            
        except Exception as e:
            print(f"[RealtimeGaussianUpdater] Update error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.is_updating = False
    
    def _incremental_update(self, current_frame: dict):
        """增量更新高斯模型"""
        # 从当前帧提取新高斯
        new_means, new_colors, new_scales, new_opacities = self._extract_gaussians_from_frame(current_frame)
        
        if len(new_means) == 0:
            return
        
        # 合并新高斯到当前模型
        if len(self.current_means) == 0:
            # 首次更新
            self.current_means = new_means
            self.current_colors = new_colors
            self.current_scales = new_scales
            self.current_opacities = new_opacities
        else:
            # 增量添加
            self.current_means = np.vstack([self.current_means, new_means])
            self.current_colors = np.vstack([self.current_colors, new_colors])
            self.current_scales = np.vstack([self.current_scales, new_scales])
            self.current_opacities = np.concatenate([self.current_opacities, new_opacities])
        
        # 限制最大高斯数
        if len(self.current_means) > self.max_gaussians:
            self._prune_gaussians()
    
    def _extract_gaussians_from_frame(self, frame_data: dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """从帧数据提取高斯参数"""
        means = []
        colors = []
        scales = []
        opacities = []
        
        # 从密集点云提取
        if 'dense_points' in frame_data and len(frame_data['dense_points']) >= 3:
            points = np.array(frame_data['dense_points']).reshape(-1, 3)
            colors_data = np.array(frame_data.get('dense_colors', [])).reshape(-1, 3) if frame_data.get('dense_colors') else None
            
            # 采样点（最多500个）
            sample_count = min(500, len(points))
            if sample_count < len(points):
                indices = np.random.choice(len(points), sample_count, replace=False)
                points = points[indices]
                if colors_data is not None:
                    colors_data = colors_data[indices]
            
            for i, pt in enumerate(points):
                # 坐标转换
                x, y, z = pt[0], -pt[1], -pt[2]
                
                # 过滤异常点
                if abs(x) > 20 or abs(y) > 20 or abs(z) > 20:
                    continue
                
                means.append([x, y, z])
                
                # 颜色
                if colors_data is not None and i < len(colors_data):
                    colors.append(colors_data[i])
                else:
                    colors.append([0.7, 0.7, 0.7])
                
                # 尺度（基于深度）
                depth = np.sqrt(x*x + y*y + z*z)
                scale = max(0.02, min(0.15, depth * 0.04))
                scales.append([scale, scale, scale])
                
                # 不透明度（基于深度）
                opacity = max(0.3, min(0.85, 1.0 - depth / 15.0))
                opacities.append(opacity)
        
        return (np.array(means), np.array(colors), 
                np.array(scales), np.array(opacities))
    
    def _prune_gaussians(self):
        """修剪高斯模型（保留高质量高斯）"""
        if len(self.current_means) <= self.max_gaussians:
            return
        
        # 基于不透明度排序，保留高不透明度高斯
        indices = np.argsort(-self.current_opacities)
        keep_indices = indices[:self.max_gaussians]
        
        self.current_means = self.current_means[keep_indices]
        self.current_colors = self.current_colors[keep_indices]
        self.current_scales = self.current_scales[keep_indices]
        self.current_opacities = self.current_opacities[keep_indices]
        
        print(f"[RealtimeGaussianUpdater] Pruned to {len(self.current_means)} gaussians")
    
    def _save_model(self):
        """保存高斯模型"""
        model_data = {
            'means': self.current_means.tolist(),
            'colors': self.current_colors.tolist(),
            'scales': self.current_scales.tolist(),
            'opacities': self.current_opacities.tolist(),
            'num_gaussians': len(self.current_means),
            'update_count': self.update_count,
            'last_update_time': self.last_update_time
        }
        
        with open(self.model_path, 'w') as f:
            json.dump(model_data, f)
    
    def get_model(self) -> Dict:
        """获取当前高斯模型"""
        return {
            'means': self.current_means.tolist() if len(self.current_means) > 0 else [],
            'colors': self.current_colors.tolist() if len(self.current_colors) > 0 else [],
            'scales': self.current_scales.tolist() if len(self.current_scales) > 0 else [],
            'opacities': self.current_opacities.tolist() if len(self.current_opacities) > 0 else [],
            'num_gaussians': len(self.current_means),
            'update_count': self.update_count,
            'is_updating': self.is_updating
        }
    
    def get_stats(self) -> Dict:
        """获取更新器状态"""
        kf_stats = self.keyframe_collector.get_stats()
        return {
            'keyframes': kf_stats['keyframes'],
            'total_frames': kf_stats['total_frames'],
            'gaussians': len(self.current_means),
            'update_count': self.update_count,
            'is_updating': self.is_updating,
            'last_update_time': self.last_update_time
        }
    
    def reset(self):
        """重置更新器"""
        self.keyframe_collector.reset()
        self.current_means = np.zeros((0, 3))
        self.current_colors = np.zeros((0, 3))
        self.current_scales = np.zeros((0, 3))
        self.current_opacities = np.zeros(0)
        self.last_update_time = 0.0
        self.update_count = 0
        self.is_updating = False
        print("[RealtimeGaussianUpdater] Reset")
