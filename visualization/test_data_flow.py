"""Test script to simulate SlamVisualizer data flow without running the C++ exe."""
import cv2
import numpy as np
import requests
import base64
import json
import time
import os
import glob

BACKEND_URL = "http://127.0.0.1:8000"
DATASET_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "datasets", "tum", "rgbd_dataset_freiburg1_xyz"
)

def load_test_images():
    """Load a few RGB images from the dataset."""
    rgb_dir = os.path.join(DATASET_DIR, "rgb")
    depth_dir = os.path.join(DATASET_DIR, "depth")
    
    rgb_files = sorted(glob.glob(os.path.join(rgb_dir, "*.png")))[:5]
    depth_files = sorted(glob.glob(os.path.join(depth_dir, "*.png")))[:5]
    
    images = []
    for rgb_path, depth_path in zip(rgb_files, depth_files):
        rgb = cv2.imread(rgb_path)
        depth = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        if rgb is not None and depth is not None:
            images.append((rgb, depth))
    return images

def encode_image(image, format=".jpg"):
    """Encode image to base64 (same as SlamVisualizer::encodeBase64)."""
    _, buffer = cv2.imencode(format, image)
    return base64.b64encode(buffer).decode("utf-8")

def send_frame(frame_number, rgb_image, mask_image=None):
    """Send frame data to backend (simulates SlamVisualizer::SendFrame)."""
    rgb_base64 = encode_image(rgb_image)
    mask_base64 = encode_image(mask_image) if mask_image is not None else ""
    
    # Create a dummy mask (all ones = no dynamic objects)
    if mask_image is None:
        mask_image = np.ones((rgb_image.shape[0], rgb_image.shape[1]), dtype=np.uint8) * 255
    
    payload = {
        "frame_number": frame_number,
        "keyframe_count": frame_number // 10 + 1,
        "map_points": frame_number * 50 + 100,
        "rgb_base64": rgb_base64,
        "mask_base64": encode_image(mask_image),
        "dynamic_coverage": 0.0,
        "timestamp": time.time(),
        "pose": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ]
    }
    
    response = requests.post(f"{BACKEND_URL}/api/frame", json=payload)
    return response.status_code, response.text

def main():
    print("=" * 60)
    print("DS-SLAM M6 Data Flow Test (Python Simulation)")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n[1] Backend health check...")
    try:
        resp = requests.get(f"{BACKEND_URL}/")
        print(f"    Status: {resp.status_code} OK")
    except Exception as e:
        print(f"    FAILED: {e}")
        return
    
    # Test 2: Load dataset images
    print("\n[2] Loading test images from dataset...")
    images = load_test_images()
    print(f"    Loaded {len(images)} image pairs")
    
    if not images:
        print("    No images found, using synthetic data")
        for i in range(3):
            rgb = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            depth = np.random.randint(0, 65535, (480, 640), dtype=np.uint16)
            images.append((rgb, depth))
    
    # Test 3: Send frames to backend
    print("\n[3] Sending frames to backend...")
    for i, (rgb, depth) in enumerate(images):
        status, text = send_frame(i, rgb, depth)
        print(f"    Frame {i}: status={status}")
        time.sleep(0.5)
    
    # Test 4: Verify data received
    print("\n[4] Verifying data on backend...")
    try:
        resp = requests.get(f"{BACKEND_URL}/api/trajectory")
        data = resp.json()
        print(f"    Trajectory points: {len(data.get('trajectory', []))}")
    except Exception as e:
        print(f"    FAILED: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete! Open http://localhost:8000 in browser to view visualization.")
    print("=" * 60)

if __name__ == "__main__":
    main()
