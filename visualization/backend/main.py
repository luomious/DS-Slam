#!/usr/bin/env python3
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
    app.state.max_buffer = 100

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

    @app.get("/api/gridmap")
    async def get_gridmap():
        """Get grid map image."""
        grid_file = OUTPUT_DIR / "maps" / "grid_map.png"

        if not grid_file.exists():
            return JSONResponse({"error": "Grid map not found"}, status_code=404)

        return FileResponse(grid_file, media_type="image/png")

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
        app.state.frame_buffer.append(frame)
        if len(app.state.frame_buffer) > app.state.max_buffer:
            app.state.frame_buffer.pop(0)

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

    @app.websocket(WS_PATH)
    async def ws_slam(ws: WebSocket):
        """WebSocket endpoint for real-time SLAM data."""
        await ws.accept()
        app.state.clients.add(ws)
        print(f"Client connected. Total: {len(app.state.clients)}")

        try:
            # Send recent buffered frames to new client
            for frame in app.state.frame_buffer[-10:]:
                await ws.send_text(json.dumps(frame))

            while True:
                data = await ws.receive_text()
                if data:
                    try:
                        payload = json.loads(data)
                        if payload.get("type") == "ping":
                            await ws.send_text(json.dumps({"type": "pong"}))
                        elif payload.get("type") == "request_buffer":
                            for frame in app.state.frame_buffer:
                                await ws.send_text(json.dumps(frame))
                    except json.JSONDecodeError:
                        pass
        except WebSocketDisconnect:
            pass
        finally:
            app.state.clients.discard(ws)
            print(f"Client disconnected. Total: {len(app.state.clients)}")

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