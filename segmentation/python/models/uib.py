#!/usr/bin/env python3
"""
UIB (Universal Inverted Bottleneck) Module
============================================
DS-SLAM Paper Chapter 3: Lightweight Semantic Segmentation Network — Backbone

Core idea: separable convolutions + multiple dilation rates, adapted for MobileNetV4-style backbone.

Parameters:
  - expand_ratio: expansion ratio (default 4), hidden_dim = in_channels * expand_ratio
  - dw_kernel_size: depthwise kernel size (3/5/7)
  - pw_kernel_size: pointwise kernel size (always 1)
  - use_residual: apply residual when stride==1 and in_channels==out_channels
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class UIB(nn.Module):
    """Universal Inverted Bottleneck — Paper Section 3.2

    Structure:
      input -> PW expand (1x1) -> BN + ReLU6
            -> DW conv (3x3/5x5/7x7, dilated) -> BN + ReLU6
            -> PW project (1x1) -> BN
            -> [+ residual if shape matches]

    Args:
        in_channels:   input channels
        out_channels:  output channels
        expand_ratio:  hidden layer expansion ratio (default: 4)
        dw_kernel_size: depthwise kernel size (default: 3)
        stride:        convolution stride (default: 1)
        dilation:      dilation rate (default: 1)
        act:           activation function (default: nn.ReLU6)
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        expand_ratio: int = 4,
        dw_kernel_size: int = 3,
        stride: int = 1,
        dilation: int = 1,
        act: nn.Module = None,
    ):
        super().__init__()
        self.stride = stride
        self.use_residual = (stride == 1 and in_channels == out_channels)

        hidden_dim = int(in_channels * expand_ratio)

        layers = []

        # 1. Pointwise expansion (1x1)
        if expand_ratio != 1:
            layers.extend([
                nn.Conv2d(in_channels, hidden_dim, 1, bias=False),
                nn.BatchNorm2d(hidden_dim),
                act if act else nn.ReLU6(inplace=True),
            ])

        # 2. Depthwise convolution with dilation
        padding = (dw_kernel_size + (dw_kernel_size - 1) * (dilation - 1)) // 2
        layers.extend([
            nn.Conv2d(
                hidden_dim, hidden_dim, dw_kernel_size,
                stride=stride, padding=padding,
                dilation=dilation, groups=hidden_dim, bias=False
            ),
            nn.BatchNorm2d(hidden_dim),
            act if act else nn.ReLU6(inplace=True),
        ])

        # 3. Pointwise projection (1x1)
        layers.extend([
            nn.Conv2d(hidden_dim, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
        ])

        self.block = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.block(x)
        if self.use_residual:
            out = out + x
        return out


class UIBStage(nn.Module):
    """UIB Stage — stacks multiple UIB blocks to form one backbone stage.

    Used to build MobileNetV4-style multi-stage backbone.
    Each stage consists of multiple UIB blocks; the first block can downsample.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_blocks: int,
        expand_ratio: int = 4,
        dw_kernel_size: int = 3,
        stride: int = 1,
    ):
        super().__init__()
        layers = []

        # First block: can downsample with stride > 1
        layers.append(UIB(
            in_channels, out_channels,
            expand_ratio=expand_ratio,
            dw_kernel_size=dw_kernel_size,
            stride=stride,
        ))

        # Remaining blocks: stride=1, in_channels==out_channels
        for _ in range(num_blocks - 1):
            layers.append(UIB(
                out_channels, out_channels,
                expand_ratio=expand_ratio,
                dw_kernel_size=dw_kernel_size,
            ))

        self.stage = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.stage(x)
