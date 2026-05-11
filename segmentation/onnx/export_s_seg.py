import os, sys
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_load(*args, **kwargs)
torch.load = _patched_load

from ultralytics import YOLO
m = YOLO('yolo11s-seg.pt')
print('Model loaded, exporting ONNX...')
result = m.export(format='onnx', imgsz=640, simplify=True)
print(f'Export done: {result}')
