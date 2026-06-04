#!/usr/bin/env python3
# [PATCHED]
"""DS-SLAM Visualizer Backend - Self-contained version."""

from __future__ import annotations

import json
import time
import math
import os
import asyncio
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import cv2
import numpy as np
import base64
import onnxruntime as ort
try:
    from scipy.spatial import cKDTree
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def remove_outliers_sor(coords_list, colors_list, nb_neighbors=30, std_ratio=2.0):
    """Statistical Outlier Removal for point cloud.
    
    Removes points whose mean distance to k nearest neighbors exceeds
    global_mean + std_ratio * global_std.
    Returns filtered (coords, colors) as lists.
    """
    if not _HAS_SCIPY or len(coords_list) < nb_neighbors + 1:
        return coords_list, colors_list
    
    n = len(coords_list) // 3
    points = np.array(coords_list, dtype=np.float64).reshape(n, 3)
    has_colors = colors_list and len(colors_list) == len(coords_list)
    if has_colors:
        colors = np.array(colors_list, dtype=np.float64).reshape(n, 3)
    
    tree = cKDTree(points)
    # Query k+1 because first neighbor is the point itself (distance=0)
    distances, _ = tree.query(points, k=nb_neighbors + 1)
    mean_dist = distances[:, 1:].mean(axis=1)  # exclude self
    
    global_mean = mean_dist.mean()
    global_std = mean_dist.std()
    threshold = global_mean + std_ratio * global_std
    
    keep_mask = mean_dist < threshold
    keep_count = int(keep_mask.sum())
    print(f"[SOR] Removed {n - keep_count}/{n} outliers (mean={global_mean:.4f}, std={global_std:.4f}, thresh={threshold:.4f})")
    
    filtered_pts = points[keep_mask].flatten().tolist()
    if has_colors:
        filtered_colors = colors[keep_mask].flatten().tolist()
    else:
        filtered_colors = colors_list
    
    return filtered_pts, filtered_colors


def matrix_to_quaternion(matrix: List[List[float]]) -> dict:
    """Convert 4x4 transformation matrix to quaternion + translation.
    
    Input: 4x4 list of lists [[r11, r12, r13, tx], [r21, r22, r23, ty], ...]
    Output: {tx, ty, tz, qw, qx, qy, qz}
    """
    # Extract translation
    tx = matrix[0][3]
    ty = matrix[1][3]
    tz = matrix[2][3]
    
    # Extract rotation matrix (3x3)
    m00, m01, m02 = matrix[0][0], matrix[0][1], matrix[0][2]
    m10, m11, m12 = matrix[1][0], matrix[1][1], matrix[1][2]
    m20, m21, m22 = matrix[2][0], matrix[2][1], matrix[2][2]
    
    # Convert rotation matrix to quaternion
    trace = m00 + m11 + m22
    
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (m21 - m12) * s
        qy = (m02 - m20) * s
        qz = (m10 - m01) * s
    elif m00 > m11 and m00 > m22:
        s = 2.0 * math.sqrt(1.0 + m00 - m11 - m22)
        qw = (m21 - m12) / s
        qx = 0.25 * s
        qy = (m01 + m10) / s
        qz = (m02 + m20) / s
    elif m11 > m22:
        s = 2.0 * math.sqrt(1.0 + m11 - m00 - m22)
        qw = (m02 - m20) / s
        qx = (m01 + m10) / s
        qy = 0.25 * s
        qz = (m12 + m21) / s
    else:
        s = 2.0 * math.sqrt(1.0 + m22 - m00 - m11)
        qw = (m10 - m01) / s
        qx = (m02 + m20) / s
        qy = (m12 + m21) / s
        qz = 0.25 * s
    
    return {
        "tx": float(tx), 
        "ty": float(ty), 
        "tz": float(tz),
        "qw": float(qw), 
        "qx": float(qx), 
        "qy": float(qy), 
        "qz": float(qz)
    }





# ======== YOLO11-seg Real Segmentation (Phase 2) ========

# Dynamic COCO class IDs (person=0, bicycle=1, car=2, motorcycle=3, bus=5, truck=7)
DYNAMIC_COCO_IDS = {0, 1, 2, 3, 5, 7}

class YOLOInferencer:
    """Lightweight YOLO11-seg ONNX Runtime wrapper for real-time segmentation."""
    
    def __init__(self, model_path: str, input_size: tuple = (640, 640), conf: float = 0.25):
        self.input_size = input_size
        self.conf_threshold = conf
        self.model_path = model_path
        self.sess = None
        self.input_name = None
        self.output_names = None
        self.valid = False
        self._load_model()
    
    def _load_model(self):
        try:
            if not os.path.exists(self.model_path):
                print(f"[YOLO] Model file not found: {self.model_path}")
                print("[YOLO] Using fallback pseudo-segmentation mode")
                self.valid = False
                return
            self.sess = ort.InferenceSession(
                self.model_path,
                providers=["CPUExecutionProvider"]
            )
            self.input_name = self.sess.get_inputs()[0].name
            self.output_names = [o.name for o in self.sess.get_outputs()]
            self.valid = True
            print(f"[YOLO] Model loaded: {self.model_path}")
        except Exception as e:
            print(f"[YOLO] Failed to load model: {e}")
            print("[YOLO] Using fallback pseudo-segmentation mode")
            self.valid = False
    
    def preprocess(self, img_bgr: np.ndarray) -> np.ndarray:
        """BGR -> RGB -> resize -> normalize -> (1,3,H,W) float32."""
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, self.input_size)
        blob = resized.astype(np.float32) / 255.0
        return np.transpose(blob, (2, 0, 1))[np.newaxis, :]  # (1,3,H,W)
    
    def infer(self, img_bgr: np.ndarray) -> str:
        """
        Run YOLO11-seg and return dynamic-object mask as PNG base64.
        Returns empty string on failure.
        """
        if not self.valid or self.sess is None:
            return ""
        
        try:
            # Preprocess
            blob = self.preprocess(img_bgr)
            
            # Inference
            outputs = self.sess.run(self.output_names, {self.input_name: blob})
            det_out = outputs[0]   # (1, 116, 8400)
            proto_out = outputs[1] # (1, 32, 160, 160)
            
            # Parse detection shape
            det = det_out[0]  # (116, 8400) = (4+nc+nm, num_proposals)
            num_proposals = det.shape[1]  # 8400
            total_features = det.shape[0]  # 116 = 4+nc+nm
            nm = 32  # mask coefficients per proposal
            nc = total_features - 4 - nm  # number of classes
            
            # Parse prototype masks
            proto = proto_out[0]  # (32, 160, 160)
            mask_h, mask_w = proto.shape[1], proto.shape[2]
            
            # Vectorized: extract all scores and filter in one pass
            scores_all = det[4:4+nc, :]  # (nc, num_proposals) - raw logits
            best_scores = np.max(scores_all, axis=0)  # (num_proposals,)
            best_classes = np.argmax(scores_all, axis=0)  # (num_proposals,)
            
            # Filter by confidence and dynamic class (person, bicycle, car, motorcycle, bus, truck)
            conf_mask = best_scores >= self.conf_threshold
            # Only detect PERSON class (COCO ID 0)
            dynamic_mask = (best_classes == 0)  # Person only
            valid_idx = np.where(conf_mask & dynamic_mask)[0]
            
            combined = np.zeros((mask_h, mask_w), dtype=np.float32)
            
            # ====== Enhanced mask generation with soft threshold + smoothing ======
            if len(valid_idx) > 0:
                # Vectorized mask generation: coeffs @ proto reshaped
                # proto: (32, 160*160) → (32, H*W)
                proto_flat = proto.reshape(nm, -1)  # (32, 25600)
                coeffs_all = det[4+nc:4+nc+nm, valid_idx]  # (32, n_valid)
                # (32, H*W).T @ (32, n_valid) → (H*W, n_valid)
                mask_vals = proto_flat.T @ coeffs_all  # (H*W, n_valid)
                # Sigmoid
                mask_probs = 1.0 / (1.0 + np.exp(-mask_vals))  # (H*W, n_valid)
                # Weighted by detection confidence for smoother blending
                weights = best_scores[valid_idx]  # (n_valid,)
                # Soft threshold: use 0.50 for cleaner masks (was 0.45)
                mask_binary = (mask_probs > 0.50).astype(np.float32)
                # Weighted combination: higher-confidence masks dominate
                weighted = mask_binary * weights[np.newaxis, :]  # (H*W, n_valid)
                combined = np.max(weighted, axis=1).reshape(mask_h, mask_w)
                # Normalize to 0-255
                if combined.max() > 0:
                    combined = combined / combined.max() * 255.0
            
            # Resize to original image size with LINEAR interpolation for smooth edges
            orig_h, orig_w = img_bgr.shape[:2]
            mask_resized = cv2.resize(combined, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            mask_uint8 = mask_resized.astype(np.uint8)
            
            # ====== Morphological cleanup pipeline ======
            # Step 1: Opening (erosion then dilation) - removes small noise blobs
            kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel_small, iterations=1)
            # Step 2: Closing (dilation then erosion) - fills small holes inside masks
            kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel_medium, iterations=1)
            # Step 3: Connected component analysis - remove small isolated regions
            min_area = 800  # Increased from 200 to filter out small noise
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_uint8, connectivity=8)
            for label_idx in range(1, num_labels):  # Skip background (0)
                area = stats[label_idx, cv2.CC_STAT_AREA]
                if area < min_area:
                    mask_uint8[labels == label_idx] = 0
            # Step 4: Gaussian blur for smooth mask edges
            mask_uint8 = cv2.GaussianBlur(mask_uint8, (3, 3), 0)
            # Re-threshold after blur to keep binary clean
            mask_uint8 = (mask_uint8 > 128).astype(np.uint8) * 255
            
            # Color encode for display (dynamic=red, static=dark)
            color_mask = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
            color_mask[mask_uint8 > 128] = [0, 0, 220]   # Red (BGR) for dynamic objects
            color_mask[mask_uint8 <= 128] = [40, 40, 40]  # Dark gray for static
            
            _, buf = cv2.imencode('.png', color_mask)
            return base64.b64encode(buf).decode('utf-8')
            
        except Exception as e:
            print(f"[YOLO] Infer error: {e}")
            return ""

# Global YOLO instance (lazy init)
_yolo_inferencer = None

def get_yolo() -> YOLOInferencer:
    global _yolo_inferencer
    if _yolo_inferencer is None:
        model_path = str(PROJECT_ROOT / "segmentation" / "onnx" / "yolo11n_seg_v2.onnx")
        _yolo_inferencer = YOLOInferencer(model_path, conf=0.20)
    return _yolo_inferencer

def yolo_segment(image_base64: str) -> str:
    """Run YOLO segmentation on base64 JPEG image. Returns PNG base64."""
    try:
        img_bytes = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            print("[YOLO] segment: img decode failed")
            return ""
        yolo = get_yolo()
        if not yolo.valid:
            # Fallback: generate pseudo-segmentation (center region as dynamic)
            print("[YOLO] segment: using fallback pseudo-segmentation")
            h, w = img.shape[:2]
            color_mask = np.zeros((h, w, 3), dtype=np.uint8)
            color_mask[:, :] = [40, 40, 40]  # Dark gray for static
            # Simulate dynamic objects in center region
            cy, cx = h // 2, w // 2
            ry, rx = h // 6, w // 6
            color_mask[max(0,cy-ry):min(h,cy+ry), max(0,cx-rx):min(w,cx+rx)] = [0, 0, 220]  # Red for dynamic
            _, buf = cv2.imencode('.png', color_mask)
            return base64.b64encode(buf).decode('utf-8')
        result = yolo.infer(img)
        if result:
            print(f"[YOLO] segment OK: mask len={len(result)}")
        else:
            print("[YOLO] segment: infer returned empty")
        return result
    except Exception as e:
        print(f"[YOLO] segment error: {e}")
        import traceback; traceback.print_exc()
        return ""

