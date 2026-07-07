"""EPE (End-Point Error) Loss — 预测与GT的L1距离."""

import torch
import torch.nn as nn


class EPELoss(nn.Module):
    """EPE 损失函数.

    Args:
        mask_invalid: 忽略视差≤0的像素
    """

    def __init__(self, mask_invalid: bool = True):
        super().__init__()
        self.mask_invalid = mask_invalid

    def forward(self, pred, target):
        mask = torch.ones_like(target, dtype=torch.bool)
        if self.mask_invalid:
            mask = target > 0

        diff = torch.abs(pred - target)
        return diff[mask].mean()
