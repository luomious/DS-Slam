#!/usr/bin/env python3
"""Simulate continuous frame data push to test real-time visualization."""

import json
import time
import requests
import base64
import numpy as np

def generate_test_frame(frame_num):
    """Generate a test frame with moving features."""
    # Create a gradient image that changes
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    offset = frame_num * 5
    
    for y in range(480):
        for x in range(640):
            arr[y, x] = [
                (x + offset) % 256,
                (y + offset * 2) % 256,
                (x + y + offset) % 256
            ]
    
    import io
    from PIL import Image
    img = Image.fromarray(arr)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=70)
    base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Create mask with moving rectangle
    mask_arr = np.zeros((480, 640, 3), dtype=np.uint8)
    rect_x = (100 + frame_num * 3) % 300
    rect_y = (100 + frame_num * 2) % 200
    mask_arr[rect_y:rect_y+150, rect_x:rect_x+200] = [255, 0, 0]
    
    mask_img = Image.fromarray(mask_arr)
    mask_buffer = io.BytesIO()
    mask_img.save(mask_buffer, format='PNG')
    base64_mask = base64.b64encode(mask_buffer.getvalue()).decode('utf-8')
    
    # Generate moving features
    features = []
    for i in range(30):
        features.append({
            'x': (100 + i * 20 + frame_num * 2) % 640,
            'y': (100 + i * 15 + frame_num) % 480
        })
    
    return {
        'type': 'frame_update',
        'frame_number': frame_num,
        'keyframe_count': frame_num // 10,
        'map_points': 2000 + frame_num * 10,
        'image_base64': base64_image,
        'mask_base64': base64_mask,
        'dynamic_coverage': 10.0 + (frame_num % 20) * 0.5,
        'features': features
    }

def main():
    url = "http://localhost:8000/api/frame"
    print("Starting continuous frame push simulation...")
    print("Press Ctrl+C to stop")
    
    frame_num = 0
    try:
        while True:
            frame = generate_test_frame(frame_num)
            
            try:
                response = requests.post(url, json=frame)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Frame {frame_num}: {data['clients']} clients, {data['buffered']} buffered")
                else:
                    print(f"Frame {frame_num}: Error {response.status_code}")
            except Exception as e:
                print(f"Frame {frame_num}: Exception {e}")
            
            frame_num += 1
            time.sleep(0.1)  # ~10 FPS
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()