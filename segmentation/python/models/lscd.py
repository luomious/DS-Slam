#!/usr/bin/env python3
"""
LSCD (Lightweight Shared Convolutional Detection) Head
========================================================
DS-SLAM Paper Chapter 3: Detection head with shared conv + segmentation branch.

Architecture:
  - Shared convolutions for detection + segmentation features
  - Detection branch: bbox regression (4 channels: cx, cy, w, h) + class scores
  - Segmentation branch: mask prototypes (H/8 x W/8 x 32)
  - Final mask: prototype coefficients x prototype masks

Output format (per frame):
  cv2.imwrite("mask.png", mask)  # uint8, 0=background, 255=dynamic object
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class LSCDHead(nn.Module):
    """LSCD Detection & Segmentation Head — Paper Section 3.4

    Args:
        in_channels:    input feature channels
        num_classes:    number of classes including background (default: 2 for binary)
        proto_channels: mask prototype channels (default: 32)
        proto_hw:       prototype spatial size (default: (80, 80) for 640 input)
        hidden_dim:     shared conv hidden channels (default: 128)
    """

    def __init__(
        self,
        in_channels: int,
        num_classes: int = 2,
        proto_channels: int = 32,
        proto_hw: tuple = (80, 80),
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.proto_channels = proto_channels
        self.proto_hw = proto_hw

        # --- Shared feature extraction ---
        self.shared_conv = nn.Sequential(
            nn.Conv2d(in_channels, hidden_dim, 3, padding=1, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
        )

        # --- Detection branch ---
        # Output: 4 bbox params (cx,cy,w,h) + num_classes class scores
        self.det_branch = nn.Sequential(
            nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.bbox_head = nn.Conv2d(hidden_dim, 4, 1)
        self.cls_head = nn.Conv2d(hidden_dim, num_classes, 1)

        # --- Segmentation branch ---
        self.seg_branch = nn.Sequential(
            nn.Conv2d(hidden_dim, hidden_dim, 3, padding=1, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.proto_head = nn.Conv2d(hidden_dim, proto_channels, 1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> dict:
        """Forward pass.

        Args:
            x: feature tensor [B, C, H, W]

        Returns:
            dict with keys:
                'bbox':   raw bbox predictions [B, 4, H, W]
                'cls':    class logits [B, num_classes, H, W]
                'proto':  mask prototypes [B, proto_channels, H, W]
        """
        shared = self.shared_conv(x)

        # Detection
        det_feat = self.det_branch(shared)
        bbox = self.bbox_head(det_feat)     # [B, 4, H, W]
        cls_logits = self.cls_head(det_feat) # [B, num_classes, H, W]

        # Segmentation
        seg_feat = self.seg_branch(shared)
        proto = self.proto_head(seg_feat)    # [B, proto_channels, H, W]

        return {'bbox': bbox, 'cls': cls_logits, 'proto': proto}


class YOLO11nSeg(nn.Module):
    """Improved YOLO11n-seg for DS-SLAM — Full network assembly.

    Backbone: UIB-based MobileNetV4
    Neck:     DWR multi-scale fusion
    Head:     LSCD detection + segmentation

    Architecture:
      input [B, 3, 640, 640]
        -> UIBStage1 (C3->C16, stride=2)   -> feat1 [B, 16, 320, 320]
        -> UIBStage2 (C16->C32, stride=2)  -> feat2 [B, 32, 160, 160]
        -> UIBStage3 (C32->C64, stride=2)  -> feat3 [B, 64, 80, 80]
        -> UIBStage4 (C64->C128, stride=2) -> feat4 [B, 128, 40, 40]
        -> DWR Neck fusion
        -> LSCD Head

    Args:
        num_classes:    number of classes (default: 2)
        proto_channels: number of mask prototype channels (default: 32)
    """

    def __init__(
        self,
        num_classes: int = 2,
        proto_channels: int = 32,
    ):
        super().__init__()
        from .uib import UIBStage
        from .dwr import DWR

        # Backbone
        self.stage1 = UIBStage(3, 16, num_blocks=1, expand_ratio=1, stride=2)
        self.stage2 = UIBStage(16, 32, num_blocks=2, expand_ratio=4, stride=2)
        self.stage3 = UIBStage(32, 64, num_blocks=2, expand_ratio=4, stride=2)
        self.stage4 = UIBStage(64, 128, num_blocks=2, expand_ratio=4, stride=2)

        # Neck: DWR on stage outputs
        self.dwr3 = DWR(64, dilations=[1, 2, 4, 8])
        self.dwr4 = DWR(128, dilations=[1, 2, 4, 8])

        # Fuse high-resolution context (n3) with deep semantic context (n4).
        # The head stays at H/8 so mask prototypes match the M2 checkpoint.
        self.n4_reduce = nn.Sequential(
            nn.Conv2d(256, 128, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        # Head
        self.head = LSCDHead(
            in_channels=256,  # concat(n3, upsample(reduced n4))
            num_classes=num_classes,
            proto_channels=proto_channels,
        )

    def forward(self, x: torch.Tensor) -> dict:
        # Backbone
        f1 = self.stage1(x)       # [B, 16, 320, 320]
        f2 = self.stage2(f1)      # [B, 32, 160, 160]
        f3 = self.stage3(f2)      # [B, 64, 80, 80]
        f4 = self.stage4(f3)      # [B, 128, 40, 40]

        # Neck fusion
        n3 = self.dwr3(f3)       # [B, 128, 80, 80]  (2 x 64)
        n4 = self.dwr4(f4)       # [B, 256, 40, 40]  (2 x 128)
        n4 = self.n4_reduce(n4)  # [B, 128, 40, 40]
        n4 = F.interpolate(n4, size=n3.shape[-2:], mode='bilinear', align_corners=False)
        fused = torch.cat([n3, n4], dim=1)  # [B, 256, 80, 80]

        # Head
        return self.head(fused)


class SegmentationDecoder(nn.Module):
    """Decode LSCD head output into binary semantic mask.

    Produces: cv2.imwrite-compatible uint8 mask
      - 0:   static background
      - 255: dynamic foreground object

    Args:
        input_hw:      input image size (default: (640, 640))
        conf_threshold: confidence threshold for detection (default: 0.3)
    """

    def __init__(
        self,
        input_hw: tuple = (640, 640),
        conf_threshold: float = 0.3,
    ):
        super().__init__()
        self.input_hw = input_hw
        self.conf_threshold = conf_threshold

    def forward(self, head_output: dict) -> torch.Tensor:
        """Decode head output to binary mask.

        Args:
            head_output: dict from LSCDHead.forward() with 'cls', 'proto', 'bbox'

        Returns:
            mask: [B, 1, H, W] float tensor, values in [0, 1]
        """
        cls_logits = head_output['cls']  # [B, 2, H, W]
        proto = head_output['proto']     # [B, 32, H, W]

        # Class probabilities
        cls_probs = F.softmax(cls_logits, dim=1)  # [B, 2, H, W]

        # Foreground probability (class 1 = dynamic)
        fg_prob = cls_probs[:, 1:2, :, :]  # [B, 1, H, W]

        # Binary mask: > threshold
        mask = (fg_prob > self.conf_threshold).float()

        # Resize to input resolution
        mask = F.interpolate(mask, size=self.input_hw, mode='bilinear', align_corners=False)

        # Smooth: small morphological dilation to close gaps
        mask = F.max_pool2d(mask, kernel_size=3, stride=1, padding=1)

        return mask
