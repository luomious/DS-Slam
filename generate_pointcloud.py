"""
Generate point cloud from depth images and camera trajectory for TUM datasets.
This script creates a PLY file from RGB-D data with semantic segmentation to filter dynamic objects.
"""

import os
import sys
import numpy as np
from PIL import Image
from pathlib import Path
import cv2

# Try to import YOLO model
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("Warning: ultralytics not installed. Install with: pip install ultralytics")

def load_trajectory(traj_file):
    """Load camera trajectory from CameraTrajectory.txt"""
    poses = {}
    with open(traj_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 8:
                timestamp = float(parts[0])
                tx, ty, tz = float(parts[1]), float(parts[2]), float(parts[3])
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                poses[timestamp] = {
                    'tx': tx, 'ty': ty, 'tz': tz,
                    'qx': qx, 'qy': qy, 'qz': qz, 'qw': qw
                }
    return poses

def quaternion_to_rotation_matrix(qx, qy, qz, qw):
    """Convert quaternion to rotation matrix"""
    r00 = 1 - 2*qy*qy - 2*qz*qz
    r01 = 2*qx*qy - 2*qz*qw
    r02 = 2*qx*qz + 2*qy*qw
    r10 = 2*qx*qy + 2*qz*qw
    r11 = 1 - 2*qx*qx - 2*qz*qz
    r12 = 2*qy*qz - 2*qx*qw
    r20 = 2*qx*qz - 2*qy*qw
    r21 = 2*qy*qz + 2*qx*qw
    r22 = 1 - 2*qx*qx - 2*qy*qy
    return np.array([[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]])

def generate_static_mask(rgb_img, yolo_model=None):
    """Generate mask for static regions (filter out people and other dynamic objects)"""
    h, w = rgb_img.shape[:2]
    
    # Default: all pixels are static
    static_mask = np.ones((h, w), dtype=bool)
    
    if yolo_model is not None:
        try:
            # Run YOLO segmentation
            results = yolo_model(rgb_img, verbose=False)
            
            if results and len(results) > 0:
                result = results[0]
                
                # Create mask for dynamic objects (people, etc.)
                dynamic_mask = np.zeros((h, w), dtype=bool)
                
                if hasattr(result, 'masks') and result.masks is not None:
                    for i, mask in enumerate(result.masks.data):
                        # Get class name
                        if hasattr(result, 'names'):
                            class_name = result.names[int(result.boxes.cls[i])] if i < len(result.boxes.cls) else ""
                        else:
                            class_name = ""
                        
                        # Filter dynamic classes (people, animals, vehicles, etc.)
                        dynamic_classes = ['person', 'dog', 'cat', 'horse', 'sheep', 'cow', 'elephant', 
                                         'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 
                                         'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                                         'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
                                         'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife',
                                         'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange', 
                                         'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
                                         'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet',
                                         'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
                                         'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
                                         'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush']
                        
                        if class_name.lower() in dynamic_classes:
                            # Resize mask to image size
                            mask_np = mask.cpu().numpy()
                            mask_resized = cv2.resize(mask_np, (w, h))
                            dynamic_mask |= (mask_resized > 0.5)
                
                # Static mask = not dynamic
                static_mask = ~dynamic_mask
                
        except Exception as e:
            print(f"Warning: YOLO segmentation failed: {e}")
    
    return static_mask

def depth_to_pointcloud(depth_img, rgb_img, fx, fy, cx, cy, depth_factor=5000.0, static_mask=None):
    """Convert depth image to point cloud with optional static mask"""
    h, w = depth_img.shape
    ys, xs = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    
    # Convert depth to meters
    z = depth_img.astype(np.float32) / depth_factor
    
    # Create mask for valid depth values (non-zero and reasonable range)
    valid_mask = (z > 0.1) & (z < 10.0)
    
    # Apply static mask if provided
    if static_mask is not None:
        valid_mask = valid_mask & static_mask
    
    # Calculate 3D coordinates
    x = (xs - cx) * z / fx
    y = (ys - cy) * z / fy
    
    # Stack coordinates
    points = np.stack([x[valid_mask], y[valid_mask], z[valid_mask]], axis=1)
    
    # Get colors if RGB image is provided
    colors = None
    if rgb_img is not None:
        colors = rgb_img[valid_mask]
    
    return points, colors

def generate_ply(dataset_path, output_ply, max_frames=50, downsample=4, use_segmentation=True):
    """Generate PLY file from RGB-D dataset with semantic segmentation"""
    dataset_path = Path(dataset_path)
    
    # Camera intrinsics for TUM3
    fx, fy = 535.4, 539.2
    cx, cy = 320.1, 247.6
    depth_factor = 5000.0
    
    # Load YOLO model if available
    yolo_model = None
    if use_segmentation and HAS_YOLO:
        try:
            # Try to find YOLO model in the project
            yolo_paths = [
                "segmentation/onnx/yolo11n_seg_v2.onnx",
                "segmentation/models/yolo11n_seg_v2.onnx",
                "yolo11n_seg_v2.onnx"
            ]
            for yolo_path in yolo_paths:
                if Path(yolo_path).exists():
                    # Explicitly specify task=segment for segmentation models
                    yolo_model = YOLO(yolo_path, task='segment')
                    print(f"Loaded YOLO segmentation model from: {yolo_path}")
                    break
        except Exception as e:
            print(f"Warning: Failed to load YOLO model: {e}")
    
    # Load trajectory
    traj_file = dataset_path / "CameraTrajectory.txt"
    if not traj_file.exists():
        print(f"Error: CameraTrajectory.txt not found")
        return False
    
    poses = load_trajectory(traj_file)
    print(f"Loaded {len(poses)} poses")
    
    # Load associations
    assoc_file = dataset_path / "associations.txt"
    if not assoc_file.exists():
        print(f"Error: associations.txt not found")
        return False
    
    associations = []
    with open(assoc_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 4:
                rgb_ts = float(parts[0])
                rgb_path = parts[1]
                depth_ts = float(parts[2])
                depth_path = parts[3]
                associations.append((rgb_ts, rgb_path, depth_ts, depth_path))
    
    print(f"Loaded {len(associations)} associations")
    
    # Select frames to process
    frame_indices = np.linspace(0, len(associations)-1, min(max_frames, len(associations)), dtype=int)
    
    all_points = []
    all_colors = []
    
    for idx in frame_indices:
        rgb_ts, rgb_path, depth_ts, depth_path = associations[idx]
        
        # Find closest pose
        closest_ts = min(poses.keys(), key=lambda t: abs(t - rgb_ts))
        pose = poses[closest_ts]
        
        # Load depth image
        depth_file = dataset_path / depth_path
        if not depth_file.exists():
            continue
        
        depth_img = np.array(Image.open(depth_file))
        
        # Load RGB image
        rgb_file = dataset_path / rgb_path
        rgb_img = None
        if rgb_file.exists():
            rgb_img = np.array(Image.open(rgb_file))
            if rgb_img.ndim == 3:
                rgb_img = rgb_img[:, :, :3]  # Keep only RGB channels
        
        # Generate static mask using YOLO
        static_mask = None
        if rgb_img is not None and yolo_model is not None:
            static_mask = generate_static_mask(rgb_img, yolo_model)
        
        # Convert to point cloud
        points, colors = depth_to_pointcloud(depth_img, rgb_img, fx, fy, cx, cy, depth_factor, static_mask)
        
        if len(points) == 0:
            continue
        
        # Transform points to world coordinates
        R = quaternion_to_rotation_matrix(pose['qx'], pose['qy'], pose['qz'], pose['qw'])
        t = np.array([pose['tx'], pose['ty'], pose['tz']])
        
        # Apply transformation: P_world = R * P_camera + t
        points_world = (R @ points.T).T + t
        
        # Downsample
        if downsample > 1:
            indices = np.random.choice(len(points_world), len(points_world)//downsample, replace=False)
            points_world = points_world[indices]
            if colors is not None:
                colors = colors[indices]
        
        all_points.append(points_world)
        if colors is not None:
            all_colors.append(colors)
        
        static_info = f" (static mask applied)" if static_mask is not None else ""
        print(f"Processed frame {idx}/{len(associations)}: {len(points_world)} points{static_info}")
    
    if not all_points:
        print("Error: No points generated")
        return False
    
    # Combine all points
    all_points = np.vstack(all_points)
    all_colors = np.vstack(all_colors) if all_colors else None
    
    print(f"Total points: {len(all_points)}")
    
    # Write PLY file
    output_ply = Path(output_ply)
    output_ply.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_ply, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(all_points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        if all_colors is not None:
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
        f.write("end_header\n")
        
        for i in range(len(all_points)):
            x, y, z = all_points[i]
            f.write(f"{x:.4f} {y:.4f} {z:.4f}")
            if all_colors is not None:
                r, g, b = all_colors[i].astype(int)
                f.write(f" {r} {g} {b}")
            f.write("\n")
    
    print(f"PLY file saved to: {output_ply}")
    print(f"Total points: {len(all_points)}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_pointcloud.py <dataset_name> [--no-segmentation]")
        print("Example: python generate_pointcloud.py rgbd_dataset_freiburg3_walking_halfsphere")
        sys.exit(1)
    
    dataset_name = sys.argv[1]
    use_segmentation = "--no-segmentation" not in sys.argv
    
    dataset_path = f"datasets/TUM/{dataset_name}"
    output_ply = f"datasets/TUM/{dataset_name}/maps/static_map.ply"
    
    print(f"=== Generate Point Cloud ===")
    print(f"Dataset: {dataset_name}")
    print(f"Output: {output_ply}")
    print(f"Semantic Segmentation: {'Enabled' if use_segmentation else 'Disabled'}")
    
    success = generate_ply(dataset_path, output_ply, use_segmentation=use_segmentation)
    
    if success:
        print("\n=== Success ===")
        print("Point cloud generated successfully!")
    else:
        print("\n=== Failed ===")
        print("Failed to generate point cloud")