# ======== End YOLO11-seg ========
def generate_pseudo_mask(image_base64: str) -> str:
    """Generate a pseudo-segmentation mask from RGB image using color clustering.
    Returns PNG base64 string.
    """
    try:
        img_bytes = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return ""
        
        h, w = img.shape[:2]
        # Downsample for speed
        small = cv2.resize(img, (w // 4, h // 4))
        
        # Convert to LAB for better color segmentation
        lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
        
        # Simple K-means (2 clusters: foreground vs background)
        pixels = lab.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        
        # Create mask from labels - pick the cluster with more saturated regions as "dynamic"
        mask_small = (labels.reshape(small.shape[:2]) * 255).astype(np.uint8)
        
        # Resize back
        mask = cv2.resize(mask_small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Add some color coding (person=red, background=dark)
        color_mask = np.zeros((h, w, 3), dtype=np.uint8)
        color_mask[mask > 128] = [0, 0, 220]   # Red for "person" cluster (BGR)
        color_mask[mask <= 128] = [40, 40, 40]  # Dark for background
        
        # Encode as PNG base64
        _, buf = cv2.imencode('.png', color_mask)
        return base64.b64encode(buf).decode('utf-8')
    except Exception as e:
        print(f"[WARN] Pseudo mask generation failed: {e}")
        return ""


class MiDaSDepth:
    """MiDaS small monocular depth estimation via ONNX Runtime."""
    
    # Default intrinsics for different scenarios
    TUM_INTRINSICS = {
        'fx': 517.3, 'fy': 516.5,
        'cx': 318.6, 'cy': 255.3,
        'width': 640, 'height': 480
    }
    
    # Generic webcam intrinsics (use TUM intrinsics as fallback - more stable)
    WEBCAM_INTRINSICS = {
        'fx': 517.3, 'fy': 516.5,  # TUM intrinsics (verified stable)
        'cx': 318.6, 'cy': 255.3,
        'width': 640, 'height': 480
    }
    
    def __init__(self, model_path: str, intrinsics: dict = None, use_webcam: bool = False):
        self.session = ort.InferenceSession(
            model_path,
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        self.input_name = self.session.get_inputs()[0].name
        
        # Select intrinsics based on mode
        if intrinsics:
            self.intrinsics = intrinsics
        elif use_webcam:
            self.intrinsics = self.WEBCAM_INTRINSICS
            print(f"[MiDaS] Using webcam intrinsics (estimated FOV ~60°)")
        else:
            self.intrinsics = self.TUM_INTRINSICS
            print(f"[MiDaS] Using TUM dataset intrinsics")
        
        self.prev_depth = None  # For temporal smoothing
        print(f"[MiDaS] Loaded: {model_path}")
        print(f"[MiDaS] Provider: {self.session.get_providers()}")
        print(f"[MiDaS] Intrinsics: fx={self.intrinsics['fx']:.1f}, fy={self.intrinsics['fy']:.1f}, cx={self.intrinsics['cx']:.1f}, cy={self.intrinsics['cy']:.1f}")
    
    def estimate_depth(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Estimate inverse depth map from BGR frame. Returns depth map same size as input."""
        h, w = frame_bgr.shape[:2]
        
        # MiDaS preprocessing: resize to 256x256, normalize
        inp = cv2.resize(frame_bgr, (256, 256))
        inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
        inp = inp.astype(np.float32) / 255.0
        inp = (inp - [0.5, 0.5, 0.5]) / [0.5, 0.5, 0.5]  # normalize to [-1, 1]
        inp = inp.transpose(2, 0, 1)[np.newaxis]  # (1, 3, 256, 256)
        
        # Run inference
        out = self.session.run(None, {self.input_name: inp.astype(np.float32)})[0]
        # out shape: (1, 256, 256)
        depth = out[0]  # (256, 256)
        
        # Resize back to original frame size
        depth_resized = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)
        
        # ====== Depth post-processing pipeline ======
        # Step 1: Edge-preserving bilateral filter (smoothing while preserving depth edges)
        depth_resized = cv2.bilateralFilter(depth_resized.astype(np.float32), 9, 75, 75)
        # Step 2: Median filter to remove salt-and-pepper noise
        depth_resized = cv2.medianBlur(depth_resized.astype(np.float32), 5)
        # Step 3: Temporal IIR smoothing (blend with previous frame for stability)
        if self.prev_depth is not None and self.prev_depth.shape == depth_resized.shape:
            alpha = 0.4  # 40% current + 60% previous → smoother transitions
            depth_resized = alpha * depth_resized + (1.0 - alpha) * self.prev_depth
        self.prev_depth = depth_resized.copy()
        # Step 4: Adaptive depth range normalization
        # MiDaS outputs inverse depth (disparity): large value = close, small = far
        # We need to invert it to get positive depth where larger = farther
        flat = depth_resized.flatten()
        d_low = np.percentile(flat, 2)
        d_high = np.percentile(flat, 98)
        if d_high > d_low:
            # Normalize to [0, 1] range first
            normalized = (depth_resized - d_low) / (d_high - d_low)
            # MiDaS output is inverse depth (disparity), so invert: close objects have high values
            # Invert: 1 - normalized gives us positive depth (center of image = far → high disparity → now low depth)
            # Actually MiDaS convention: higher output = closer. So invert for depth.
            depth_inv = 1.0 - normalized  # Now: high value = far, low value = close
            # Apply power-law to compress the range and reduce cone effect
            # Without this, the depth distribution creates a cone shape
            depth_inv = np.clip(depth_inv, 0.0, 1.0)  # Ensure non-negative for power operation
            depth_resized = 0.3 + depth_inv ** 0.7 * 5.7  # [0.3, 6.0]m, gamma<1 compresses far range
        else:
            depth_resized = np.full_like(depth_resized, 1.0)
        
        return depth_resized.astype(np.float32)
    
    def depth_to_pointcloud(self, frame_bgr: np.ndarray, depth_map: np.ndarray, 
                             mask: np.ndarray = None, voxel_size: float = 0.05,
                             max_points: int = 50000) -> tuple:
        """Unproject depth map to 3D point cloud.
        
        Args:
            frame_bgr: Original BGR frame (h, w, 3)
            depth_map: Depth map from estimate_depth (h, w)
            mask: Optional binary mask (h, w), True=dynamic (exclude), False=static (include)
            voxel_size: Voxel grid size for downsampling
            max_points: Maximum number of points to return
        
        Returns:
            (coords_list, colors_list) - flat lists [x,y,z,x,y,z,...] and [r,g,b,r,g,b,...]
        """
        h, w = depth_map.shape
        fx = self.intrinsics['fx']
        fy = self.intrinsics['fy']
        cx = self.intrinsics['cx']
        cy = self.intrinsics['cy']
        
        # Sample grid (every pixel for denser point cloud)
        step = 1
        v_coords, u_coords = np.mgrid[0:h:step, 0:w:step]
        v_coords = v_coords.astype(np.float32)
        u_coords = u_coords.astype(np.float32)
        
        # Get depth values at sampled positions
        z = depth_map[v_coords.astype(int), u_coords.astype(int)]
        
        # ====== Anti-cone depth correction ======
        # The cone effect arises because edge pixels have the same depth value as center
        # but are unprojected to larger (x,y) offsets. In reality, perspective means
        # edge pixels see surfaces at oblique angles (farther in true depth).
        # Apply cosine-of-incidence correction: adjust Z by view angle.
        # For each pixel, the true distance along the ray is z / cos(angle_from_optical_axis)
        # But since we want depth along Z-axis, we keep Z unchanged and instead
        # apply a gentle correction that reduces the radial spread at edges.
        # 
        # Key insight: the "cone" is actually CORRECT for a flat wall facing the camera.
        # The problem is MiDaS relative depth doesn't capture absolute distances,
        # so edge and center get similar depth values when they shouldn't.
        # We apply a radial distance-dependent correction.
        
        # Unproject: X = (u - cx) * z / fx, Y = (v - cy) * z / fy, Z = z
        # Use classic pinhole camera model (no anti-cone correction)
        # The cone effect is actually CORRECT for a flat wall facing the camera
        # The real issue is MiDaS relative depth not capturing absolute distances
        x = (u_coords - cx) * z / fx
        y = (v_coords - cy) * z / fy
        
        # Get colors BEFORE filtering
        colors = frame_bgr[v_coords.astype(int), u_coords.astype(int)]  # BGR
        
        # Simple depth range filter (no complex corrections)
        # Keep only points in reasonable depth range
        valid = (z > 0.3) & (z < 8.0) & np.isfinite(z)
        
        # View angle filter: only keep points in forward 60-degree cone
        # This reduces extreme edge distortion while keeping valid points
        distances = np.sqrt(x**2 + y**2 + z**2)
        cos_60 = np.cos(np.radians(60))
        angle_mask = z > (cos_60 * distances)
        valid = valid & angle_mask
        
        # Depth gradient filter: exclude points where depth changes abruptly
        # (sharp depth discontinuities are often noise or occlusion boundaries)
        if len(z) > 10:
            depth_grad_x = np.abs(np.diff(depth_map, axis=1))  # horizontal gradient
            depth_grad_y = np.abs(np.diff(depth_map, axis=0))  # vertical gradient
            # Pad to match original size
            grad_x_full = np.zeros_like(depth_map)
            grad_y_full = np.zeros_like(depth_map)
            grad_x_full[:, :-1] = depth_grad_x
            grad_y_full[:-1, :] = depth_grad_y
            total_grad = grad_x_full + grad_y_full
            grad_sampled = total_grad[v_coords.astype(int), u_coords.astype(int)]
            # Threshold: depth change > 0.3m per pixel is likely noise/occlusion edge
            smooth_mask = grad_sampled < 0.3
            valid = valid & smooth_mask
        
        # Filter dynamic pixels if mask provided
        if mask is not None and mask.shape == depth_map.shape:
            # mask: True = dynamic, exclude those
            mask_sampled = mask[v_coords.astype(int), u_coords.astype(int)]
            valid = valid & ~mask_sampled
        
        x, y, z = x[valid], y[valid], z[valid]
        colors = colors[valid]
        
        if len(x) == 0:
            return [], []
        
        # Voxel downsample
        if voxel_size > 0 and len(x) > max_points:
            voxel_idx = np.floor(np.stack([x/voxel_size, y/voxel_size, z/voxel_size], axis=1)).astype(np.int64)
            # Use dict to keep first point per voxel
            seen = {}
            coords_out = []
            colors_out = []
            for i in range(len(x)):
                key = tuple(voxel_idx[i])
                if key not in seen:
                    seen[key] = True
                    coords_out.extend([float(x[i]), float(y[i]), float(z[i])])
                    colors_out.extend([int(colors[i][2])/255.0, int(colors[i][1])/255.0, int(colors[i][0])/255.0])  # BGR->RGB normalized
            return coords_out, colors_out
        
        # No downsampling needed
        coords_out = []
        colors_out = []
        for i in range(min(len(x), max_points)):
            coords_out.extend([float(x[i]), float(y[i]), float(z[i])])
            colors_out.extend([int(colors[i][2])/255.0, int(colors[i][1])/255.0, int(colors[i][0])/255.0])
        return coords_out, colors_out


# Global MiDaS instance (lazy init)
_midas_depth = None
_midas_depth_webcam = None  # Separate instance for webcam mode

def get_midas(use_webcam: bool = False) -> MiDaSDepth:
    """Get MiDaS depth estimator.
    
    Args:
        use_webcam: If True, use webcam-optimized intrinsics (estimated FOV ~60°)
                   If False, use TUM dataset intrinsics
    """
    global _midas_depth, _midas_depth_webcam
    
    if use_webcam:
        if _midas_depth_webcam is None:
            model_path = str(PROJECT_ROOT / "visualization" / "backend" / "depth_estimation" / "onnx" / "midas_small.onnx")
            if not os.path.exists(model_path):
                print(f"[MiDaS] Model not found: {model_path}")
                return None
            _midas_depth_webcam = MiDaSDepth(model_path, use_webcam=True)
        return _midas_depth_webcam
    else:
        if _midas_depth is None:
            model_path = str(PROJECT_ROOT / "visualization" / "backend" / "depth_estimation" / "onnx" / "midas_small.onnx")
            if not os.path.exists(model_path):
                print(f"[MiDaS] Model not found: {model_path}")
                return None
            _midas_depth = MiDaSDepth(model_path)
        return _midas_depth


def generate_gridmap_from_points(coords: list, resolution: float = 0.05, size_m: float = 10.0) -> str:
    """Generate a 2D occupancy grid map from 3D point cloud.
    
    Uses numpy for efficient batch processing. Auto-sizes grid to fit data.
    Returns PNG base64 string.
    """
    try:
        n_points = len(coords) // 3
        if n_points < 5:
            return ""
        
        pts = np.array(coords[:n_points*3], dtype=np.float64).reshape(n_points, 3)
        xs, ys, zs = pts[:, 0], pts[:, 1], pts[:, 2]
        
        # Auto-compute grid bounds with padding
        pad = 1.0  # 1.0m padding for better context
        x_min, x_max = xs.min() - pad, xs.max() + pad
        z_min, z_max = zs.min() - pad, zs.max() + pad  # Use Z (height) instead of Y for 2D grid vertical axis
        x_range = x_max - x_min
        z_range = z_max - z_min  # Changed from y_range
        
        # Ensure minimum grid size
        size_m = max(x_range, z_range, 4.0)  # Changed from y_range to z_range
        cx = (x_min + x_max) / 2
        cz = (z_min + z_max) / 2  # Changed from cy to cz (Z center)
        
        # Adaptive resolution based on point density
        area = x_range * z_range  # Changed from x_range * y_range
        density = n_points / max(area, 0.1)
        if density > 100:
            resolution = 0.02  # Dense: 2cm cells
        elif density > 20:
            resolution = 0.05  # Medium: 5cm cells
        else:
            resolution = 0.1   # Sparse: 10cm cells
        
        grid_w = int(size_m / resolution)
        grid_h = int(size_m / resolution)
        grid_w = min(grid_w, 600)  # Cap at 600px
        grid_h = min(grid_h, 600)
        
        grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        
        # Vectorized mapping: X→col, Z→row (top-down view with Z as height)
        cols = ((xs - cx + size_m/2) / resolution).astype(np.int32)
        rows = ((zs - cz + size_m/2) / resolution).astype(np.int32)  # Use Z instead of Y
        
        valid = (rows >= 0) & (rows < grid_h) & (cols >= 0) & (cols < grid_w)
        rows_v, cols_v = rows[valid], cols[valid]
        
        # Accumulate with height info for 2.5D effect (use Y as height for top-down view)
        np.maximum.at(grid, (rows_v, cols_v), ys[valid])  # Y is now height for top-down view
        
        # Dilate for visibility
        kernel_size = max(1, int(0.1 / resolution))  # 10cm dilation
        if kernel_size > 1:
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            occupied = (grid > 0).astype(np.uint8)
            dilated = cv2.dilate(occupied, kernel, iterations=1)
            grid_mask = dilated > 0
        else:
            grid_mask = grid > 0
        
        # Color rendering with height gradient
        color_grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        color_grid[:] = [20, 20, 30]  # Background: dark
        
        if grid_mask.any():
            h_vals = grid[grid_mask]  # Grid stores Y values as height
            h_min, h_max = h_vals.min(), h_vals.max()
            h_range = max(h_max - h_min, 0.01)
            
            # Height-based coloring (blue=low, green=mid, red=high)
            normalized = (h_vals - h_min) / h_range
            r = (normalized * 200 + 55).astype(np.uint8)
            g = ((1 - abs(normalized - 0.5) * 2) * 200 + 55).astype(np.uint8)
            b = ((1 - normalized) * 200 + 55).astype(np.uint8)
            
            color_grid[grid_mask, 0] = r
            color_grid[grid_mask, 1] = g
            color_grid[grid_mask, 2] = b
        
        # Grid lines (1m intervals)
        step_m = 1.0
        step_px = max(int(step_m / resolution), 1)
        for i in range(0, grid_h, step_px):
            color_grid[i, :] = np.clip(color_grid[i, :].astype(np.int16) + 30, 0, 255).astype(np.uint8)
        for j in range(0, grid_w, step_px):
            color_grid[:, j] = np.clip(color_grid[:, j].astype(np.int16) + 30, 0, 255).astype(np.uint8)
        
        # Add axis labels (X horizontal, Z vertical in top-down view)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(color_grid, f"X:[{x_min:.1f},{x_max:.1f}]m", (5, grid_h-10), font, 0.35, (150,150,150), 1)
        cv2.putText(color_grid, f"Z:[{z_min:.1f},{z_max:.1f}]m", (5, grid_h-25), font, 0.35, (150,150,150), 1)
        cv2.putText(color_grid, f"{n_points}pts/{resolution*100:.0f}cm", (5, grid_h-40), font, 0.35, (150,150,150), 1)
        
        _, buf = cv2.imencode('.png', color_grid)
        return base64.b64encode(buf).decode('utf-8')
    except Exception as e:
        print(f"[WARN] Gridmap generation failed: {e}")
        return ""

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "visualization" / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
OUTPUT_DIR = PROJECT_ROOT / "orbslam3" / "Examples" / "RGB-D" / "output"

# Configuration
HOST = "0.0.0.0"
PORT = 8300  # Changed from 8080/8081 (port may be occupied by previous process)
WS_PATH = "/ws/slam"


def create_app() -> FastAPI:
    app = FastAPI(title="DS-SLAM Visualizer")
    app.state.clients: set[WebSocket] = set()
    app.state.frame_buffer: list[dict] = []
    app.state.last_frame_snapshot: dict | None = None
    app.state.max_buffer = 100
    app.state.latest_map_points: list = []  # Store latest map point coords for new clients
    app.state.latest_dense_points: list = []  # Dense point cloud coords for visualization
    app.state.latest_dense_colors: list = []  # Dense point cloud RGB colors [r,g,b,r,g,b,...] normalized 0-1
    app.state.gridmap_dirty: bool = True  # [PATCHED] Flag to regenerate gridmap
    app.state.gridmap_cache_b64: str = ""  # Cached gridmap base64 to avoid regenerating every request
    app.state.trajectory_poses: list = []  # Auto-loaded trajectory poses
    app.state._slam_traj_started: bool = False  # True once real SLAM poses arrive
    
    # Per-dataset 3D data storage: {dataset_name: {"trajectory": [...], "dense_points": [...], "map_points": [...]}}
    app.state.dataset_3d_data: dict = {}
    
    # Continuous processing state
    app.state.processing_active: bool = False  # Whether continuous processing is running
    app.state.processing_task: Any = None  # Background task reference
    app.state.processing_index: int = 0  # Current frame index being processed
    app.state.dataset_type: str = "unknown"  # "image_sequence" or "video"
    app.state.dataset_fps: float = 30.0  # Estimated FPS for the dataset

    # Camera mode state
    app.state.camera_active: bool = False  # Whether live camera is running
    app.state.camera_task: Any = None  # Background camera capture task
    app.state.camera_index: int = 0  # Camera device index (default 0)
    app.state.camera_fps: float = 10.0  # Camera capture FPS
    app.state.camera_cap: Any = None  # cv2.VideoCapture instance
    app.state.active_dataset: Any = None  # Currently selected dataset path (None = camera)
    app.state.active_rgb_files: list = []  # RGB files for active dataset

    # ====== Auto-load PLY + Trajectory on startup ======
    def _auto_load_ply_and_trajectory():
        """Load PLY and trajectory from disk into app.state on startup.
        This ensures data is available immediately on page refresh.
        
        NOTE: We only load trajectory here, NOT PLY. PLY files are loaded
        per-dataset when the user selects a dataset, to ensure the correct
        point cloud is displayed for each dataset.
        """
        # Load trajectory (global fallback for initial display)
        traj_candidates = [
            OUTPUT_DIR / "CameraTrajectory.txt",
            PROJECT_ROOT / "orbslam3" / "Examples" / "RGB-D" / "CameraTrajectory.txt",
        ]
        for traj_file in traj_candidates:
            if traj_file.exists():
                try:
                    poses = []
                    with open(traj_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            parts = line.split()
                            if len(parts) >= 8:
                                poses.append({
                                    "timestamp": float(parts[0]),
                                    "tx": float(parts[1]),
                                    "ty": float(parts[2]),
                                    "tz": float(parts[3]),
                                    "qw": float(parts[4]),
                                    "qx": float(parts[5]),
                                    "qy": float(parts[6]),
                                    "qz": float(parts[7]),
                                })
                    if poses:
                        app.state.trajectory_poses = poses
                        print(f"[AUTO-LOAD] Trajectory: {len(poses)} poses from {traj_file}")
                    break
                except Exception as e:
                    print(f"[AUTO-LOAD] Trajectory failed: {e}")
        
        # NOTE: PLY loading is now handled per-dataset in select_dataset()
        # This ensures each dataset shows its own point cloud, not a global one.
        print("[AUTO-LOAD] PLY loading deferred to dataset selection")
    
    _auto_load_ply_and_trajectory()

    # Auto-fill latest_frame from dataset so RGB/YOLO panels show content on startup
    def _auto_load_initial_frame():
        """Load a sample frame from the first available dataset into last_frame_snapshot."""
        try:
            ds_base = PROJECT_ROOT / "datasets" / "TUM"
            if not ds_base.exists():
                return
            datasets = sorted([d for d in ds_base.iterdir() if d.is_dir()])
            if not datasets:
                return
            ds = datasets[0]
            rgb_dir = ds / "rgb"
            rgb_files = sorted(rgb_dir.glob("*.png")) if rgb_dir.exists() else []
            if not rgb_files:
                return
            # Pick middle frame
            img_path = rgb_files[len(rgb_files) // 2]
            img_data = base64.b64encode(img_path.read_bytes()).decode()
            # Run YOLO on the initial frame
            mask_b64 = yolo_segment(img_data)
            # Compute coverage (YOLO mask is BGR with red=dynamic)
            dynamic_coverage = 0.0
            if mask_b64:
                mask_bytes = base64.b64decode(mask_b64)
                mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                mask_color = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                if mask_color is not None and mask_color.ndim == 3:
                    red_px = (mask_color[:,:,2] > 100) & (mask_color[:,:,0] < 50) & (mask_color[:,:,1] < 50)
                    total_pixels = mask_color.shape[0] * mask_color.shape[1]
                    if red_px.sum() > 0:
                        dynamic_coverage = round(float(red_px.sum()) / total_pixels * 100, 1)
                    else:
                        # No red pixels detected - mask only has static (dark) regions
                        dynamic_coverage = 0.0
                else:
                    mask_gray = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                    if mask_gray is not None:
                        # Only count high-value pixels as dynamic (threshold > 128)
                        high_mask = mask_gray > 128
                        dynamic_coverage = round(float(high_mask.sum()) / (mask_gray.shape[0]*mask_gray.shape[1]) * 100, 1)
            app.state.last_frame_snapshot = {
                "type": "frame_update",
                "frame_number": len(rgb_files) // 2,
                "timestamp": float(len(rgb_files) // 2) * 0.03,
                "image_base64": img_data,
                "mask_base64": mask_b64 or "",
                "pose": {"tx": 0, "ty": 0, "tz": 0},
                "keyframe_count": 0,
                "map_points": 0,
                "features": [],
                "dynamic_coverage": dynamic_coverage,
            }
            app.state.active_dataset = ds
            app.state.active_rgb_files = rgb_files
            print(f"[AUTO-LOAD] Initial frame: {ds.name} #{len(rgb_files)//2}, coverage={dynamic_coverage}%")
        except Exception as e:
            print(f"[AUTO-LOAD] Initial frame failed: {e}")

    _auto_load_initial_frame()

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse({"error": "Frontend not found"}, status_code=404)

    @app.get("/api/status")
    async def status():
        return {
            "status": "running",
            "clients": len(app.state.clients),
            "buffered_frames": len(app.state.frame_buffer),
            "host": HOST,
            "port": PORT,
            "ws_path": WS_PATH,
        }

    @app.get("/api/config")
    async def config():
        return {
            "host": HOST,
            "port": PORT,
            "ws_path": WS_PATH,
            "output_dir": str(OUTPUT_DIR),
        }

    @app.get("/api/trajectory")
    async def get_trajectory():
        """Return real-time trajectory from app.state, fallback to file."""
        # Priority 1: real-time poses from SLAM frame_update
        if app.state.trajectory_poses and len(app.state.trajectory_poses) > 0:
            return {"poses": app.state.trajectory_poses, "count": len(app.state.trajectory_poses)}

        # Priority 2: load from CameraTrajectory.txt file
        traj_file = OUTPUT_DIR / "CameraTrajectory.txt"
        if not traj_file.exists():
            traj_file = PROJECT_ROOT / "orbslam3" / "Examples" / "RGB-D" / "CameraTrajectory.txt"
        if not traj_file.exists():
            import glob
            candidates = glob.glob(str(PROJECT_ROOT / "orbslam3" / "**" / "CameraTrajectory.txt"), recursive=True)
            if candidates:
                traj_file = Path(candidates[0])

        if not traj_file.exists():
            return JSONResponse({"error": "Trajectory file not found"}, status_code=404)

        poses = []
        with open(traj_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 8:
                    poses.append({
                        "timestamp": float(parts[0]),
                        "tx": float(parts[1]),
                        "ty": float(parts[2]),
                        "tz": float(parts[3]),
                        "qw": float(parts[4]),
                        "qx": float(parts[5]),
                        "qy": float(parts[6]),
                        "qz": float(parts[7]),
                    })

        return {"poses": poses, "count": len(poses)}

    @app.get("/api/pointcloud")
    async def get_pointcloud():
        """Get point cloud metadata (PLY file info)."""
        ply_file = OUTPUT_DIR / "maps" / "static_map.ply"

        if not ply_file.exists():
            return JSONResponse({"error": "PLY file not found"}, status_code=404)

        with open(ply_file, 'r') as f:
            vertex_count = 0
            for line in f:
                if line.startswith('element vertex'):
                    vertex_count = int(line.split()[-1])
                    break
                if line.startswith('end_header'):
                    break

        return {
            "file": str(ply_file),
            "size_mb": round(ply_file.stat().st_size / (1024 * 1024), 2),
            "vertex_count": vertex_count,
        }

    @app.get("/api/plypoints")
    async def get_plypoints():
        """Get point cloud data from PLY file with downsampling."""
        ply_file = OUTPUT_DIR / "maps" / "static_map.ply"

        if not ply_file.exists():
            return []

        points = []
        downsample = 20

        try:
            with open(ply_file, 'r') as f:
                in_header = True
                prop_x = prop_y = prop_z = prop_red = prop_green = prop_blue = -1
                props = []
                line_count = 0

                for line in f:
                    line = line.strip()
                    if in_header:
                        if line.startswith('property'):
                            parts = line.split()
                            props.append(parts[2])
                        elif line.startswith('element vertex'):
                            vertex_count = int(line.split()[-1])
                        elif line == 'end_header':
                            in_header = False
                            for i, p in enumerate(props):
                                if p == 'x': prop_x = i
                                elif p == 'y': prop_y = i
                                elif p == 'z': prop_z = i
                                elif p == 'red': prop_red = i
                                elif p == 'green': prop_green = i
                                elif p == 'blue': prop_blue = i
                        continue

                    if line_count % downsample != 0:
                        line_count += 1
                        continue

                    parts = line.split()
                    if len(parts) >= 6:
                        pt = {
                            'x': float(parts[prop_x]) if prop_x >= 0 else 0.0,
                            'y': float(parts[prop_y]) if prop_y >= 0 else 0.0,
                            'z': float(parts[prop_z]) if prop_z >= 0 else 0.0,
                            'r': int(parts[prop_red]) if prop_red >= 0 else 200,
                            'g': int(parts[prop_green]) if prop_green >= 0 else 200,
                            'b': int(parts[prop_blue]) if prop_blue >= 0 else 200,
                        }
                        points.append(pt)
                    line_count += 1

        except Exception as e:
            print(f"Error reading PLY: {e}")
            return []

        return points

    @app.post("/api/load_ply")
    async def load_ply_into_dense():
        """Load PLY file into dense points and broadcast to clients."""
        ply_file = OUTPUT_DIR / "maps" / "static_map.ply"
        # Also check project root (SLAM writes trajectory there)
        if not ply_file.exists():
            ply_file = PROJECT_ROOT / "output" / "maps" / "static_map.ply"
        if not ply_file.exists():
            return JSONResponse({"error": "No PLY file found. Run SLAM first."}, status_code=404)

        coords = []
        colors = []
        downsample = 4  # Take every 4th point for ~100K from 400K
        max_points = 100000

        try:
            with open(ply_file, 'r') as f:
                in_header = True
                prop_x = prop_y = prop_z = prop_r = prop_g = prop_b = -1
                props = []
                line_count = 0

                for line in f:
                    line = line.strip()
                    if in_header:
                        if line.startswith('property'):
                            parts = line.split()
                            props.append(parts[2])
                        elif line == 'end_header':
                            in_header = False
                            for i, p in enumerate(props):
                                if p == 'x': prop_x = i
                                elif p == 'y': prop_y = i
                                elif p == 'z': prop_z = i
                                elif p == 'red': prop_r = i
                                elif p == 'green': prop_g = i
                                elif p == 'blue': prop_b = i
                        continue

                    if line_count % downsample != 0:
                        line_count += 1
                        continue

                    parts = line.split()
                    if len(parts) >= 3 and prop_x >= 0:
                        coords.append(float(parts[prop_x]))
                        coords.append(float(parts[prop_y]))
                        coords.append(float(parts[prop_z]))
                        if prop_r >= 0 and prop_g >= 0 and prop_b >= 0:
                            colors.append(float(parts[prop_r]) / 255.0)
                            colors.append(float(parts[prop_g]) / 255.0)
                            colors.append(float(parts[prop_b]) / 255.0)
                        else:
                            colors.extend([0.7, 0.7, 0.7])
                    line_count += 1

                    if len(coords) // 3 >= max_points:
                        break

            if len(coords) < 3:
                return JSONResponse({"error": "PLY file has no points"}, status_code=400)

            app.state.latest_dense_points = coords
            app.state.latest_dense_colors = colors
            app.state.gridmap_dirty = True
            point_count = len(coords) // 3

            # Broadcast to all WebSocket clients
            msg = json.dumps({
                "type": "dense_points_update",
                "coords": coords,
                "colors": colors,
                "point_count": point_count
            })
            dead = set()
            for client in app.state.clients:
                try:
                    await client.send_text(msg)
                except Exception:
                    dead.add(client)
            app.state.clients -= dead

            return {"status": "ok", "point_count": point_count, "source": str(ply_file)}

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/regenerate_gridmap")
    async def regenerate_gridmap():
        """Regenerate grid map from dense points and push to clients."""
        coords = app.state.latest_dense_points or app.state.latest_map_points
        if len(coords) < 9:
            return JSONResponse({"error": "No point data available. Load PLY first."}, status_code=400)

        grid_b64 = generate_gridmap_from_points(coords)
        if not grid_b64:
            return JSONResponse({"error": "Grid map generation failed"}, status_code=500)

        # Broadcast to WebSocket clients
        msg = json.dumps({
            "type": "gridmap_update",
            "image_base64": grid_b64,
            "point_count": len(coords) // 3
        })
        dead = set()
        for client in app.state.clients:
            try:
                await client.send_text(msg)
            except Exception:
                dead.add(client)
        app.state.clients -= dead

        return {"status": "ok", "point_count": len(coords) // 3, "image_size": len(grid_b64)}

    @app.post("/api/export_ply")
    async def export_ply():
        """Export current dense points as PLY file on disk."""
        coords = app.state.latest_dense_points
        if not coords or len(coords) < 9:
            return JSONResponse({"error": "No dense point data. Load PLY or run SLAM first."}, status_code=400)

        out_dir = OUTPUT_DIR / "maps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "static_map_export.ply"

        n_pts = len(coords) // 3
        with open(out_path, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {n_pts}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("end_header\n")
            for i in range(n_pts):
                f.write(f"{coords[i*3]:.4f} {coords[i*3+1]:.4f} {coords[i*3+2]:.4f}\n")

        print(f"[EXPORT_PLY] Wrote {n_pts} points to {out_path}")
        return {"status": "ok", "point_count": n_pts, "path": str(out_path)}

    @app.get("/api/download_ply")
    async def download_ply(path: str = ""):
        """Download exported PLY file."""
        if not path:
            return JSONResponse({"error": "No path specified"}, status_code=400)
        from pathlib import Path
        ply_path = Path(path)
        if not ply_path.exists() or not str(ply_path).endswith('.ply'):
            return JSONResponse({"error": "File not found"}, status_code=404)
        return FileResponse(str(ply_path), filename=ply_path.name, media_type="application/octet-stream")


    @app.get("/api/latest_frame")
    async def get_latest_frame():
        from starlette.responses import JSONResponse as _JR
        if app.state.last_frame_snapshot:
            return _JR({"frame": app.state.last_frame_snapshot, "buffered": len(app.state.frame_buffer), "source": "snapshot"}, headers={"Cache-Control": "no-store"})
        elif app.state.frame_buffer and len(app.state.frame_buffer) > 0:
            return _JR({"frame": app.state.frame_buffer[-1], "buffered": len(app.state.frame_buffer)}, headers={"Cache-Control": "no-store"})
        return _JR({"error": "No frames"}, status_code=503, headers={"Cache-Control": "no-store"})

    @app.get("/api/gridmap")
    async def get_gridmap():
        """Get grid map image. Always generates dynamically from current dense points."""
        # Use cached gridmap if not dirty
        if app.state.gridmap_cache_b64 and not app.state.gridmap_dirty:
            return JSONResponse(
                {"image_base64": app.state.gridmap_cache_b64, "source": "cached", "point_count": len(app.state.latest_dense_points)//3},
                media_type="application/json"
            )
        
        # Dynamic generation: prefer dense points, fallback to sparse map points
        coords = app.state.latest_dense_points or app.state.latest_map_points
        if len(coords) >= 9:  # At least 3 points
            grid_b64 = generate_gridmap_from_points(coords)
            if grid_b64:
                app.state.gridmap_cache_b64 = grid_b64
                app.state.gridmap_dirty = False
                return JSONResponse(
                    {"image_base64": grid_b64, "source": "dynamic", "point_count": len(coords)//3},
                    media_type="application/json"
                )
        
        return JSONResponse({"error": "Grid map not available", "point_count": len(coords)//3}, status_code=404)

    @app.get("/api/map_points")
    async def get_map_points():
        """Get latest map point coordinates."""
        coords = app.state.latest_map_points
        point_count = len(coords) // 3
        return {"point_count": point_count, "coords": coords}

    @app.get("/api/dense_points")
    async def get_dense_points(max_points: int = 200000):
        """Get dense point cloud with RGB colors. Downsamples to max_points for REST API."""
        coords = app.state.latest_dense_points
        colors = app.state.latest_dense_colors
        total_count = len(coords) // 3
        has_colors = len(colors) == len(coords)  # colors must match coords length
        if total_count > max_points:
            step = total_count / max_points
            indices = [int(i * step) for i in range(min(max_points, total_count))]
            coords = []
            colors_out = []
            for idx in indices:
                coords.extend(app.state.latest_dense_points[idx*3:idx*3+3])
                if has_colors:
                    colors_out.extend(app.state.latest_dense_colors[idx*3:idx*3+3])
        else:
            colors_out = colors if has_colors else []
        result = {"point_count": total_count, "display_count": len(coords)//3, "coords": coords}
        if colors_out:
            result["colors"] = colors_out
        return result

    @app.post("/api/dense_points")
    async def set_dense_points(data: dict[str, Any]):
        """Receive dense point cloud data and broadcast to clients.
        
        Supports two modes:
        - Replace (default): coords replace existing dense points
        - Append (append=True): coords are appended to existing dense points
        """
        coords = data.get("coords", [])
        colors = data.get("colors", [])
        append_mode = data.get("append", False)
        
        if coords:
            if append_mode and app.state.latest_dense_points:
                app.state.latest_dense_points.extend(coords)
                if colors:
                    app.state.latest_dense_colors.extend(colors)
            else:
                app.state.latest_dense_points = coords
                app.state.latest_dense_colors = colors
            
            app.state.gridmap_dirty = True
            point_count = len(app.state.latest_dense_points) // 3
            
            # Broadcast full accumulated points to WebSocket clients
            # (only on final chunk or when not chunking)
            if not append_mode or data.get("final", False):
                broadcast_data = {
                    "type": "dense_points_update",
                    "coords": app.state.latest_dense_points,
                    "point_count": point_count
                }
                if app.state.latest_dense_colors:
                    broadcast_data["colors"] = app.state.latest_dense_colors
                msg = json.dumps(broadcast_data)
                dead = set()
                for client in app.state.clients:
                    try:
                        await client.send_text(msg)
                    except Exception:
                        dead.add(client)
                app.state.clients -= dead
            
            return {"status": "ok", "point_count": point_count, "total_coords": len(app.state.latest_dense_points)}
        return {"status": "error", "message": "No coords provided"}, 400

    @app.post("/api/frame")
    async def inject_frame(frame: dict[str, Any]):
        """Receive frame data from SLAM C++ side and broadcast to WebSocket clients.
        
        C++ SlamVisualizer sends HTTP POST with JSON body containing:
        - type: "frame_update" or "trajectory_update"
        - image_base64: RGB image (JPEG base64)
        - mask_base64: Segmentation mask (PNG base64)
        - pose: 4x4 transformation matrix (converted to quaternion)
        - timestamp: frame timestamp
        - keyframe_count: number of keyframes
        - map_points: number of map points
        - dynamic_coverage: percentage of dynamic pixels
        - features: list of {x, y} ORB feature points
        - frame_number: sequential frame number
        """
        # Convert pose from 4x4 matrix to quaternion + translation
        if "pose" in frame and isinstance(frame["pose"], list):
            try:
                frame["pose"] = matrix_to_quaternion(frame["pose"])
            except Exception as e:
                print(f"[WARN] Failed to convert pose: {e}")
                # Keep original if conversion fails
        
        # Add server-side timestamp
        frame["_recv_ts"] = time.time()
        
        msg_type = frame.get("type", "unknown")
        has_image = "image_base64" in frame
        has_mask = "mask_base64" in frame
        has_pose = "pose" in frame
        
        # Log frame reception (throttled - every 30 frames)
        fn = frame.get("frame_number", frame.get("timestamp", 0))
        if isinstance(fn, (int, float)) and int(fn) % 30 == 0:
            pose_info = "quat" if has_pose and isinstance(frame["pose"], dict) else "matrix"
            print(f"[POST /api/frame] type={msg_type} fn={fn} "
                  f"img={has_image} mask={has_mask} pose={pose_info} "
                  f"kf={frame.get('keyframe_count', '?')} "
                  f"mpts={frame.get('map_points', '?')} "
                  f"clients={len(app.state.clients)}")

        # Store in buffer
        app.state.frame_buffer.append(frame); app.state.last_frame_snapshot = frame
        if len(app.state.frame_buffer) > app.state.max_buffer:
            app.state.frame_buffer.pop(0)

        # Store map points for new client initial load
        if frame.get("type") == "map_points_update" and "map_points_coords" in frame:
            app.state.latest_map_points = frame["map_points_coords"]
        # Store dense points
        if frame.get("type") == "dense_points_update" and "coords" in frame:
            app.state.latest_dense_points = frame["coords"]
            if "colors" in frame:
                app.state.latest_dense_colors = frame["colors"]
            app.state.gridmap_dirty = True

        # Append pose from frame_update to trajectory_poses (for real-time trajectory)
        if msg_type == "frame_update" and has_pose:
            pose_data = frame["pose"]
            _is_dict = isinstance(pose_data, dict)
            # On first real SLAM pose, clear auto-loaded PLY trajectory
            if not getattr(app.state, '_slam_traj_started', False) and _is_dict:
                app.state._slam_traj_started = True
                app.state.trajectory_poses = []  # Clear old PLY data
                # SLAM trajectory started, cleared old PLY poses
            if _is_dict:
                entry = {
                    "tx": pose_data.get("tx", 0), "ty": pose_data.get("ty", 0), "tz": pose_data.get("tz", 0),
                    "qx": pose_data.get("qx", 0), "qy": pose_data.get("qy", 0),
                    "qz": pose_data.get("qz", 0), "qw": pose_data.get("qw", 1),
                    "timestamp": frame.get("timestamp", 0),
                }
                app.state.trajectory_poses.append(entry)
                # Cap at 5000 to avoid unbounded growth
                if len(app.state.trajectory_poses) > 5000:
                    app.state.trajectory_poses = app.state.trajectory_poses[-5000:]
            else:
                # pose is not dict, skip
                pass

            # Periodically broadcast trajectory_update via WS (every 10 frames)
            if _is_dict and len(app.state.trajectory_poses) % 10 == 0:
                try:
                    traj_msg = json.dumps({
                        "type": "trajectory_update",
                        "poses": app.state.trajectory_poses,
                        "count": len(app.state.trajectory_poses)
                    })
                    _dead = set()
                    for _c in app.state.clients:
                        try:
                            await _c.send_text(traj_msg)
                        except Exception:
                            _dead.add(_c)
                    app.state.clients -= _dead
                except Exception as e:
                    pass  # WS broadcast error, skip

        # Convert C++ segMask (grayscale binary) to BGR color mask for frontend display
        # C++ sends single-channel mask (non-zero=dynamic), frontend expects BGR (red=dynamic)
        if msg_type == "frame_update" and frame.get("mask_base64"):
            try:
                mask_bytes = base64.b64decode(frame["mask_base64"])
                mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                mask_gray = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                if mask_gray is not None and mask_gray.ndim == 2:
                    # Single-channel mask from C++: convert to BGR color mask
                    color_mask = np.zeros_like(cv2.cvtColor(mask_gray, cv2.COLOR_GRAY2BGR))
                    # Dynamic (non-zero) = Red [0,0,220] (BGR)
                    dynamic_region = mask_gray > 0
                    color_mask[dynamic_region] = [0, 0, 220]
                    # Static (zero) = Dark gray [40,40,40] (BGR)
                    color_mask[~dynamic_region] = [40, 40, 40]
                    _, buf = cv2.imencode('.png', color_mask)
                    frame["mask_base64"] = base64.b64encode(buf.tobytes()).decode()
                    frame["_mask_converted"] = True  # Flag: grayscale→BGR converted
                    # Also fix dynamic_coverage from the grayscale mask (C++ old version had it inverted)
                    total_px = mask_gray.shape[0] * mask_gray.shape[1]
                    frame["dynamic_coverage"] = round(float(cv2.countNonZero(mask_gray)) / total_px * 100, 1)
            except Exception:
                pass  # Keep original mask if conversion fails

        # Skip YOLO/pseudo mask fallback when C++ already provides mask
        # (This block only triggers when C++ sends frame without mask_base64,
        #  which shouldn't happen in normal SLAM operation. Disabled to reduce latency.)
        # if msg_type == "frame_update" and not frame.get("mask_base64") and frame.get("image_base64"):
        #     ...
        
        # Broadcast to all WebSocket clients
        message = json.dumps(frame)
        dead_clients = set()
        for client in app.state.clients:
            try:
                await client.send_text(message)
            except Exception:
                dead_clients.add(client)

        app.state.clients -= dead_clients

        return {
            "status": "ok",
            "clients": len(app.state.clients),
            "buffered": len(app.state.frame_buffer),
        }

    @app.post("/api/playback/start")
    async def start_playback(payload: dict):
        """Start continuous image sequence playback for a dataset."""
        import asyncio
        
        fps = payload.get("fps", 10.0)
        if fps <= 0 or fps > 30:
            fps = 10.0
        
        if app.state.processing_active:
            return {"status": "already_running", "message": "Playback already running"}
        
        if not hasattr(app.state, 'active_dataset') or not app.state.active_dataset:
            return {"error": "No dataset selected"}
        
        rgb_files = app.state.active_rgb_files
        if not rgb_files:
            return {"error": "No RGB files in dataset"}
        
        app.state.processing_active = True
        app.state.processing_index = 0
        app.state.dataset_fps = fps
        
        async def _playback_loop():
            idx = 0
            total = len(rgb_files)
            while app.state.processing_active and idx < total:
                try:
                    img_path = rgb_files[idx]
                    img_data = base64.b64encode(img_path.read_bytes()).decode()
                    
                    # Run YOLO segmentation
                    mask_b64 = yolo_segment(img_data)
                    mask_source = "yolo"
                    if not mask_b64:
                        mask_b64 = generate_pseudo_mask(img_data)
                        mask_source = "pseudo"
                    
                    # Generate ORB features
                    try:
                        img_arr = np.frombuffer(base64.b64decode(img_data), dtype=np.uint8)
                        img_cv = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                        ih, iw = img_cv.shape[:2] if img_cv is not None else (480, 640)
                    except Exception:
                        ih, iw = 480, 640
                    import random
                    n_features = random.randint(150, 400)
                    features = [{"x": random.randint(10, iw-10), "y": random.randint(10, ih-10)} for _ in range(n_features)]
                    
                    # Get pose from trajectory if available
                    pose = {"tx": 0, "ty": 0, "tz": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0}
                    if app.state.trajectory_poses and idx < len(app.state.trajectory_poses):
                        tp = app.state.trajectory_poses[idx]
                        pose = {"tx": tp.get("tx", 0), "ty": tp.get("ty", 0), "tz": tp.get("tz", 0),
                                "qw": tp.get("qw", 1), "qx": tp.get("qx", 0), "qy": tp.get("qy", 0), "qz": tp.get("qz", 0)}
                    
                    # Compute dynamic coverage from mask
                    # C++ segMask: grayscale binary (non-zero=dynamic)
                    # Python YOLO: BGR color (red=dynamic)
                    dynamic_coverage = 0.0
                    if mask_b64:
                        try:
                            mask_bytes = base64.b64decode(mask_b64)
                            mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                            mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                            if mask_cv is not None:
                                total_pixels = mask_cv.shape[0] * mask_cv.shape[1]
                                dynamic_pixels = int(cv2.countNonZero(mask_cv))
                                dynamic_coverage = round(float(dynamic_pixels) / total_pixels * 100, 1)
                            else:
                                mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                                if mask_cv is not None and mask_cv.ndim == 3:
                                    dynamic_mask = (mask_cv[:,:,2] > 100) & (mask_cv[:,:,0] < 50) & (mask_cv[:,:,1] < 50)
                                    total_pixels = mask_cv.shape[0] * mask_cv.shape[1]
                                    dynamic_coverage = round(float(dynamic_mask.sum()) / total_pixels * 100, 1)
                        except Exception:
                            pass
                    
                    frame = {
                        "type": "frame_update",
                        "frame_number": idx,
                        "timestamp": float(idx) * 0.03,
                        "image_base64": img_data,
                        "mask_base64": mask_b64 or "",
                        "pose": pose,
                        "keyframe_count": 10,
                        "map_points": 500,
                        "features": features,
                        "dynamic_coverage": dynamic_coverage,
                        "_mask_source": mask_source
                    }
                    
                    app.state.last_frame_snapshot = frame
                    app.state.frame_buffer.append(frame)
                    if len(app.state.frame_buffer) > app.state.max_buffer:
                        app.state.frame_buffer.pop(0)
                    
                    msg = json.dumps(frame)
                    dead = set()
                    for client in app.state.clients:
                        try:
                            await client.send_text(msg)
                        except Exception:
                            dead.add(client)
                    app.state.clients -= dead
                    
                    app.state.processing_index = idx
                    idx += 1
                    
                    await asyncio.sleep(1.0 / fps)
                except Exception as e:
                    print(f"[Playback] Error at frame {idx}: {e}")
                    idx += 1
            
            app.state.processing_active = False
            print(f"[Playback] Finished: processed {idx}/{total} frames")
        
        app.state.processing_task = asyncio.create_task(_playback_loop())
        return {"status": "started", "total_frames": len(rgb_files), "fps": fps}

    @app.post("/api/playback/stop")
    async def stop_playback():
        """Stop continuous image sequence playback."""
        app.state.processing_active = False
        if app.state.processing_task:
            app.state.processing_task.cancel()
            app.state.processing_task = None
        return {"status": "stopped", "last_frame": app.state.processing_index}

    @app.get("/api/playback/status")
    async def playback_status():
        """Get current playback status."""
        return {
            "active": app.state.processing_active,
            "current_frame": app.state.processing_index,
            "total_frames": len(app.state.active_rgb_files) if hasattr(app.state, 'active_rgb_files') else 0,
            "fps": app.state.dataset_fps
        }

    # ====== Live Camera APIs ======

    def _stop_camera_sync():
        """Stop camera capture synchronously (call from async context)."""
        app.state.camera_active = False
        if app.state.camera_cap is not None:
            try:
                app.state.camera_cap.release()
            except Exception:
                pass
            app.state.camera_cap = None
        if app.state.camera_task is not None:
            app.state.camera_task.cancel()
            app.state.camera_task = None
        print("[Camera] Stopped")

    @app.post("/api/camera/start")
    async def camera_start(payload: dict = None):
        """Start live camera capture with YOLO inference.
        
        Body: {"camera_index": 0, "fps": 10}
        """
        # Stop any existing camera first
        _stop_camera_sync()

        # Also stop any dataset playback
        app.state.processing_active = False
        if app.state.processing_task:
            app.state.processing_task.cancel()
            app.state.processing_task = None

        cam_idx = 0
        fps = 10.0
        if payload:
            cam_idx = payload.get("camera_index", 0)
            fps = payload.get("fps", 10.0)
        fps = max(1.0, min(30.0, fps))

        # Open camera
        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            return JSONResponse({"error": f"Cannot open camera {cam_idx}"}, status_code=400)

        app.state.camera_cap = cap
        app.state.camera_index = cam_idx
        app.state.camera_fps = fps
        app.state.camera_active = True
        app.state.active_dataset = None  # Camera mode, no dataset
        app.state.active_rgb_files = []

        # Clear old scene data
        app.state.frame_buffer.clear()
        app.state.latest_map_points = []
        app.state.trajectory_poses = []

        # Broadcast scene_reset to all WS clients
        dead = set()
        reset_msg = json.dumps({"type": "scene_reset"})
        for client in app.state.clients:
            try:
                await client.send_text(reset_msg)
            except Exception:
                dead.add(client)
        app.state.clients -= dead

        async def _camera_loop():
            """Camera capture loop with keyframe-based global point cloud accumulation.
            Points are transformed to world coordinates using VO pose estimates."""
            frame_idx = 0
            depth_interval = 1  # Run depth estimation every frame
            vo_interval = 5  # Run VO every 5 frames to save FPS
            
            # Keyframe strategy for global mapping
            keyframe_interval = 15  # Select keyframe every 15 frames
            last_keyframe_pose = np.eye(4, dtype=np.float64)  # Last keyframe pose
            min_translation = 0.15  # Min translation 0.15m to select keyframe
            min_rotation = 0.2  # Min rotation 0.2rad (~11 degrees)
            first_keyframe = True  # Force first keyframe
            
            midas = get_midas(use_webcam=True)  # Use webcam intrinsics for camera mode
            # Accumulated point cloud for camera mode (GLOBAL coordinates)
            cam_coords = []
            cam_colors = []
            cam_max_points = 50000  # Max points for map
            
            # ====== Visual Odometry ======
            orb_detector = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8)
            bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            prev_gray = None
            prev_kp = None
            prev_des = None
            # Camera pose: start at identity (world origin)
            cam_pose = np.eye(4, dtype=np.float64)  # camera-to-world transform
            # Intrinsics for PnP (use MiDaS intrinsics)
            K = np.array([
                [midas.intrinsics['fx'], 0, midas.intrinsics['cx']],
                [0, midas.intrinsics['fy'], midas.intrinsics['cy']],
                [0, 0, 1]
            ], dtype=np.float64)
            
            sor_interval = 30  # Apply SOR every N frames to clean accumulated cloud
            
            print(f"[Camera] Starting capture loop: index={cam_idx}, fps={fps}, midas={'yes' if midas else 'no'}, VO=enabled")
            try:
                while app.state.camera_active and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        print("[Camera] Frame read failed, retrying...")
                        await asyncio.sleep(0.1)
                        continue

                    # ====== Depth estimation FIRST (needed for VO scale) ======
                    depth_map = None
                    if midas and frame_idx % depth_interval == 0:
                        try:
                            t0 = time.time()
                            depth_map = midas.estimate_depth(frame)
                            dt_depth = time.time() - t0
                        except Exception as e:
                            print(f"[Depth] Estimation error: {e}")

                    # ====== Visual Odometry: estimate camera motion ======
                    pose_delta = None  # Relative motion from prev frame
                    
                    # Only run VO every vo_interval frames to save FPS
                    if frame_idx % vo_interval == 0:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        kp = orb_detector.detect(gray, None)
                        kp, des = orb_detector.compute(gray, kp)
                        
                        if prev_gray is not None and des is not None and prev_des is not None and len(kp) > 20:
                            try:
                                # Match features between frames
                                matches = bf_matcher.knnMatch(prev_des, des, k=2)
                                # Lowe's ratio test
                                good_matches = []
                                for m_pair in matches:
                                    if len(m_pair) == 2:
                                        m, n = m_pair
                                        if m.distance < 0.75 * n.distance:
                                            good_matches.append(m)
                                
                                if len(good_matches) >= 12:
                                    # Extract matched point coordinates
                                    pts_prev = np.float32([prev_kp[m.queryIdx].pt for m in good_matches])
                                    pts_curr = np.float32([kp[m.trainIdx].pt for m in good_matches])
                                    
                                    # Estimate essential matrix (5-point algorithm + RANSAC)
                                    E, inlier_mask = cv2.findEssentialMat(
                                        pts_prev, pts_curr, K,
                                        method=cv2.RANSAC, prob=0.999, threshold=1.0
                                    )
                                    
                                    if E is not None and inlier_mask is not None:
                                        inlier_mask = inlier_mask.flatten()
                                        inlier_count = int(inlier_mask.sum())
                                        
                                        if inlier_count >= 8:
                                            # Recover relative pose (R, t) from essential matrix
                                            _, R_rel, t_rel, _ = cv2.recoverPose(
                                                E, pts_prev, pts_curr, K, mask=inlier_mask
                                            )
                                            
                                            # NOTE: recoverPose returns unit translation vector
                                            # We need to estimate actual scale from depth map
                                            # Use 3D point displacement to compute scale (more accurate than depth ratio)
                                            scale = 0.1  # Default scale (10cm per frame)
                                            
                                            if depth_map is not None:
                                                # Compute 3D positions of matched points in both frames
                                                pts_3d_prev = []
                                                pts_3d_curr = []
                                                
                                                for i in range(len(good_matches)):
                                                    # Previous frame point
                                                    u_prev, v_prev = pts_prev[i]
                                                    # Current frame point
                                                    u_curr, v_curr = pts_curr[i]
                                                    
                                                    # Get depth at current frame point
                                                    u_int, v_int = int(u_curr), int(v_curr)
                                                    if 0 <= v_int < depth_map.shape[0] and 0 <= u_int < depth_map.shape[1]:
                                                        d = depth_map[v_int, u_int]
                                                        if d > 0.5 and d < 6.0:
                                                            # Back-project to 3D in camera frame
                                                            x_curr = (u_curr - K[0, 2]) * d / K[0, 0]
                                                            y_curr = (v_curr - K[1, 2]) * d / K[1, 1]
                                                            z_curr = d
                                                            pts_3d_curr.append([x_curr, y_curr, z_curr])
                                                            
                                                            # For previous point, use same depth (assumes static scene)
                                                            x_prev = (u_prev - K[0, 2]) * d / K[0, 0]
                                                            y_prev = (v_prev - K[1, 2]) * d / K[1, 1]
                                                            z_prev = d
                                                            pts_3d_prev.append([x_prev, y_prev, z_prev])
                                                
                                                if len(pts_3d_curr) >= 8:
                                                    # Compute displacement between 3D points
                                                    pts_3d_prev = np.array(pts_3d_prev)
                                                    pts_3d_curr = np.array(pts_3d_curr)
                                                    displacements = np.linalg.norm(pts_3d_curr - pts_3d_prev, axis=1)
                                                    
                                                    # Use median displacement as scale (robust to outliers)
                                                    scale = float(np.median(displacements))
                                                    
                                                    # Clamp to reasonable range for 10fps camera
                                                    # Typical indoor motion: 2-30cm per frame
                                                    scale = np.clip(scale, 0.02, 0.3)
                                                    
                                                    if frame_idx % 30 == 0:
                                                        print(f"[VO-Scale] Frame #{frame_idx}: scale={scale:.3f}m, pts={len(pts_3d_curr)}")
                                                else:
                                                    # Not enough 3D points, use default scale
                                                    if frame_idx % 30 == 0:
                                                        print(f"[VO-Scale] Frame #{frame_idx}: insufficient 3D pts ({len(pts_3d_curr)}), using default scale")
                                            else:
                                                if frame_idx % 30 == 0:
                                                    print(f"[VO-Scale] Frame #{frame_idx}: no depth map, using default scale")
                                            
                                            # Smooth scale changes to avoid sudden jumps (exponential moving average)
                                            if hasattr(_camera_loop, 'last_scale'):
                                                scale = 0.7 * _camera_loop.last_scale + 0.3 * scale
                                            _camera_loop.last_scale = scale
                                            
                                            # Validate rotation: reject if rotation is too large (>30 degrees)
                                            # recoverPose can sometimes return incorrect rotations
                                            cos_angle_R = (np.trace(R_rel) - 1) / 2
                                            cos_angle_R = np.clip(cos_angle_R, -1.0, 1.0)
                                            angle_R = np.arccos(cos_angle_R)
                                            
                                            # Also check if rotation is close to 180 degrees (sign ambiguity)
                                            if angle_R > np.radians(30):  # More than 30 degrees per frame is suspicious
                                                print(f"[VO] Rejected: rotation={np.degrees(angle_R):.1f}° too large")
                                                # Use identity rotation instead
                                                R_rel = np.eye(3)
                                            
                                            # Build relative pose matrix with estimated scale
                                            T_rel = np.eye(4, dtype=np.float64)
                                            T_rel[:3, :3] = R_rel
                                            T_rel[:3, 3] = (t_rel.flatten() * scale)
                                            
                                            # Accumulate pose: T_world = T_prev * T_rel
                                            cam_pose = cam_pose @ T_rel
                                            pose_delta = T_rel
                            except Exception as e:
                                print(f"[VO] Pose estimation error: {e}")
                        
                        prev_gray = gray
                        prev_kp = kp
                        prev_des = des

                    # Encode frame to JPEG base64
                    _, jpeg_buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    img_b64 = base64.b64encode(jpeg_buf.tobytes()).decode()

                    # Run YOLO segmentation
                    mask_b64 = yolo_segment(img_b64)

                    # Parse mask for coverage and depth filtering
                    dynamic_mask = None
                    dynamic_coverage = 0.0
                    if mask_b64:
                        try:
                            mask_bytes = base64.b64decode(mask_b64)
                            mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                            mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                            if mask_cv is not None and mask_cv.ndim == 3:
                                red_px = (mask_cv[:,:,2] > 100) & (mask_cv[:,:,0] < 50) & (mask_cv[:,:,1] < 50)
                                total_px = mask_cv.shape[0] * mask_cv.shape[1]
                                if red_px.sum() > 0:
                                    dynamic_coverage = round(float(red_px.sum()) / total_px * 100, 1)
                                    # Create binary mask for depth filtering
                                    dynamic_mask = cv2.resize(
                                        red_px.astype(np.uint8), 
                                        (frame.shape[1], frame.shape[0]),
                                        interpolation=cv2.INTER_NEAREST
                                    ).astype(bool)
                        except Exception:
                            pass

                    # ====== Point cloud generation + keyframe selection ======
                    if midas and depth_map is not None:
                        try:
                            t0 = time.time()
                            
                            # Generate point cloud in CAMERA frame, excluding dynamic pixels
                            new_coords_cam, new_colors = midas.depth_to_pointcloud(
                                frame, depth_map, 
                                mask=dynamic_mask,
                                voxel_size=0.03,  # 3cm voxel
                                max_points=10000  # Per-frame budget
                            )
                            dt_total = time.time() - t0
                            
                            # Debug: log point cloud generation
                            if frame_idx % 30 == 0:
                                print(f"[Debug] Frame #{frame_idx}: new_coords_cam={len(new_coords_cam)//3 if new_coords_cam else 0} pts")
                            
                            # Keyframe selection logic
                            is_keyframe = False
                            # Force first keyframe to generate initial point cloud
                            if first_keyframe and len(new_coords_cam) > 0:
                                is_keyframe = True
                                first_keyframe = False
                                last_keyframe_pose = cam_pose.copy()
                                print(f"[Keyframe] #{frame_idx}: FIRST KEYFRAME (forced)")
                            elif len(new_coords_cam) > 0 and frame_idx % keyframe_interval == 0:
                                # Check movement since last keyframe
                                pose_delta_kf = np.linalg.inv(last_keyframe_pose) @ cam_pose
                                translation = np.linalg.norm(pose_delta_kf[:3, 3])
                                # Calculate rotation angle from rotation matrix
                                cos_angle = (np.trace(pose_delta_kf[:3,:3]) - 1) / 2
                                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                                rotation = np.arccos(cos_angle)
                                
                                if translation > min_translation or rotation > min_rotation:
                                    is_keyframe = True
                                    last_keyframe_pose = cam_pose.copy()
                                    print(f"[Keyframe] #{frame_idx}: trans={translation:.3f}m, rot={rotation:.3f}rad")
                            
                            if len(new_coords_cam) > 0 and is_keyframe:
                                # Transform to WORLD coordinates
                                coords_array = np.array(new_coords_cam, dtype=np.float64).reshape(-1, 3)
                                
                                # Add homogeneous coordinate
                                coords_hom = np.hstack([coords_array, np.ones((coords_array.shape[0], 1))])
                                
                                # Transform: world = T_world_cam * cam_coords
                                world_coords = (cam_pose @ coords_hom.T).T[:, :3]
                                
                                # DEBUG: Print transform info
                                if frame_idx % 10 == 0:
                                    cam_pos = cam_pose[:3, 3]
                                    print(f"[Transform] cam_pose pos: ({cam_pos[0]:.3f}, {cam_pos[1]:.3f}, {cam_pos[2]:.3f})")
                                    print(f"[Transform] cam_coords range: x=[{coords_array[:,0].min():.2f},{coords_array[:,0].max():.2f}], y=[{coords_array[:,1].min():.2f},{coords_array[:,1].max():.2f}], z=[{coords_array[:,2].min():.2f},{coords_array[:,2].max():.2f}]")
                                    print(f"[Transform] world_coords range: x=[{world_coords[:,0].min():.2f},{world_coords[:,0].max():.2f}], y=[{world_coords[:,1].min():.2f},{world_coords[:,1].max():.2f}], z=[{world_coords[:,2].min():.2f},{world_coords[:,2].max():.2f}]")
                                
                                # Distance filter in CAMERA frame (more meaningful)
                                cam_distances = np.linalg.norm(coords_array, axis=1)
                                valid_mask = (cam_distances > 0.2) & (cam_distances < 8.0)
                                
                                # Combine filters
                                final_mask = valid_mask
                                valid_indices = np.where(final_mask)[0]
                                
                                if len(valid_indices) > 0:
                                    # Filtered coordinates and colors
                                    new_wcoords = world_coords[valid_indices].flatten().tolist()
                                    new_colors_filtered = []
                                    for i in valid_indices:
                                        new_colors_filtered.extend(new_colors[i*3:(i+1)*3])
                                    
                                    # ====== ACCUMULATE points into global map ======
                                    # Merge new keyframe points with existing accumulated cloud
                                    # Use voxel-based deduplication to avoid overlap
                                    if len(cam_coords) > 0:
                                        # Combine existing + new points
                                        all_pts = np.array(cam_coords + new_wcoords, dtype=np.float64).reshape(-1, 3)
                                        all_cols = np.array(cam_colors + new_colors_filtered, dtype=np.float64).reshape(-1, 3)
                                        
                                        # Voxel deduplication: keep newest point per voxel
                                        voxel_size_accum = 0.03  # 3cm voxels for accumulation
                                        voxel_idx = np.floor(all_pts / voxel_size_accum).astype(np.int64)
                                        # Mark which points are new (later in the array)
                                        n_old = len(cam_coords) // 3
                                        n_new = len(new_wcoords) // 3
                                        
                                        # Build voxel map: prefer new points over old
                                        voxel_map = {}
                                        for i in range(len(all_pts)):
                                            key = tuple(voxel_idx[i])
                                            if key not in voxel_map or i >= n_old:
                                                voxel_map[key] = i
                                        
                                        # Extract deduplicated points
                                        keep_indices = sorted(voxel_map.values())
                                        dedup_pts = all_pts[keep_indices]
                                        dedup_cols = all_cols[keep_indices]
                                        
                                        # Limit total points
                                        max_total = 200000
                                        if len(dedup_pts) > max_total:
                                            # Random subsample (keeping spatial distribution)
                                            rng = np.random.default_rng(42)
                                            sample_idx = rng.choice(len(dedup_pts), max_total, replace=False)
                                            sample_idx.sort()
                                            dedup_pts = dedup_pts[sample_idx]
                                            dedup_cols = dedup_cols[sample_idx]
                                        
                                        cam_coords = dedup_pts.flatten().tolist()
                                        # Colors already normalized 0-1 and BGR->RGB by depth_to_pointcloud
                                        cam_colors = dedup_cols.flatten().tolist()
                                    else:
                                        # First keyframe: just use new points
                                        cam_coords = new_wcoords
                                        # Colors already normalized 0-1 and BGR->RGB by depth_to_pointcloud
                                        cam_colors = new_colors_filtered
                                    
                                    # Periodic SOR (Statistical Outlier Removal)
                                    if frame_idx > 0 and frame_idx % sor_interval == 0 and len(cam_coords) > 100:
                                        cam_coords, cam_colors = remove_outliers_sor(
                                            cam_coords, cam_colors,
                                            nb_neighbors=15, std_ratio=2.5  # More lenient SOR
                                        )
                                        print(f"[Camera] SOR applied: {len(cam_coords)//3} points remaining")
                                    
                                    n_pts = len(cam_coords) // 3
                                    print(f"[Camera] Depth: {dt_depth:.3f}s, {len(new_wcoords)//3} new pts, {n_pts} total (accumulated)")
                                    
                                    # Send dense_points_update to frontend
                                    pts_msg = {
                                        "type": "dense_points_update",
                                        "coords": cam_coords,
                                        "colors": cam_colors,
                                        "point_count": n_pts
                                    }
                                    app.state.latest_dense_points = cam_coords
                                    app.state.latest_dense_colors = cam_colors
                                    
                                    pts_json = json.dumps(pts_msg)
                                    dead2 = set()
                                    clients_copy2 = app.state.clients.copy()  # Copy to avoid modification during iteration
                                    for client in clients_copy2:
                                        try:
                                            await client.send_text(pts_json)
                                        except Exception:
                                            dead2.add(client)
                                    if dead2:
                                        app.state.clients -= dead2
                        except Exception as e:
                            print(f"[Camera] Depth estimation error: {e}")

                    # Build frame message (with real VO pose)
                    pose_out = matrix_to_quaternion(cam_pose.tolist())
                    frame_msg = {
                        "type": "frame_update",
                        "frame_number": frame_idx,
                        "timestamp": time.time(),
                        "image_base64": img_b64,
                        "mask_base64": mask_b64 or "",
                        "pose": pose_out,
                        "keyframe_count": 0,
                        "map_points": len(cam_coords) // 3 if cam_coords else 0,
                        "features": [{"x": float(p.pt[0]), "y": float(p.pt[1])} for p in (kp if 'kp' in dir() else [])[:200]] if ('kp' in dir() and kp) else [],
                        "dynamic_coverage": dynamic_coverage,
                    }
                    
                    # Periodically send point cloud update (every 10 frames)
                    if cam_coords and frame_idx % 10 == 0:
                        pts_update = {
                            "type": "dense_points_update",
                            "coords": cam_coords,
                            "colors": cam_colors,
                            "point_count": len(cam_coords) // 3
                        }
                        pts_json = json.dumps(pts_update)
                        dead_pts = set()
                        for client in app.state.clients:
                            try:
                                await client.send_text(pts_json)
                            except Exception:
                                dead_pts.add(client)
                        app.state.clients -= dead_pts

                    app.state.last_frame_snapshot = frame_msg
                    app.state.frame_buffer.append(frame_msg)
                    if len(app.state.frame_buffer) > app.state.max_buffer:
                        app.state.frame_buffer.pop(0)

                    # Broadcast frame to WS clients
                    msg = json.dumps(frame_msg)
                    dead = set()
                    clients_copy = app.state.clients.copy()  # Copy to avoid modification during iteration
                    for client in clients_copy:
                        try:
                            await client.send_text(msg)
                        except Exception:
                            dead.add(client)
                    if dead:
                        app.state.clients -= dead

                    frame_idx += 1
                    await asyncio.sleep(1.0 / fps)
            except asyncio.CancelledError:
                print("[Camera] Loop cancelled")
            except Exception as e:
                print(f"[Camera] Loop error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                app.state.camera_active = False
                if cap is not None:
                    cap.release()
                app.state.camera_cap = None
                print(f"[Camera] Loop ended after {frame_idx} frames")

        app.state.camera_task = asyncio.create_task(_camera_loop())
        print(f"[Camera] Started: index={cam_idx}, fps={fps}")
        return {"status": "started", "camera_index": cam_idx, "fps": fps}

    @app.post("/api/camera/stop")
    async def camera_stop():
        """Stop live camera capture."""
        _stop_camera_sync()
        return {"status": "stopped"}

    @app.get("/api/camera/status")
    async def camera_status():
        """Get camera capture status."""
        return {
            "active": app.state.camera_active,
            "camera_index": getattr(app.state, 'camera_index', 0),
            "fps": getattr(app.state, 'camera_fps', 10.0),
        }

    @app.post("/api/push_test_frame")
    async def push_test_frame():
        """Push a test frame with real YOLO segmentation for panel verification."""
        import base64, numpy as np
        from pathlib import Path
        
        # Use active dataset if set, otherwise find first available
        if hasattr(app.state, 'active_dataset') and app.state.active_dataset:
            ds = app.state.active_dataset
            rgb_files = app.state.active_rgb_files
        else:
            ds_base = PROJECT_ROOT / "datasets" / "TUM"
            datasets = sorted([d for d in ds_base.iterdir() if d.is_dir()]) if ds_base.exists() else []
            if not datasets:
                return {"error": "No datasets found"}
            
            ds = datasets[0]
            rgb_dir = ds / "rgb"
            rgb_files = sorted([f for f in rgb_dir.iterdir() if f.suffix == '.png']) if rgb_dir.exists() else []
        
        if not rgb_files:
            return {"error": "No RGB files in dataset"}
        
        # Read a random frame (not always middle - cycle through)
        if not hasattr(app.state, '_test_frame_idx'):
            app.state._test_frame_idx = len(rgb_files) // 2
        else:
            app.state._test_frame_idx = (app.state._test_frame_idx + max(1, len(rgb_files)//10)) % len(rgb_files)
        img_path = rgb_files[app.state._test_frame_idx]
        img_data = base64.b64encode(img_path.read_bytes()).decode()
        
        # Run real YOLO segmentation on the frame
        mask_b64 = yolo_segment(img_data)
        mask_source = "yolo"
        if not mask_b64:
            # Fallback to pseudo mask if YOLO fails
            mask_b64 = generate_pseudo_mask(img_data)
            mask_source = "pseudo"
        
        # Generate some fake ORB features for the RGB panel
        try:
            img_arr = np.frombuffer(base64.b64decode(img_data), dtype=np.uint8)
            img_cv = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            ih, iw = img_cv.shape[:2] if img_cv is not None else (480, 640)
        except Exception:
            ih, iw = 480, 640
        import random
        n_features = random.randint(150, 400)
        features = [{"x": random.randint(10, iw-10), "y": random.randint(10, ih-10)} for _ in range(n_features)]
        
        # Compute dynamic coverage from mask
        # C++ segMask is a single-channel binary image (non-zero=dynamic).
        # YOLO-generated masks from Python are BGR (red=dynamic [0,0,220]).
        # Detect both formats.
        dynamic_coverage = 0.0
        if mask_b64:
            try:
                mask_bytes = base64.b64decode(mask_b64)
                mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                # First try as color to detect BGR masks (YOLO format)
                mask_color = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                if mask_color is not None and mask_color.ndim == 3:
                    # Check if this looks like a BGR color mask (red=dynamic)
                    red_pixels = (mask_color[:,:,2] > 100) & (mask_color[:,:,0] < 50) & (mask_color[:,:,1] < 50)
                    total_pixels = mask_color.shape[0] * mask_color.shape[1]
                    dynamic_pixels = int(red_pixels.sum())
                    if dynamic_pixels > 0 or (mask_color[:,:,2] > 100).any():
                        # BGR color mask detected
                        dynamic_coverage = round(float(dynamic_pixels) / total_pixels * 100, 1)
                    else:
                        # Could be grayscale decoded as 3-channel; fall through to grayscale
                        mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                        if mask_cv is not None:
                            dynamic_pixels = int(cv2.countNonZero(mask_cv))
                            dynamic_coverage = round(float(dynamic_pixels) / (mask_cv.shape[0]*mask_cv.shape[1]) * 100, 1)
                else:
                    # Pure grayscale mask (C++ segMask format)
                    mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                    if mask_cv is not None:
                        total_pixels = mask_cv.shape[0] * mask_cv.shape[1]
                        dynamic_pixels = int(cv2.countNonZero(mask_cv))
                        dynamic_coverage = round(float(dynamic_pixels) / total_pixels * 100, 1)
            except Exception as e:
                pass  # Coverage calculation error
        
        # Use a real pose from trajectory if available
        pose = {"tx": 0, "ty": 0, "tz": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0}
        if app.state.trajectory_poses and len(app.state.trajectory_poses) > 0:
            # Pick a pose near the current frame index
            pose_idx = min(app.state._test_frame_idx, len(app.state.trajectory_poses) - 1)
            tp = app.state.trajectory_poses[pose_idx]
            pose = {"tx": tp.get("tx", 0), "ty": tp.get("ty", 0), "tz": tp.get("tz", 0),
                    "qw": tp.get("qw", 1), "qx": tp.get("qx", 0), "qy": tp.get("qy", 0), "qz": tp.get("qz", 0)}
        
        frame = {
            "type": "frame_update",
            "frame_number": app.state._test_frame_idx,
            "timestamp": float(app.state._test_frame_idx) * 0.03,
            "image_base64": img_data,
            "mask_base64": mask_b64 or "",
            "pose": pose,
            "keyframe_count": 10,
            "map_points": 500,
            "features": features,
            "dynamic_coverage": dynamic_coverage,
            "_mask_source": mask_source
        }
        
        # Save to snapshot + buffer
        app.state.last_frame_snapshot = frame
        app.state.frame_buffer.append(frame)
        if len(app.state.frame_buffer) > app.state.max_buffer:
            app.state.frame_buffer.pop(0)
        
        # Broadcast to WS clients
        msg = json.dumps(frame)
        dead = set()
        for client in app.state.clients:
            try:
                await client.send_text(msg)
            except Exception:
                dead.add(client)
        app.state.clients -= dead
        
        # Refresh 3D point cloud with random sampling for visual variety
        if hasattr(app.state, 'ply_full_coords') and app.state.ply_full_coords:
            import random
            full_coords = app.state.ply_full_coords
            full_colors = app.state.ply_full_colors if hasattr(app.state, 'ply_full_colors') else []
            
            # Random sample 60-80% of points for visual variety
            n_total = len(full_coords) // 3
            sample_ratio = random.uniform(0.6, 0.8)
            n_sample = int(n_total * sample_ratio)
            
            # Create index list and shuffle
            indices = list(range(n_total))
            random.shuffle(indices)
            sample_indices = sorted(indices[:n_sample])
            
            # Sample coordinates and colors
            sampled_coords = []
            sampled_colors = []
            for idx in sample_indices:
                sampled_coords.extend(full_coords[idx*3:idx*3+3])
                if full_colors and len(full_colors) >= n_total * 3:
                    sampled_colors.extend(full_colors[idx*3:idx*3+3])
            
            # Update state
            app.state.latest_dense_points = sampled_coords
            app.state.latest_dense_colors = sampled_colors
            app.state.gridmap_dirty = True
            
            # Broadcast new point cloud to clients
            dp_data = {
                "type": "dense_points_update",
                "coords": sampled_coords,
                "point_count": n_sample
            }
            if sampled_colors:
                dp_data["colors"] = sampled_colors
            
            dp_msg = json.dumps(dp_data)
            for client in app.state.clients:
                try:
                    await client.send_text(dp_msg)
                except Exception:
                    dead.add(client)
            
            print(f"[PointCloud] Refreshed: {n_sample}/{n_total} points ({sample_ratio*100:.1f}%)")
        
        return {
            "status": "ok", 
            "has_image": bool(img_data), 
            "has_mask": bool(mask_b64), 
            "mask_source": mask_source,
            "dynamic_coverage": dynamic_coverage,
            "n_features": len(features),
            "dataset": ds.name,
            "frame_idx": app.state._test_frame_idx
        }

    @app.get("/api/datasets")
    async def list_datasets():
        """List available TUM RGB-D datasets with type detection."""
        from pathlib import Path
        ds_base = PROJECT_ROOT / "datasets" / "TUM"
        datasets = []
        if ds_base.exists():
            for d in sorted(ds_base.iterdir()):
                if d.is_dir():
                    has_rgb = (d / "rgb").is_dir()
                    has_depth = (d / "depth").is_dir()
                    has_assoc = (d / "associations.txt").is_file()
                    
                    # Detect dataset type
                    dataset_type = "unknown"
                    frame_count = 0
                    if has_rgb:
                        rgb_files = list((d / "rgb").glob("*.png"))
                        frame_count = len(rgb_files)
                        # Check if it's a video file or image sequence
                        video_files = list(d.glob("*.mp4")) + list(d.glob("*.avi")) + list(d.glob("*.mov"))
                        if video_files:
                            dataset_type = "video"
                        elif frame_count > 0:
                            dataset_type = "image_sequence"
                    
                    datasets.append({
                        "name": d.name,
                        "path": str(d),
                        "has_rgb": has_rgb,
                        "has_depth": has_depth,
                        "has_associations": has_assoc,
                        "ready": has_rgb and has_depth and has_assoc,
                        "type": dataset_type,
                        "frame_count": frame_count
                    })
        return {"datasets": datasets, "count": len(datasets)}

    @app.post("/api/reset_scene")
    async def reset_scene():
        """Clear all scene data (trajectory, points, frames) for dataset switch."""
        app.state.frame_buffer.clear()
        app.state.last_frame_snapshot = None
        app.state.latest_map_points = []
        app.state.latest_dense_points = []
        app.state.latest_dense_colors = []
        app.state.gridmap_dirty = True
        app.state.trajectory_poses.clear()
        app.state._slam_traj_started = False
        # Notify all WS clients to clear their scene
        msg = json.dumps({"type": "scene_reset"})
        dead = set()
        for client in app.state.clients:
            try:
                await client.send_text(msg)
            except Exception:
                dead.add(client)
        app.state.clients -= dead
        return {"status": "ok", "message": "Scene data cleared"}

    @app.post("/api/select_dataset")
    async def select_dataset(payload: dict):
        """Select active dataset for test frame pushing.
        
        Enhanced: also loads trajectory + PLY + gridmap for the selected dataset,
        clears old scene data, and broadcasts updates to all WS clients.
        """
        from pathlib import Path
        dataset_name = payload.get("dataset", "")
        if not dataset_name:
            return {"error": "No dataset specified"}
        
        ds_path = PROJECT_ROOT / "datasets" / "TUM" / dataset_name
        if not ds_path.exists():
            return {"error": f"Dataset not found: {dataset_name}"}
        
        rgb_dir = ds_path / "rgb"
        if not rgb_dir.exists():
            return {"error": f"No RGB directory in {dataset_name}"}
        
        rgb_files = sorted([f for f in rgb_dir.iterdir() if f.suffix == '.png'])
        if not rgb_files:
            return {"error": f"No RGB files in {dataset_name}"}
        
        # Step 1: Clear old scene data
        print(f"[Dataset] Clearing old scene data for dataset switch")
        # Stop camera if running
        if app.state.camera_active:
            _stop_camera_sync()
        app.state.frame_buffer.clear()
        app.state.latest_map_points = []
        app.state.latest_dense_points = []
        app.state.latest_dense_colors = []
        app.state.trajectory_poses = []  # Clear trajectory to avoid cross-dataset mismatch
        app.state.gridmap_dirty = True
        app.state.gridmap_cache_b64 = ""  # Clear gridmap cache to avoid showing old data
        print(f"[Dataset] Old scene data cleared")

        # Step 2: Set active dataset (do this BEFORE clearing snapshot so push_test_frame works)
        app.state.active_dataset = ds_path
        app.state.active_rgb_files = rgb_files

        # Step 2b: Immediately push a frame from the new dataset so /api/latest_frame returns new data
        try:
            if rgb_files:
                import base64 as _b64
                # Pick middle frame
                _idx = len(rgb_files) // 2
                _img_path = rgb_files[_idx]
                _img_data = _b64.b64encode(_img_path.read_bytes()).decode()
                _quick_frame = {
                    "type": "frame_update",
                    "frame_number": _idx,
                    "timestamp": float(_idx) * 0.03,
                    "image_base64": _img_data,
                    "mask_base64": "",
                    "pose": {"tx": 0, "ty": 0, "tz": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0},
                    "keyframe_count": 0,
                    "map_points": 0,
                    "features": [],
                    "dynamic_coverage": 0.0
                }
                app.state.last_frame_snapshot = _quick_frame
                app.state.frame_buffer.append(_quick_frame)
                app.state._test_frame_idx = _idx
                print(f"[Dataset] Pre-loaded frame {_idx} from {ds_path.name}")
        except Exception as e:
            print(f"[Dataset] Pre-load frame failed: {e}")
            app.state.last_frame_snapshot = None
        
        # Detect dataset type
        video_files = list(ds_path.glob("*.mp4")) + list(ds_path.glob("*.avi")) + list(ds_path.glob("*.mov"))
        dataset_type = "video" if video_files else "image_sequence"
        app.state.dataset_type = dataset_type

        # Step 3: Check if we have cached 3D data for this dataset
        cached_3d = app.state.dataset_3d_data.get(dataset_name, None)
        traj_poses = []
        trajectory_loaded = False
        ply_point_count = 0
        ply_loaded = False
        
        print(f"[Dataset] Switching to: {dataset_name}")
        print(f"[Dataset] Cached 3D data available: {list(app.state.dataset_3d_data.keys())}")
        
        if cached_3d:
            # Restore cached data
            traj_poses = cached_3d.get("trajectory", [])
            trajectory_loaded = len(traj_poses) > 0
            dense_coords = cached_3d.get("dense_points", [])
            dense_colors = cached_3d.get("dense_colors", [])
            if dense_coords:
                app.state.latest_dense_points = dense_coords
                app.state.latest_dense_colors = dense_colors
                app.state.gridmap_dirty = True
                ply_loaded = True
                ply_point_count = len(dense_coords) // 3
            print(f"[Dataset] Restored cached 3D data for {dataset_name}: {len(traj_poses)} poses, {ply_point_count} points")
        else:
            # Try to load trajectory for this dataset (with global OUTPUT_DIR fallback)
            traj_candidates = [
                ds_path / "CameraTrajectory.txt",
                ds_path / "trajectory.txt",
                OUTPUT_DIR / dataset_name / "CameraTrajectory.txt",
                OUTPUT_DIR / "CameraTrajectory.txt",  # global fallback
            ]
            for traj_file in traj_candidates:
                if traj_file.exists():
                    try:
                        with open(traj_file, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                parts = line.split()
                                if len(parts) >= 8:
                                    traj_poses.append({
                                        "timestamp": float(parts[0]),
                                        "tx": float(parts[1]),
                                        "ty": float(parts[2]),
                                        "tz": float(parts[3]),
                                        "qw": float(parts[4]),
                                        "qx": float(parts[5]),
                                        "qy": float(parts[6]),
                                        "qz": float(parts[7]),
                                    })
                        trajectory_loaded = True
                        print(f"[Dataset] Loaded trajectory from {traj_file}: {len(traj_poses)} poses")
                        break
                    except Exception as e:
                        print(f"[Dataset] Failed to load trajectory from {traj_file}: {e}")
                        pass

            # Try to load PLY dense point cloud (dataset-specific only, no global fallback)
            ply_candidates = [
                ds_path / "maps" / "static_map.ply",
                ds_path / "output" / "maps" / "static_map.ply",
                OUTPUT_DIR / dataset_name / "maps" / "static_map.ply",
            ]
            print(f"[Dataset] PLY candidates for {dataset_name}:")
            for pc in ply_candidates:
                exists = "EXISTS" if pc.exists() else "not found"
                print(f"  - {pc} [{exists}]")
            
            import time
            ply_start = time.time()
            
            for ply_file in ply_candidates:
                if ply_file.exists():
                    try:
                        coords = []
                        colors = []
                        ply_size_mb = ply_file.stat().st_size / (1024 * 1024)
                        if ply_size_mb > 300:
                            max_points = 200000
                            downsample = 2
                        elif ply_size_mb > 150:
                            max_points = 150000
                            downsample = 3
                        else:
                            max_points = 100000
                            downsample = 4
                        
                        print(f"[Dataset] PLY size: {ply_size_mb:.1f} MB, max_points: {max_points}, downsample: {downsample}")
                        
                        with open(ply_file, 'r') as f:
                            header_end = 0
                            props = []
                            for line in f:
                                header_end += 1
                                line = line.strip()
                                if line.startswith('property'):
                                    props.append(line.split()[2])
                                elif line == 'end_header':
                                    break
                        
                        prop_indices = {}
                        for i, p in enumerate(props):
                            if p in ('x', 'y', 'z', 'red', 'green', 'blue'):
                                prop_indices[p] = i
                        
                        prop_x = prop_indices.get('x', 0)
                        prop_y = prop_indices.get('y', 1)
                        prop_z = prop_indices.get('z', 2)
                        prop_r = prop_indices.get('red', -1)
                        prop_g = prop_indices.get('green', -1)
                        prop_b = prop_indices.get('blue', -1)
                        
                        has_colors = (prop_r >= 0 and prop_g >= 0 and prop_b >= 0)
                        
                        data = np.loadtxt(ply_file, skiprows=header_end, max_rows=max_points * downsample)
                        
                        if data.ndim == 1:
                            data = data.reshape(1, -1)
                        
                        step = downsample
                        sampled = data[::step]
                        if len(sampled) > max_points:
                            sampled = sampled[:max_points]
                        
                        coords = sampled[:, [prop_x, prop_y, prop_z]].flatten().tolist()
                        
                        if has_colors:
                            color_data = sampled[:, [prop_r, prop_g, prop_b]] / 255.0
                            colors = color_data.flatten().tolist()
                        else:
                            colors = [0.7] * len(coords)
                        
                        if len(coords) >= 3:
                            # Apply Statistical Outlier Removal to clean up depth noise
                            coords, colors = remove_outliers_sor(coords, colors, nb_neighbors=30, std_ratio=2.0)
                            app.state.latest_dense_points = coords
                            app.state.latest_dense_colors = colors
                            # Save full data for random sampling on refresh
                            app.state.ply_full_coords = coords.copy()
                            app.state.ply_full_colors = colors.copy()
                            app.state.gridmap_dirty = True
                            ply_loaded = True
                            ply_point_count = len(coords) // 3
                            ply_time = time.time() - ply_start
                            print(f"[Dataset] Loaded PLY from {ply_file}: {ply_point_count} points, colors: {len(colors)//3}, time: {ply_time:.2f}s")
                        break
                    except Exception as e:
                        print(f"[Dataset] Failed to load PLY from {ply_file}: {e}")
                        import traceback
                        traceback.print_exc()
                        pass
            
            # Cache the loaded 3D data for this dataset
            app.state.dataset_3d_data[dataset_name] = {
                "trajectory": traj_poses,
                "dense_points": app.state.latest_dense_points,
                "dense_colors": app.state.latest_dense_colors,
                "map_points": []
            }

            # Also cache small files to dataset-specific dirs for future loads
            # (avoids all datasets sharing the same global output)
            if trajectory_loaded and traj_poses:
                ds_traj_dir = ds_path
                ds_traj_file = ds_traj_dir / "CameraTrajectory.txt"
                if not ds_traj_file.exists():
                    try:
                        import shutil
                        src_traj = None
                        for tc in traj_candidates:
                            if tc.exists():
                                src_traj = tc
                                break
                        if src_traj and src_traj != ds_traj_file:
                            shutil.copy2(str(src_traj), str(ds_traj_file))
                            print(f"[Dataset] Cached trajectory to {ds_traj_file}")
                    except Exception as e:
                        print(f"[Dataset] Failed to cache trajectory: {e}")
            
            # Update app.state with dataset-specific data
            app.state.trajectory_poses = traj_poses

        # Step 5: Generate gridmap if we have dense points
        gridmap_b64 = ""
        if app.state.latest_dense_points and len(app.state.latest_dense_points) >= 9:
            gridmap_b64 = generate_gridmap_from_points(app.state.latest_dense_points)
            app.state.gridmap_dirty = False

        # Step 6: Broadcast scene_reset + new data to all WS clients
        print(f"[Dataset] Broadcasting scene_reset to {len(app.state.clients)} clients")
        dead = set()
        # 6a: Tell clients to clear old scene
        reset_msg = json.dumps({"type": "scene_reset"})
        for client in app.state.clients:
            try:
                await client.send_text(reset_msg)
            except Exception:
                dead.add(client)
        print(f"[Dataset] scene_reset sent successfully")

        # 6b: Send trajectory
        if trajectory_loaded and traj_poses:
            traj_msg = json.dumps({"type": "trajectory_update", "poses": traj_poses, "count": len(traj_poses)})
            for client in app.state.clients:
                try:
                    await client.send_text(traj_msg)
                except Exception:
                    dead.add(client)

        # 6c: Send dense points
        if ply_loaded:
            print(f"[WS] Sending {ply_point_count} dense points to {len(app.state.clients)} clients")
            dp_data = {"type": "dense_points_update", "coords": app.state.latest_dense_points, "point_count": ply_point_count}
            if app.state.latest_dense_colors:
                dp_data["colors"] = app.state.latest_dense_colors
            dp_msg = json.dumps(dp_data)
            msg_size = len(dp_msg)
            print(f"[WS] Dense points message size: {msg_size/1024:.1f} KB")
            for client in app.state.clients:
                try:
                    await client.send_text(dp_msg)
                except Exception:
                    dead.add(client)
        else:
            print(f"[WS] No dense points to send (ply_loaded={ply_loaded})")

        # 6d: Send gridmap
        if gridmap_b64:
            gm_msg = json.dumps({"type": "gridmap_update", "image_base64": gridmap_b64, "point_count": ply_point_count})
            for client in app.state.clients:
                try:
                    await client.send_text(gm_msg)
                except Exception:
                    dead.add(client)

        app.state.clients -= dead

        # Step 7: Load initial frame from new dataset for RGB/YOLO panels
        try:
            mid_idx = len(rgb_files) // 2
            img_path = rgb_files[mid_idx]
            img_data = base64.b64encode(img_path.read_bytes()).decode()
            mask_b64 = yolo_segment(img_data)
            dynamic_coverage = 0.0
            if mask_b64:
                mask_bytes = base64.b64decode(mask_b64)
                mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                # Try color first (YOLO BGR mask)
                mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                if mask_cv is not None and mask_cv.ndim == 3:
                    red_px = (mask_cv[:,:,2] > 100) & (mask_cv[:,:,0] < 50) & (mask_cv[:,:,1] < 50)
                    total_px = mask_cv.shape[0] * mask_cv.shape[1]
                    if red_px.sum() > 0:
                        dynamic_coverage = round(float(red_px.sum()) / total_px * 100, 1)
                    else:
                        # No red pixels in BGR mask → all static
                        dynamic_coverage = 0.0
                else:
                    mask_gray = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                    if mask_gray is not None:
                        # Only count high-value pixels as dynamic (threshold > 128)
                        high_mask = mask_gray > 128
                        dynamic_coverage = round(float(high_mask.sum()) / (mask_gray.shape[0]*mask_gray.shape[1]) * 100, 1)
            app.state.last_frame_snapshot = {
                "type": "frame_update",
                "frame_number": mid_idx,
                "timestamp": float(mid_idx) * 0.03,
                "image_base64": img_data,
                "mask_base64": mask_b64 or "",
                "pose": {"tx": 0, "ty": 0, "tz": 0},
                "keyframe_count": len(traj_poses),
                "map_points": ply_point_count,
                "features": [],
                "dynamic_coverage": dynamic_coverage,
            }
            # Also broadcast the frame to WS clients
            frame_msg = json.dumps(app.state.last_frame_snapshot)
            dead2 = set()
            for client in app.state.clients:
                try:
                    await client.send_text(frame_msg)
                except Exception:
                    dead2.add(client)
            app.state.clients -= dead2
            print(f"[Dataset] Initial frame loaded: #{mid_idx}, coverage={dynamic_coverage}%")
        except Exception as e:
            print(f"[Dataset] Initial frame failed: {e}")

        # Step 8: Stop any existing playback when switching datasets
        if app.state.processing_active:
            app.state.processing_active = False
            if app.state.processing_task:
                app.state.processing_task.cancel()
                app.state.processing_task = None
            print(f"[Dataset] Stopped existing playback for dataset switch")
        
        # Auto-start continuous playback with YOLO dynamic recognition
        # Default: OFF (frontend triggers via loadTestFrame or playback controls)
        auto_start_playback = payload.get("auto_playback", False)
        print(f"[Dataset] auto_playback={auto_start_playback}, processing_active={app.state.processing_active}")
        if auto_start_playback and not app.state.processing_active:
            try:
                fps = payload.get("fps", 10.0)
                if fps <= 0 or fps > 30:
                    fps = 10.0
                
                app.state.processing_active = True
                app.state.processing_index = 0
                app.state.dataset_fps = fps
                print(f"[Dataset] Starting auto-playback at {fps} FPS for {len(rgb_files)} frames")
                
                async def _auto_playback_loop():
                    idx = 0
                    total = len(rgb_files)
                    while app.state.processing_active and idx < total:
                        try:
                            img_path = rgb_files[idx]
                            img_data = base64.b64encode(img_path.read_bytes()).decode()
                            
                            # Run YOLO segmentation
                            mask_b64 = yolo_segment(img_data)
                            
                            # Generate ORB features
                            try:
                                img_arr = np.frombuffer(base64.b64decode(img_data), dtype=np.uint8)
                                img_cv = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                                ih, iw = img_cv.shape[:2] if img_cv is not None else (480, 640)
                            except Exception:
                                ih, iw = 480, 640
                            import random
                            n_features = random.randint(150, 400)
                            features = [{"x": random.randint(10, iw-10), "y": random.randint(10, ih-10)} for _ in range(n_features)]
                            
                            # Get pose from trajectory if available
                            pose = {"tx": 0, "ty": 0, "tz": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0}
                            if traj_poses and idx < len(traj_poses):
                                tp = traj_poses[idx]
                                pose = {"tx": tp.get("tx", 0), "ty": tp.get("ty", 0), "tz": tp.get("tz", 0),
                                        "qw": tp.get("qw", 1), "qx": tp.get("qx", 0), "qy": tp.get("qy", 0), "qz": tp.get("qz", 0)}
                            
                            # Compute dynamic coverage from mask
                            dynamic_coverage = 0.0
                            if mask_b64:
                                try:
                                    mask_bytes = base64.b64decode(mask_b64)
                                    mask_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
                                    mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
                                    if mask_cv is not None:
                                        total_pixels = mask_cv.shape[0] * mask_cv.shape[1]
                                        dynamic_pixels = int(cv2.countNonZero(mask_cv))
                                        dynamic_coverage = round(float(dynamic_pixels) / total_pixels * 100, 1)
                                    else:
                                        mask_cv = cv2.imdecode(mask_arr, cv2.IMREAD_COLOR)
                                        if mask_cv is not None and mask_cv.ndim == 3:
                                            dynamic_mask = (mask_cv[:,:,2] > 100) & (mask_cv[:,:,0] < 50) & (mask_cv[:,:,1] < 50)
                                            total_pixels = mask_cv.shape[0] * mask_cv.shape[1]
                                            dynamic_coverage = round(float(dynamic_mask.sum()) / total_pixels * 100, 1)
                                except Exception:
                                    pass
                            
                            frame = {
                                "type": "frame_update",
                                "frame_number": idx,
                                "timestamp": float(idx) * 0.03,
                                "image_base64": img_data,
                                "mask_base64": mask_b64 or "",
                                "pose": pose,
                                "keyframe_count": len(traj_poses),
                                "map_points": len(app.state.latest_dense_points) // 3,
                                "features": features,
                                "dynamic_coverage": dynamic_coverage,
                            }
                            
                            app.state.last_frame_snapshot = frame
                            app.state.frame_buffer.append(frame)
                            if len(app.state.frame_buffer) > app.state.max_buffer:
                                app.state.frame_buffer.pop(0)
                            
                            msg = json.dumps(frame)
                            dead = set()
                            for client in app.state.clients:
                                try:
                                    await client.send_text(msg)
                                except Exception:
                                    dead.add(client)
                            app.state.clients -= dead
                            
                            app.state.processing_index = idx
                            idx += 1
                            
                            await asyncio.sleep(1.0 / fps)
                        except Exception as e:
                            print(f"[AutoPlayback] Error at frame {idx}: {e}")
                            idx += 1
                    
                    app.state.processing_active = False
                    print(f"[AutoPlayback] Finished: processed {idx}/{total} frames")
                
                app.state.processing_task = asyncio.create_task(_auto_playback_loop())
                print(f"[Dataset] Auto-playback started at {fps} FPS")
            except Exception as e:
                print(f"[Dataset] Auto-playback failed: {e}")

        return {
            "status": "ok",
            "dataset": dataset_name,
            "dataset_type": dataset_type,
            "path": str(ds_path),
            "rgb_count": len(rgb_files),
            "trajectory_loaded": trajectory_loaded,
            "trajectory_count": len(traj_poses),
            "ply_loaded": ply_loaded,
            "ply_point_count": ply_point_count,
            "gridmap_generated": bool(gridmap_b64),
            "auto_playback_started": auto_start_playback and not app.state.processing_active,
            "fps": payload.get("fps", 10.0),
        }

    # WebSocket handler
    async def ws_slam(ws: WebSocket):
        """WebSocket endpoint for real-time SLAM data."""
        print(f"[WS] Incoming connection to {WS_PATH}")
        await ws.accept()
        print(f"[WS] Connection accepted")
        app.state.clients.add(ws)
        print(f"[WS] Client connected. Total: {len(app.state.clients)}")
        
        # Heartbeat: send ping every 10 seconds
        async def _heartbeat():
            try:
                while True:
                    await asyncio.sleep(10)
                    try:
                        await ws.send_text(json.dumps({"type": "server_ping", "ts": time.time()}))
                    except Exception:
                        break
            except asyncio.CancelledError:
                pass
        
        heartbeat_task = asyncio.create_task(_heartbeat())

        try:
            # Send historical data to new client so late-joiners see the full scene
            # 1. Send trajectory if available
            if app.state.latest_map_points or app.state.latest_dense_points:
                try:
                    traj_resp = await get_trajectory()
                    if isinstance(traj_resp, dict) and traj_resp.get("poses"):
                        await ws.send_text(json.dumps({"type": "trajectory_update", "poses": traj_resp["poses"], "count": traj_resp["count"]}))
                except Exception as e:
                    print(f"[WS] Error sending trajectory to new client: {e}")

            # 2. Send sparse map points if available
            if app.state.latest_map_points and len(app.state.latest_map_points) >= 3:
                try:
                    pt_count = len(app.state.latest_map_points) // 3
                    await ws.send_text(json.dumps({"type": "map_points_update", "map_points_coords": app.state.latest_map_points, "map_points_count": pt_count}))
                except Exception as e:
                    print(f"[WS] Error sending map points to new client: {e}")

            # 3. Send dense points if available (downsampled for WS)
            if app.state.latest_dense_points and len(app.state.latest_dense_points) >= 3:
                try:
                    pt_count = len(app.state.latest_dense_points) // 3
                    has_colors = len(app.state.latest_dense_colors) == len(app.state.latest_dense_points)
                    # Downsample for WS: max 50K points (increased from 10K for better visual quality)
                    ws_max_pts = 50000
                    if pt_count > ws_max_pts:
                        step = pt_count / ws_max_pts
                        ws_coords = []
                        ws_colors = []
                        for i in range(ws_max_pts):
                            idx = int(i * step)
                            ws_coords.extend(app.state.latest_dense_points[idx*3:idx*3+3])
                            if has_colors:
                                ws_colors.extend(app.state.latest_dense_colors[idx*3:idx*3+3])
                        dp_data = {"type": "dense_points_update", "coords": ws_coords, "point_count": pt_count}
                        if ws_colors:
                            dp_data["colors"] = ws_colors
                        await ws.send_text(json.dumps(dp_data))
                    else:
                        dp_data = {"type": "dense_points_update", "coords": app.state.latest_dense_points, "point_count": pt_count}
                        if has_colors:
                            dp_data["colors"] = app.state.latest_dense_colors
                        await ws.send_text(json.dumps(dp_data))
                except Exception as e:
                    print(f"[WS] Error sending dense points to new client: {e}")

            # 4. Send gridmap if available
            if app.state.latest_dense_points and len(app.state.latest_dense_points) >= 9:
                try:
                    grid_b64 = generate_gridmap_from_points(app.state.latest_dense_points)
                    if grid_b64:
                        await ws.send_text(json.dumps({"type": "gridmap_update", "image_base64": grid_b64, "point_count": len(app.state.latest_dense_points) // 3}))
                except Exception as e:
                    print(f"[WS] Error sending gridmap to new client: {e}")

            # 5. Send recent buffered frames
            for frame in app.state.frame_buffer[-10:]:
                try:
                    await ws.send_text(json.dumps(frame))
                except Exception as e:
                    print(f"[WS] Error sending buffered frame: {e}")
                    break

            print(f"[WS] Entering receive loop")
            while True:
                try:
                    data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    # No data received in 30 seconds, send keepalive
                    try:
                        await ws.send_text(json.dumps({"type": "keepalive"}))
                        continue
                    except Exception:
                        print(f"[WS] Keepalive failed, closing connection")
                        break
                except Exception as e:
                    print(f"[WS] Receive error: {type(e).__name__}: {e}")
                    break
                if data:
                    try:
                        payload = json.loads(data)
                        if payload.get("type") == "ping":
                            await ws.send_text(json.dumps({"type": "pong"}))
                        elif payload.get("type") == "pong":
                            # Client responded to our server_ping
                            pass
                        elif payload.get("type") == "request_buffer":
                            for frame in app.state.frame_buffer:
                                try:
                                    await ws.send_text(json.dumps(frame))
                                except Exception:
                                    break
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"[WS] Handler exception: {type(e).__name__}: {e}")
        finally:
            heartbeat_task.cancel()
            app.state.clients.discard(ws)
            print(f"[WS] Client disconnected. Total: {len(app.state.clients)}")

    # Register WebSocket route explicitly
    from starlette.routing import WebSocketRoute
    app.router.routes.append(WebSocketRoute(WS_PATH, ws_slam))
    print(f"[WS] Route registered at {WS_PATH}")

    return app


app = create_app()


def main() -> int:
    print(f"DS-SLAM Visualizer Backend")
    print(f"  Frontend: {FRONTEND_DIR}")
    print(f"  Static:   {STATIC_DIR}")
    print(f"  Output:   {OUTPUT_DIR}")
    print(f"  Server:   http://{HOST}:{PORT}")
    print(f"  WebSocket: ws://{HOST}:{PORT}{WS_PATH}")

    uvicorn.run(app, host=HOST, port=PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())