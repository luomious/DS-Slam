import urllib.request
import json

BASE = "http://127.0.0.1:8081"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}", timeout=5)
    return json.loads(r.read().decode())

# 检查轨迹
traj = get("/api/trajectory?limit=10")
poses = traj.get("poses", [])
if poses:
    txs = [p['tx'] for p in poses]
    tys = [p['ty'] for p in poses]
    tzs = [p['tz'] for p in poses]
    print(f"=== 轨迹数据 ({traj.get('count', 0)} 位姿) ===")
    print(f"TX范围: [{min(txs):.3f}, {max(txs):.3f}]")
    print(f"TY范围: [{min(tys):.3f}, {max(tys):.3f}]")
    print(f"TZ范围: [{min(tzs):.3f}, {max(tzs):.3f}]")
    print(f"轨迹中心: ({(min(txs)+max(txs))/2:.3f}, {(min(tys)+max(tys))/2:.3f}, {(min(tzs)+max(tzs))/2:.3f})")

# 检查点云
dense = get("/api/dense_points?max_points=100")
n = dense.get("point_count", 0)
print(f"\n=== 点云数据 ===")
print(f"总点数: {n}")
if n > 0 and dense.get("coords"):
    coords = dense["coords"]
    xs = [coords[i*3] for i in range(min(100, len(coords)//3))]
    ys = [coords[i*3+1] for i in range(min(100, len(coords)//3))]
    zs = [coords[i*3+2] for i in range(min(100, len(coords)//3))]
    print(f"X范围: [{min(xs):.3f}, {max(xs):.3f}]")
    print(f"Y范围: [{min(ys):.3f}, {max(ys):.3f}]")
    print(f"Z范围: [{min(zs):.3f}, {max(zs):.3f}]")
    print(f"点云中心: ({(min(xs)+max(xs))/2:.3f}, {(min(ys)+max(ys))/2:.3f}, {(min(zs)+max(zs))/2:.3f})")

# 检查最新帧
frame_data = get("/api/latest_frame")
frame = frame_data.get("frame", {})
print(f"\n=== 最新帧 ===")
print(f"帧号: {frame.get('frame_number', 'N/A')}")
print(f"动态覆盖率: {frame.get('dynamic_coverage', 0)}%")
