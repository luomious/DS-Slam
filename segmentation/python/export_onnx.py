#!/usr/bin/env python3
"""
DS-SLAM M2: Export YOLO11n-seg to ONNX
========================================

Exports the trained/initialized model to ONNX format for C++ deployment (M3).

Usage:
  python export_onnx.py [--output path/to/model.onnx] [--opset 14] [--dynamic]
"""

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
from models.lscd import YOLO11nSeg


def export_onnx(
    model: torch.nn.Module,
    output_path: str,
    input_size: tuple = (640, 640),
    opset: int = 14,
    dynamic: bool = True,
):
    """Export model to ONNX format.

    Args:
        model:      YOLO11nSeg model instance
        output_path: output .onnx file path
        input_size: (H, W) of input image
        opset:      ONNX opset version
        dynamic:    use dynamic axes for batch/height/width
    """
    device = next(model.parameters()).device
    model.eval()

    # Dummy input
    dummy = torch.randn(1, 3, *input_size, device=device)

    # Dynamic axes
    dynamic_axes = None
    if dynamic:
        dynamic_axes = {
            'input': {0: 'batch', 2: 'height', 3: 'width'},
            'proto': {0: 'batch', 2: 'height', 3: 'width'},
            'bbox': {0: 'batch', 2: 'height', 3: 'width'},
            'cls': {0: 'batch', 2: 'height', 3: 'width'},
        }

    output_names = ['bbox', 'cls', 'proto']

    print(f"[EXPORT] Exporting to {output_path}")
    print(f"[EXPORT] Input:  [1, 3, {input_size[0]}, {input_size[1]}]")
    print(f"[EXPORT] Opset:  {opset}")
    print(f"[EXPORT] Dynamic axes: {dynamic}")

    # Handle torch 2.5+ API
    try:
        # New API (torch >= 2.5)
        torch.onnx.export(
            model, dummy, output_path,
            input_names=['input'],
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            opset_version=opset,
        )
    except TypeError:
        # Old API (torch < 2.5)
        torch.onnx.export(
            model, (dummy,), output_path,
            input_names=['input'],
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            opset_version=opset,
            export_params=True,
            do_constant_folding=True,
        )

    # Verify
    file_size = Path(output_path).stat().st_size
    print(f"[EXPORT] Done! File size: {file_size / 1024:.1f} KB")

    # Quick validation
    try:
        import onnx
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        print("[EXPORT] ONNX model verified: VALID")
    except ImportError:
        print("[EXPORT] Install 'onnx' package for model verification")
    except Exception as e:
        print(f"[EXPORT] ONNX verification warning: {e}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export DS-SLAM model to ONNX")
    parser.add_argument("--output", type=str, default=None,
                       help="Output ONNX path (default: ../onnx/yolo11n_seg.onnx)")
    parser.add_argument("--opset", type=int, default=14,
                       help="ONNX opset version (default: 14)")
    parser.add_argument("--cpu", action="store_true",
                       help="Use CPU model (no GPU)")
    parser.add_argument("--width", type=int, default=640,
                       help="Input width (default: 640)")
    parser.add_argument("--height", type=int, default=640,
                       help="Input height (default: 640)")
    parser.add_argument("--static", action="store_true",
                       help="Use static axes (no dynamic batch/size)")
    args = parser.parse_args()

    # Output path
    if args.output:
        output_path = args.output
    else:
        out_dir = Path(__file__).parent.parent / "onnx"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / "yolo11n_seg.onnx")

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    print(f"[EXPORT] Device: {device}")

    # Build model
    model = YOLO11nSeg(num_classes=2, proto_channels=32).to(device)
    print(f"[EXPORT] Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Export
    export_onnx(
        model, output_path,
        input_size=(args.height, args.width),
        opset=args.opset,
        dynamic=not args.static,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
