"""Smooth L1 Loss — PSMNet 标配."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SmoothL1Loss(nn.Module):
    """平滑 L1 视差损失.

    Args:
        beta: smooth L1 的转折点 (默认 1.0)
        mask_invalid: 是否忽略视差≤0的像素
    """

    def __init__(self, beta: float = 1.0, mask_invalid: bool = True):
        super().__init__()
        self.beta = beta
        self.mask_invalid = mask_invalid

    def forward(self, pred, target):
        """前向传播.

        Args:
            pred:   [B, 1, H, W] 预测视差
            target: [B, 1, H, W] 真实视差

        Returns:
            scalar loss
        """
        mask = torch.ones_like(target, dtype=torch.bool)
        if self.mask_invalid:
            mask = target > 0

        loss = F.smooth_l1_loss(pred[mask], target[mask], beta=self.beta, reduction="mean")
        return loss
