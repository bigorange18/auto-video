"""组合损失函数 — 支持多个 loss 加权求和，可选多尺度监督."""

import torch.nn as nn

from .epe import EPELoss
from .smooth_l1 import SmoothL1Loss

_LOSS_MAP = {
    "smooth_l1": SmoothL1Loss,
    "epe": EPELoss,
}


class CompositeLoss(nn.Module):
    """组合多个 Loss，加权求和.

    配置示例:
        loss:
          name: composite
          items:
            - {name: smooth_l1, weight: 1.0}
            - {name: epe, weight: 0.3}

    Args:
        items: list of dict，每个包含 {name, weight, kwargs(可选)}
        mask_invalid: 全局忽略无效视差
    """

    def __init__(self, items: list[dict], mask_invalid: bool = True):
        super().__init__()
        self.losses = nn.ModuleList()
        self.weights = []

        for item in items:
            name = item["name"]
            w = item.get("weight", 1.0)
            kw = item.get("kwargs", {})
            kw.setdefault("mask_invalid", mask_invalid)

            if name not in _LOSS_MAP:
                raise KeyError(f"未知 loss: {name}，可选: {list(_LOSS_MAP.keys())}")
            self.losses.append(_LOSS_MAP[name](**kw))
            self.weights.append(w)

    def forward(self, pred, target):
        """计算加权总 loss.

        Args:
            pred:   [B, 1, H, W] 或 list of tensors (多尺度)
            target: [B, 1, H, W]

        Returns:
            (total_loss, dict of per-loss values)
        """
        total = 0.0
        details = {}

        # 多尺度支持：如果 pred 是 list，每层都算 loss
        preds = pred if isinstance(pred, (list, tuple)) else [pred]

        for loss_fn, w in zip(self.losses, self.weights):
            name = type(loss_fn).__name__
            scaled_weight = w / len(preds)
            val = sum(loss_fn(p, target) * scaled_weight for p in preds)
            total = total + val
            details[name] = val.item()

        return total, details
