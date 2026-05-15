import urllib.request
import json

# Test HTTP API
response = urllib.request.urlopen('http://localhost:8000/api/trajectory')
data = json.loads(response.read())
print('=== HTTP API Test ===')
print(f'Camera poses: {data["camera_count"]}')
print(f'Keyframe poses: {data["keyframe_count"]}')
print(f'First camera pos: {data["camera_trajectory"][0]["pos"]}')
print(f'Last camera pos: {data["camera_trajectory"][-1]["pos"]}')
