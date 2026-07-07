"""Loss 工厂函数 — 从配置字典构建 loss."""

import torch.nn as nn

from .composite import CompositeLoss
from .epe import EPELoss
from .smooth_l1 import SmoothL1Loss

_BUILDERS = {
    "smooth_l1": lambda cfg: SmoothL1Loss(**cfg.get("kwargs", {})),
    "epe": lambda cfg: EPELoss(**cfg.get("kwargs", {})),
    "composite": lambda cfg: CompositeLoss(
        items=cfg.get("items", [{"name": "smooth_l1", "weight": 1.0}]),
        mask_invalid=cfg.get("mask_invalid", True),
    ),
}


def build_loss(cfg: dict) -> nn.Module:
    """从配置构建损失函数.

    cfg 格式:
        {name: "composite", items: [{name: "smooth_l1", weight: 1.0}, ...]}
    """
    name = cfg["name"]
    if name not in _BUILDERS:
        raise KeyError(f"未知 loss: {name}，可选: {list(_BUILDERS.keys())}")
    return _BUILDERS[name](cfg)
