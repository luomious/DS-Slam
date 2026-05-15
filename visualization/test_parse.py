from pathlib import Path

def parse_tum_trajectory(filepath):
    poses = []
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 8:
                poses.append({
                    't': float(parts[0]),
                    'pos': [float(parts[1]), float(parts[2]), float(parts[3])],
                    'quat': [float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])]
                })
    return poses

traj = parse_tum_trajectory(Path('E:/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/CameraTrajectory.txt'))
print(f'Parsed {len(traj)} poses')
print(f'First: t={traj[0]["t"]}, pos=({traj[0]["pos"][0]:.3f}, {traj[0]["pos"][1]:.3f}, {traj[0]["pos"][2]:.3f})')
print(f'Last:  t={traj[-1]["t"]}, pos=({traj[-1]["pos"][0]:.3f}, {traj[-1]["pos"][1]:.3f}, {traj[-1]["pos"][2]:.3f})')

# Calculate trajectory length
length = 0
for i in range(1, len(traj)):
    import math
    dx = traj[i]['pos'][0] - traj[i-1]['pos'][0]
    dy = traj[i]['pos'][1] - traj[i-1]['pos'][1]
    dz = traj[i]['pos'][2] - traj[i-1]['pos'][2]
    length += math.sqrt(dx*dx + dy*dy + dz*dz)
print(f'Trajectory length: {length:.3f} m')
