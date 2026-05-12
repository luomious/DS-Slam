#!/usr/bin/env python3
"""简化版 DS-SLAM 可视化后端 - 读取轨迹文件并通过 WebSocket 推送"""

import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

# 轨迹文件路径
TRAJ_FILE = Path("E:/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/CameraTrajectory.txt")
KF_FILE = Path("E:/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/KeyFrameTrajectory.txt")

app = FastAPI(title="DS-SLAM Simple Visualizer")
clients = []

def parse_tum_trajectory(filepath: Path):
    """解析 TUM 格式轨迹文件"""
    poses = []
    if not filepath.exists():
        return poses
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 8:
                timestamp = float(parts[0])
                tx, ty, tz = float(parts[1]), float(parts[2]), float(parts[3])
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                poses.append({
                    "t": timestamp,
                    "pos": [tx, ty, tz],
                    "quat": [qx, qy, qz, qw]
                })
    return poses

@app.get("/")
async def index():
    """返回前端页面"""
    html_content = Path(__file__).parent / "simple_frontend.html"
    if html_content.exists():
        return HTMLResponse(content=html_content.read_text(encoding='utf-8'))
    return {"error": "frontend not found"}

@app.get("/api/trajectory")
async def get_trajectory():
    """获取轨迹数据（HTTP API）"""
    camera_traj = parse_tum_trajectory(TRAJ_FILE)
    kf_traj = parse_tum_trajectory(KF_FILE)
    return {
        "camera_trajectory": camera_traj,
        "keyframe_trajectory": kf_traj,
        "camera_count": len(camera_traj),
        "keyframe_count": len(kf_traj)
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print(f"Client connected. Total: {len(clients)}")
    
    try:
        # 发送初始数据
        camera_traj = parse_tum_trajectory(TRAJ_FILE)
        kf_traj = parse_tum_trajectory(KF_FILE)
        
        await websocket.send_text(json.dumps({
            "type": "init",
            "camera_trajectory": camera_traj,
            "keyframe_trajectory": kf_traj
        }))
        
        # 保持连接
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        if websocket in clients:
            clients.remove(websocket)
        print(f"Client disconnected. Total: {len(clients)}")

if __name__ == "__main__":
    print("="*50)
    print("DS-SLAM Simple Visualizer")
    print("="*50)
    print(f"Trajectory: {TRAJ_FILE}")
    print(f"KeyFrames:  {KF_FILE}")
    print("\nOpen browser: http://localhost:8000")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
