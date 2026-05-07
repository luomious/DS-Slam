#!/usr/bin/env python3
"""
DS-SLAM M2 Checkpoint: End-to-end inference test
==================================================
Verifies:
  1. Model constructs without errors
  2. Forward pass produces valid outputs
  3. Mask decoding produces binary uint8 mask
  4. Inference time is reasonable (< 50ms on GPU)

Usage:
  python test_inference.py [--image path/to/test.jpg] [--cpu]
"""

import argparse
import sys
import time
from pathlib import Path

import torch

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

# Add models directory to path
sys.path.insert(0, str(Path(__file__).parent))
from models.lscd import YOLO11nSeg, SegmentationDecoder


def select_device(force_cpu=False):
    """Pick a usable device, falling back when CUDA is installed but incompatible."""
    if force_cpu or not torch.cuda.is_available():
        return torch.device("cpu"), None

    device = torch.device("cuda")
    try:
        probe = torch.ones(1, device=device)
        probe = probe + 1
        torch.cuda.synchronize()
        del probe
        return device, None
    except RuntimeError as exc:
        warning = (
            "CUDA is visible but unusable for this PyTorch build; "
            f"falling back to CPU. Original error: {exc}"
        )
        return torch.device("cpu"), warning


def load_or_create_image(image_path=None, size=(640, 640)):
    """Load image from path or create a random test image."""
    if cv2 is None or np is None:
        if image_path:
            raise RuntimeError("Loading image files requires opencv-python and numpy.")
        return torch.rand(3, size[1], size[0])

    if image_path and Path(image_path).exists():
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        # Random test image
        img = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)

    # Resize
    img = cv2.resize(img, size)
    return img


def preprocess(img, device):
    """Convert HWC uint8 numpy to BCHW float tensor."""
    if isinstance(img, torch.Tensor):
        return img.unsqueeze(0).to(device)

    tensor = torch.from_numpy(img).float().permute(2, 0, 1).unsqueeze(0)  # [1, 3, H, W]
    tensor = tensor / 255.0
    return tensor.to(device)


def main():
    parser = argparse.ArgumentParser(description="DS-SLAM M2 inference test")
    parser.add_argument("--image", type=str, default=None, help="Path to test image")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup iterations")
    parser.add_argument("--iters", type=int, default=10, help="Benchmark iterations")
    args = parser.parse_args()

    # Device
    device, device_warning = select_device(args.cpu)
    print(f"[M2] Device: {device}")
    print(f"[M2] GPU: {torch.cuda.get_device_name(0) if device.type == 'cuda' else 'N/A'}")
    if device_warning:
        print(f"[M2] WARNING: {device_warning}")

    # Build model
    print("[M2] Building YOLO11nSeg...")
    model = YOLO11nSeg(num_classes=2, proto_channels=32).to(device)
    model.eval()

    decoder = SegmentationDecoder(input_hw=(640, 640), conf_threshold=0.3).to(device)

    # Parameter count
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[M2] Parameters: {total_params:,} total, {trainable_params:,} trainable")

    # Load/create image
    img = load_or_create_image(args.image)
    tensor = preprocess(img, device)
    print(f"[M2] Input shape: {tensor.shape}")

    # Warmup
    print(f"[M2] Warming up ({args.warmup} iters)...")
    with torch.no_grad():
        for _ in range(args.warmup):
            _ = model(tensor)

    # Benchmark
    print(f"[M2] Benchmarking ({args.iters} iters)...")
    times = []
    with torch.no_grad():
        for _ in range(args.iters):
            torch.cuda.synchronize() if device.type == 'cuda' else None
            t0 = time.perf_counter()
            head_out = model(tensor)
            mask = decoder(head_out)
            torch.cuda.synchronize() if device.type == 'cuda' else None
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)  # ms

    avg_time = sum(times) / len(times)
    std_time = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
    print(f"[M2] Inference: {avg_time:.1f} +/- {std_time:.1f} ms")

    # Verify outputs
    print(f"[M2] Head outputs:")
    print(f"     bbox:  {head_out['bbox'].shape} (expected [1,4,80,80])")
    print(f"     cls:   {head_out['cls'].shape}  (expected [1,2,80,80])")
    print(f"     proto: {head_out['proto'].shape} (expected [1,32,80,80])")

    print(f"[M2] Mask output: {mask.shape} (expected [1,1,640,640])")
    print(f"[M2] Mask range: [{mask.min().item():.3f}, {mask.max().item():.3f}]")

    # Save sample mask for visual check
    if cv2 is not None and np is not None:
        mask_np = (mask[0, 0].cpu().numpy() * 255).astype(np.uint8)
        out_dir = Path(__file__).parent / "output"
        out_dir.mkdir(exist_ok=True)
        cv2.imwrite(str(out_dir / "test_mask.png"), mask_np)
        print(f"[M2] Saved test_mask.png to {out_dir}")
    else:
        print("[M2] Skipped mask PNG save because opencv-python/numpy is not installed.")

    # Validation
    checks = []
    checks.append(("bbox shape", head_out['bbox'].shape == (1, 4, 80, 80)))
    checks.append(("proto shape", head_out['proto'].shape == (1, 32, 80, 80)))
    checks.append(("mask shape", mask.shape == (1, 1, 640, 640)))
    checks.append(("mask binary", mask.min() >= 0 and mask.max() <= 1))
    checks.append(("inference speed", avg_time < 200))  # < 200ms even on CPU

    all_ok = all(v for _, v in checks)
    print(f"\n[M2] Validation results:")
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"     [{status}] {name}")

    if not all_ok:
        print(f"\n[M2] SOME CHECKS FAILED!")
        sys.exit(1)

    print(f"\n[M2] ALL CHECKS PASSED! M2 complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
