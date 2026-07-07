"""立体匹配评估指标 — EPE, D1-all, RMSE."""

import torch


@torch.no_grad()
def compute_metrics(pred, target, mask=None):
    """计算立体匹配常用指标.

    Args:
        pred:   [B, 1, H, W] 预测视差
        target: [B, 1, H, W] 真实视差
        mask:   [B, 1, H, W] bool，有效像素 (None = target>0)

    Returns:
        dict: {"epe", "d1_all", "rmse", "bad_1px", "bad_3px", "valid_pixels"}
    """
    if mask is None:
        mask = target > 0

    valid = mask.sum().item()
    if valid == 0:
        return {"epe": float("nan"), "d1_all": float("nan"),
                "rmse": float("nan"), "bad_1px": float("nan"),
                "bad_3px": float("nan"), "valid_pixels": 0}

    diff = torch.abs(pred - target)

    epe = diff[mask].mean().item()
    rmse = torch.sqrt((diff[mask] ** 2).mean()).item()

    # D1-all: 误差 > max(3px, 5% of gt) 的像素占比
    threshold = torch.maximum(torch.tensor(3.0, device=target.device),
                              target[mask] * 0.05)
    bad = (diff[mask] > threshold).float().mean().item()

    bad_1px = (diff[mask] > 1).float().mean().item()
    bad_3px = (diff[mask] > 3).float().mean().item()

    return {
        "epe": epe,
        "d1_all": bad,
        "rmse": rmse,
        "bad_1px": bad_1px,
        "bad_3px": bad_3px,
        "valid_pixels": int(valid),
    }
