#!/usr/bin/env python3
# [PATCHED]
"""DS-SLAM Visualizer Backend - Self-contained version."""

from __future__ import annotations

import json
import time
import math
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
            det = det_out[0]  # (116, 8400)
            total_features, num_proposals = det.shape[1], det.shape[0]
            nm = 32  # mask coefficients per proposal
            nc = total_features - 4 - nm  # number of classes
            
            # Parse prototype masks
            proto = proto_out[0]  # (32, 160, 160)
            mask_h, mask_w = proto.shape[1], proto.shape[2]
            
            # Build combined dynamic mask
            combined = np.zeros((mask_h, mask_w), dtype=np.float32)
            
            for i in range(num_proposals):
                row = det[i]
                cx, cy, w_box, h_box = row[0], row[1], row[2], row[3]
                scores = row[4:4+nc]
                
                best_class = int(np.argmax(scores))
                best_score = float(scores[best_class])
                
                if best_score < self.conf_threshold:
                    continue
                if best_class not in DYNAMIC_COCO_IDS:
                    continue
                
                # Mask coefficients
                coeffs = row[4+nc:4+nc+nm]
                
                # Linear combination of prototype masks + sigmoid
                mask_val = np.zeros((mask_h, mask_w), dtype=np.float32)
                for k in range(nm):
                    mask_val += coeffs[k] * proto[k]
                
                prob = 1.0 / (1.0 + np.exp(-mask_val))
                combined = np.maximum(combined, (prob > 0.5).astype(np.float32) * 255.0)
            
            # Resize to original image size
            orig_h, orig_w = img_bgr.shape[:2]
            mask_resized = cv2.resize(combined, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            mask_uint8 = mask_resized.astype(np.uint8)
            
            # Morphological cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask_uint8 = cv2.dilate(mask_uint8, kernel, iterations=1)
            
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
        _yolo_inferencer = YOLOInferencer(model_path)
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
            print("[YOLO] segment: inferencer not valid!")
            return ""
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
        pad = 0.5  # 0.5m padding
        x_min, x_max = xs.min() - pad, xs.max() + pad
        z_min, z_max = zs.min() - pad, zs.max() + pad
        x_range = x_max - x_min
        z_range = z_max - z_min
        
        # Ensure minimum grid size
        size_m = max(x_range, z_range, 2.0)
        cx = (x_min + x_max) / 2
        cz = (z_min + z_max) / 2
        
        # Adaptive resolution based on point density
        area = x_range * z_range
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
        
        # Vectorized mapping: X→col, Z→row
        cols = ((xs - cx + size_m/2) / resolution).astype(np.int32)
        rows = ((zs - cz + size_m/2) / resolution).astype(np.int32)
        
        valid = (rows >= 0) & (rows < grid_h) & (cols >= 0) & (cols < grid_w)
        rows_v, cols_v = rows[valid], cols[valid]
        
        # Accumulate with height info for 2.5D effect
        for r, c, y_val in zip(rows_v, cols_v, ys[valid]):
            grid[r, c] = max(grid[r, c], y_val)
        
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
            y_vals = grid[grid_mask]
            y_min, y_max = y_vals.min(), y_vals.max()
            y_range = max(y_max - y_min, 0.01)
            
            # Height-based coloring (blue=low, green=mid, red=high)
            normalized = (y_vals - y_min) / y_range
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
        
        # Add axis labels (pixel coordinates)
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
PORT = 8000
WS_PATH = "/ws/slam"


def create_app() -> FastAPI:
    app = FastAPI(title="DS-SLAM Visualizer")
    app.state.clients: set[WebSocket] = set()
    app.state.frame_buffer: list[dict] = []
    app.state.last_frame_snapshot: dict | None = None
    app.state.max_buffer = 100
    app.state.latest_map_points: list = []  # Store latest map point coords for new clients
    app.state.latest_dense_points: list = []  # Dense point cloud coords for visualization
    app.state.gridmap_dirty: bool = True  # [PATCHED] Flag to regenerate gridmap

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
        """Load trajectory data from CameraTrajectory.txt."""
        traj_file = OUTPUT_DIR / "CameraTrajectory.txt"
        if not traj_file.exists():
            traj_file = PROJECT_ROOT / "orbslam3" / "Examples" / "RGB-D" / "CameraTrajectory.txt"
        if not traj_file.exists():
            # Check for recent trajectory in common locations
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


    @app.get("/api/latest_frame")
    async def get_latest_frame():
        if app.state.last_frame_snapshot:
            return {"frame": app.state.last_frame_snapshot, "buffered": len(app.state.frame_buffer), "source": "snapshot"}
        elif app.state.frame_buffer and len(app.state.frame_buffer) > 0:
            return {"frame": app.state.frame_buffer[-1], "buffered": len(app.state.frame_buffer)}
        return {"error": "No frames"}, 503

    @app.get("/api/gridmap")
    async def get_gridmap():
        """Get grid map image. Falls back to dynamic generation from map points."""
        grid_file = OUTPUT_DIR / "maps" / "grid_map.png"

        if grid_file.exists():
            return FileResponse(grid_file, media_type="image/png")
        
        # Dynamic generation: prefer dense points, fallback to sparse map points
        coords = app.state.latest_dense_points or app.state.latest_map_points
        if len(coords) >= 9:  # At least 3 points
            grid_b64 = generate_gridmap_from_points(coords)
            if grid_b64:
                import io
                img_bytes = base64.b64decode(grid_b64)
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
    async def get_dense_points():
        """Get dense point cloud from depth-based reconstruction."""
        coords = app.state.latest_dense_points
        point_count = len(coords) // 3
        return {"point_count": point_count, "coords": coords}

    @app.post("/api/dense_points")
    async def set_dense_points(data: dict[str, Any]):
        """Receive dense point cloud data and broadcast to clients.
        
        Supports two modes:
        - Replace (default): coords replace existing dense points
        - Append (append=True): coords are appended to existing dense points
        """
        coords = data.get("coords", [])
        append_mode = data.get("append", False)
        
        if coords:
            if append_mode and app.state.latest_dense_points:
                app.state.latest_dense_points.extend(coords)
            else:
                app.state.latest_dense_points = coords
            
            app.state.gridmap_dirty = True
            point_count = len(app.state.latest_dense_points) // 3
            
            # Broadcast full accumulated points to WebSocket clients
            # (only on final chunk or when not chunking)
            if not append_mode or data.get("final", False):
                msg = json.dumps({
                    "type": "dense_points_update",
                    "coords": app.state.latest_dense_points,
                    "point_count": point_count
                })
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
            app.state.gridmap_dirty = True

        # Real YOLO segmentation (Phase 2) - replace pseudo mask
        if msg_type == "frame_update" and not frame.get("mask_base64") and frame.get("image_base64"):
            yolo_mask = yolo_segment(frame["image_base64"])
            if yolo_mask:
                frame["mask_base64"] = yolo_mask
                frame["_yolo_mask"] = True  # Flag for frontend
            else:
                # Fallback to pseudo mask if YOLO fails
                pseudo_mask = generate_pseudo_mask(frame["image_base64"])
                if pseudo_mask:
                    frame["mask_base64"] = pseudo_mask
                    frame["_pseudo_mask"] = True
        
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

    @app.post("/api/push_test_frame")
    async def push_test_frame():
        """Push a test frame with YOLO mask for panel verification."""
        import base64, numpy as np
        from pathlib import Path
        
        # Use active dataset if set, otherwise find first available
        if hasattr(app.state, 'active_dataset') and app.state.active_dataset:
            ds = app.state.active_dataset
            rgb_files = app.state.active_rgb_files
        else:
            ds_base = PROJECT_ROOT / "datasets" / "tum"
            datasets = sorted([d for d in ds_base.iterdir() if d.is_dir()]) if ds_base.exists() else []
            if not datasets:
                return {"error": "No datasets found"}
            
            ds = datasets[0]
            rgb_dir = ds / "rgb"
            rgb_files = sorted([f for f in rgb_dir.iterdir() if f.suffix == '.png']) if rgb_dir.exists() else []
        
        if not rgb_files:
            return {"error": "No RGB files in dataset"}
        
        # Read middle frame
        img_path = rgb_files[len(rgb_files)//2]
        img_data = base64.b64encode(img_path.read_bytes()).decode()
        
        # Generate a YOLO-style mask using pure Python (no PIL needed)
        import struct, zlib as _zlib
        try:
            # Read image dimensions from PNG header
            with open(img_path, 'rb') as _f:
                _f.read(16)  # skip to IHDR
                _w, _h = struct.unpack('>II', _f.read(8))
            w, h = _w, _h
        except Exception:
            w, h = 640, 480
        
        # Build RGBA pixel data with colored rectangles (simulated YOLO detections)
        _raw = bytearray(w * h * 4)
        _rects = [
            (w//10, h//10, w//3, h//2, 255, 0, 0, 80),
            (w//2, h//5, w*9//10, h*2//3, 0, 255, 0, 80),
            (w//4, h//2, w*3//4, h*9//10, 0, 0, 255, 80),
        ]
        for _x1, _y1, _x2, _y2, _r, _g, _b, _a in _rects:
            for _y in range(max(0,_y1), min(h,_y2)):
                for _x in range(max(0,_x1), min(w,_x2)):
                    _idx = (_y * w + _x) * 4
                    _raw[_idx] = _r; _raw[_idx+1] = _g; _raw[_idx+2] = _b; _raw[_idx+3] = _a
        
        # Encode as PNG
        def _png_chunk(ctype, data):
            _c = ctype + data
            return struct.pack('>I', len(data)) + _c + struct.pack('>I', _zlib.crc32(_c) & 0xffffffff)
        _filtered = bytearray()
        for _y in range(h):
            _filtered.append(0)
            _filtered.extend(_raw[_y*w*4:(_y+1)*w*4])
        _compressed = _zlib.compress(bytes(_filtered))
        _png = b'\x89PNG\r\n\x1a\n'
        _png += _png_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
        _png += _png_chunk(b'IDAT', _compressed)
        _png += _png_chunk(b'IEND', b'')
        mask_b64 = base64.b64encode(_png).decode()
        
        frame = {
            "type": "frame_update",
            "frame_number": len(rgb_files) // 2,
            "timestamp": 0.0,
            "image_base64": img_data,
            "mask_base64": mask_b64,
            "pose": {"tx": 0, "ty": 0, "tz": 0},
            "keyframe_count": 10,
            "map_points": 500,
            "features": []
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
        
        return {"status": "ok", "has_image": bool(img_data), "has_mask": bool(mask_b64), "dataset": ds.name}

    @app.get("/api/datasets")
    async def list_datasets():
        """List available TUM RGB-D datasets."""
        from pathlib import Path
        ds_base = PROJECT_ROOT / "datasets" / "tum"
        datasets = []
        if ds_base.exists():
            for d in sorted(ds_base.iterdir()):
                if d.is_dir():
                    has_rgb = (d / "rgb").is_dir()
                    has_depth = (d / "depth").is_dir()
                    has_assoc = (d / "associations.txt").is_file()
                    datasets.append({
                        "name": d.name,
                        "path": str(d),
                        "has_rgb": has_rgb,
                        "has_depth": has_depth,
                        "has_associations": has_assoc,
                        "ready": has_rgb and has_depth and has_assoc
                    })
        return {"datasets": datasets, "count": len(datasets)}

    @app.post("/api/select_dataset")
    async def select_dataset(payload: dict):
        """Select active dataset for test frame pushing."""
        from pathlib import Path
        dataset_name = payload.get("dataset", "")
        if not dataset_name:
            return {"error": "No dataset specified"}
        
        ds_path = PROJECT_ROOT / "datasets" / "tum" / dataset_name
        if not ds_path.exists():
            return {"error": f"Dataset not found: {dataset_name}"}
        
        rgb_dir = ds_path / "rgb"
        if not rgb_dir.exists():
            return {"error": f"No RGB directory in {dataset_name}"}
        
        rgb_files = sorted([f for f in rgb_dir.iterdir() if f.suffix == '.png'])
        if not rgb_files:
            return {"error": f"No RGB files in {dataset_name}"}
        
        app.state.active_dataset = ds_path
        app.state.active_rgb_files = rgb_files
        
        return {
            "status": "ok",
            "dataset": dataset_name,
            "path": str(ds_path),
            "rgb_count": len(rgb_files)
        }

    # WebSocket handler
    async def ws_slam(ws: WebSocket):
        """WebSocket endpoint for real-time SLAM data."""
        print(f"[WS] Incoming connection to {WS_PATH}")
        await ws.accept()
        print(f"[WS] Connection accepted")
        app.state.clients.add(ws)
        print(f"[WS] Client connected. Total: {len(app.state.clients)}")

        try:
            # Send recent buffered frames to new client
            for frame in app.state.frame_buffer[-10:]:
                try:
                    await ws.send_text(json.dumps(frame))
                except Exception as e:
                    print(f"[WS] Error sending buffered frame: {e}")
                    break

            print(f"[WS] Entering receive loop")
            while True:
                try:
                    data = await ws.receive_text()
                except Exception as e:
                    print(f"[WS] Receive error: {type(e).__name__}: {e}")
                    break
                if data:
                    try:
                        payload = json.loads(data)
                        if payload.get("type") == "ping":
                            await ws.send_text(json.dumps({"type": "pong"}))
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