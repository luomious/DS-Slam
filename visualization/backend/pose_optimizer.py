"""
位姿优化器 - 基于3D高斯光度误差优化SLAM相机位姿

功能：
1. 使用光度误差梯度优化相机位姿
2. 支持紧耦合优化（几何误差+光度误差）
3. 动态权重调整（静态区域优先）
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from photometric_error import PhotometricErrorCalculator


class PoseOptimizer:
    """基于光度误差的相机位姿优化器"""
    
    def __init__(self, 
                 photometric_calculator: PhotometricErrorCalculator,
                 learning_rate: float = 0.01,
                 max_iterations: int = 50,
                 convergence_threshold: float = 1e-4):
        self.photometric = photometric_calculator
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        
        # 动态权重参数
        self.static_weight = 0.7  # 静态区域权重
        self.dynamic_weight = 0.3  # 动态区域权重
        
        print(f"[PoseOptimizer] Initialized: lr={learning_rate}, max_iter={max_iterations}")
    
    def optimize_pose(self,
                     means: np.ndarray,
                     colors: np.ndarray,
                     scales: np.ndarray,
                     opacities: np.ndarray,
                     initial_pose: Dict[str, float],
                     real_image: np.ndarray,
                     dynamic_mask: Optional[np.ndarray] = None) -> Tuple[Dict[str, float], Dict]:
        """
        优化相机位姿
        
        Args:
            means, colors, scales, opacities: 高斯模型参数
            initial_pose: 初始相机位姿
            real_image: 真实图像
            dynamic_mask: 动态区域掩码（可选）
        
        Returns:
            (优化后的位姿, 优化信息)
        """
        current_pose = initial_pose.copy()
        errors = []
        
        for iteration in range(self.max_iterations):
            # 计算光度误差
            rendered = self.photometric.render_gaussian_image(
                means, colors, scales, opacities, current_pose
            )
            
            # 应用动态权重
            if dynamic_mask is not None:
                # 静态区域使用高权重，动态区域使用低权重
                weight_map = np.ones_like(dynamic_mask)
                weight_map[dynamic_mask > 0.5] = self.dynamic_weight
                weight_map[dynamic_mask <= 0.5] = self.static_weight
                
                error_value, error_map = self.photometric.compute_photometric_error(
                    rendered, real_image, mask=weight_map
                )
            else:
                error_value, error_map = self.photometric.compute_photometric_error(
                    rendered, real_image
                )
            
            errors.append(error_value)
            
            # 检查收敛
            if iteration > 0 and abs(errors[-2] - errors[-1]) < self.convergence_threshold:
                print(f"[PoseOptimizer] Converged at iteration {iteration}: error={error_value:.6f}")
                break
            
            # 计算位姿梯度
            gradients = self.photometric.compute_pose_gradient(
                means, colors, scales, opacities, current_pose, real_image
            )
            
            # 更新位姿（梯度下降）
            current_pose = self._update_pose(current_pose, gradients)
            
            if iteration % 10 == 0:
                print(f"[PoseOptimizer] Iteration {iteration}: error={error_value:.6f}")
        
        info = {
            'final_error': errors[-1] if errors else 0.0,
            'iterations': len(errors),
            'error_history': errors,
            'converged': len(errors) < self.max_iterations
        }
        
        return current_pose, info
    
    def _update_pose(self, pose: Dict[str, float], gradients: Dict[str, float]) -> Dict[str, float]:
        """根据梯度更新位姿"""
        updated_pose = pose.copy()
        
        # 更新平移
        for key in ['tx', 'ty', 'tz']:
            if key in gradients:
                updated_pose[key] = pose.get(key, 0.0) - self.learning_rate * gradients[key]
        
        # 更新旋转（简化：直接调整四元数）
        if 'rx' in gradients or 'ry' in gradients or 'rz' in gradients:
            # 将旋转梯度转换为四元数更新
            current_qw = pose.get('qw', 1.0)
            current_qx = pose.get('qx', 0.0)
            current_qy = pose.get('qy', 0.0)
            current_qz = pose.get('qz', 0.0)
            
            # 小角度旋转更新
            delta_rx = gradients.get('rx', 0.0) * self.learning_rate
            delta_ry = gradients.get('ry', 0.0) * self.learning_rate
            delta_rz = gradients.get('rz', 0.0) * self.learning_rate
            
            # 创建增量旋转四元数
            angle = np.sqrt(delta_rx**2 + delta_ry**2 + delta_rz**2)
            if angle > 1e-6:
                axis = np.array([delta_rx, delta_ry, delta_rz]) / angle
                half_angle = angle / 2.0
                
                dqw = np.cos(half_angle)
                dqx = axis[0] * np.sin(half_angle)
                dqy = axis[1] * np.sin(half_angle)
                dqz = axis[2] * np.sin(half_angle)
                
                # 四元数乘法：q_new = dq * q_old
                updated_pose['qw'] = dqw * current_qw - dqx * current_qx - dqy * current_qy - dqz * current_qz
                updated_pose['qx'] = dqw * current_qx + dqx * current_qw + dqy * current_qz - dqz * current_qy
                updated_pose['qy'] = dqw * current_qy - dqx * current_qz + dqy * current_qw + dqz * current_qx
                updated_pose['qz'] = dqw * current_qz + dqx * current_qy - dqy * current_qx + dqz * current_qw
                
                # 归一化
                norm = np.sqrt(updated_pose['qw']**2 + updated_pose['qx']**2 + 
                              updated_pose['qy']**2 + updated_pose['qz']**2)
                updated_pose['qw'] /= norm
                updated_pose['qx'] /= norm
                updated_pose['qy'] /= norm
                updated_pose['qz'] /= norm
        
        return updated_pose
    
    def set_weights(self, static_weight: float, dynamic_weight: float):
        """设置动态权重"""
        self.static_weight = static_weight
        self.dynamic_weight = dynamic_weight
        print(f"[PoseOptimizer] Weights updated: static={static_weight}, dynamic={dynamic_weight}")
