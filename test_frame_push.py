#!/usr/bin/env python3
"""Test script to simulate C++ frame data push to Web."""

import json
import time
import requests
import base64
from PIL import Image
import numpy as np

def test_frame_push():
    """Test pushing frame data to the backend."""
    url = "http://localhost:8000/api/frame"
    
    # Create a test image
    img = Image.new('RGB', (640, 480), color=(128, 128, 128))
    img_bytes = img.tobytes()
    
    # Create a simple gradient
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    for y in range(480):
        for x in range(640):
            arr[y, x] = [x % 256, y % 256, (x + y) % 256]
    
    img = Image.fromarray(arr)
    
    import io
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Create mask image
    mask_arr = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a rectangle representing dynamic object
    mask_arr[100:300, 200:400] = [255, 0, 0]
    mask_img = Image.fromarray(mask_arr)
    mask_buffer = io.BytesIO()
    mask_img.save(mask_buffer, format='PNG')
    base64_mask = base64.b64encode(mask_buffer.getvalue()).decode('utf-8')
    
    # Generate test features
    features = []
    for i in range(50):
        features.append({
            'x': np.random.randint(0, 640),
            'y': np.random.randint(0, 480)
        })
    
    frame_data = {
        'type': 'frame_update',
        'frame_number': 1,
        'keyframe_count': 10,
        'map_points': 2500,
        'image_base64': base64_image,
        'mask_base64': base64_mask,
        'dynamic_coverage': 15.5,
        'features': features
    }
    
    try:
        response = requests.post(url, json=frame_data)
        print(f"Response: {response.status_code}")
        print(f"Response body: {response.text}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_websocket():
    """Test WebSocket connection."""
    import websocket
    try:
        ws = websocket.create_connection("ws://localhost:8000/ws/slam")
        print("WebSocket connected")
        
        # Send ping
        ws.send(json.dumps({'type': 'ping'}))
        response = ws.recv()
        print(f"Ping response: {response}")
        
        ws.close()
        return True
    except Exception as e:
        print(f"WebSocket error: {e}")
        return False

def main():
    print("Testing DS-SLAM Visualizer API...")
    print("=" * 50)
    
    print("\n1. Testing WebSocket connection...")
    ws_ok = test_websocket()
    
    print("\n2. Testing frame push...")
    frame_ok = test_frame_push()
    
    print("\n" + "=" * 50)
    if ws_ok and frame_ok:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")

if __name__ == "__main__":
    main()