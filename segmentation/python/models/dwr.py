#!/usr/bin/env python3
"""
DWR (Dilation-wise Residual) Module
=====================================
DS-SLAM Paper Chapter 3: Lightweight Semantic Segmentation Network — Neck

Core idea: multi-scale dilated convolutions for fusing context features.
Dilations [1, 2, 4, 8] capture receptive fields at different scales.
Output channels = 2 * input_channels (split into left/right paths).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DWR(nn.Module):
    """Dilation-wise Residual — Paper Section 3.3 (Neck)

    Structure:
      input -> 4 parallel dilated conv branches (d=1,2,4,8)
             -> concat -> 1x1 fusion
             -> residual connection (identity if in==out, else 1x1 proj)

    Args:
        in_channels:  input channels
        dilations:    list of dilation rates (default: [1, 2, 4, 8])
        reduction:    channel reduction ratio per branch (default: 2, i.e. half)
    """

    def __init__(
        self,
        in_channels: int,
        dilations: list = None,
        reduction: int = 2,
    ):
        super().__init__()
        if dilations is None:
            dilations = [1, 2, 4, 8]

        self.in_channels = in_channels
        branch_channels = in_channels // reduction

        # Parallel dilated convolution branches
        self.branches = nn.ModuleList()
        for d in dilations:
            pad = d  # 'same' padding for dilation
            self.branches.append(nn.Sequential(
                nn.Conv2d(in_channels, branch_channels, 3,
                         padding=pad, dilation=d, bias=False),
                nn.BatchNorm2d(branch_channels),
                nn.ReLU(inplace=True),
            ))

        # Fusion: concat all branches then 1x1 proj
        total = branch_channels * len(dilations)
        out_channels = in_channels * 2  # paper spec: output = 2 * input
        self.fusion = nn.Sequential(
            nn.Conv2d(total, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
        )

        # Residual projection if in != out
        self.residual = (
            nn.Conv2d(in_channels, out_channels, 1, bias=False)
            if in_channels != out_channels else None
        )

        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Parallel dilated branches
        branch_outs = []
        for branch in self.branches:
            branch_outs.append(branch(x))

        # Concat + fusion
        concat = torch.cat(branch_outs, dim=1)
        out = self.fusion(concat)

        # Residual (with projection if needed)
        residual = x if self.residual is None else self.residual(x)
        out = out + residual

        return self.act(out)


class DWRNeck(nn.Module):
    """DWR Neck — stacks DWR modules to form the feature fusion neck.

    Used between backbone stages to progressively fuse multi-scale context.
    """

    def __init__(
        self,
        channels: list,  # list of channel counts per stage
        dilations: list = None,
        reduction: int = 2,
    ):
        super().__init__()
        self.layers = nn.ModuleList()
        for i in range(len(channels) - 1):
            self.layers.append(DWR(
                channels[i], dilations, reduction
            ))

    def forward(self, features: list) -> list:
        """Process list of feature maps from backbone stages."""
        out_features = []
        for i, feat in enumerate(features[:-1]):
            out = self.layers[i](feat)
            out_features.append(out)
        return out_features
