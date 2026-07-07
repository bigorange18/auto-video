"""占位模型 — 用于测试框架流程，后续替换为真实 backbone."""

import torch
import torch.nn as nn
import torch.nn.functional as F

from .registry import BaseStereoModel, register_model


@register_model("placeholder")
class PlaceholderStereo(BaseStereoModel):
    """一个最小的视差估计模型骨架，用于验证训练流程.

    实际使用时替换为 PSMNet / RAFT-Stereo / GwcNet 等。
    """

    def __init__(self, max_disp: int = 192):
        super().__init__()
        self.max_disp = max_disp

        # 简易 Siamese 特征提取
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, stride=1, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, stride=1, padding=1), nn.ReLU(),
        )

        # 代价聚合
        self.aggregator = nn.Sequential(
            nn.Conv2d(128, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 32, 3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 1, 1),
        )

    def forward(self, left, right):
        """前向传播 → 输出 {"disparity": [B,1,H,W]}.

        实现方式（简化版 cost volume）:
            对于每个视差候选 d, 将右特征图平移 d 后与左特征拼接，通过 CNN 聚合。
        """
        b = left.shape[0]

        feat_l = self.backbone(left)
        feat_r = self.backbone(right)

        # 简化：用 max_disp 个视差平面两两拼接
        d_max = min(self.max_disp // 4, feat_l.shape[-1] // 2)
        cost_list = []
        for d in range(0, d_max):
            if d == 0:
                cost_list.append(torch.cat([feat_l, feat_r], dim=1))
            else:
                r_shifted = F.pad(feat_r, (d, 0, 0, 0))[:, :, :, :feat_l.shape[-1]]
                cost_list.append(torch.cat([feat_l, r_shifted], dim=1))

        costs = torch.stack(cost_list, dim=1)  # [B, D, C, H, W]

        # 简单聚合：对每个视差平面做卷积后再 soft argmin
        b, D, C, h, w = costs.shape
        costs = costs.view(b * D, C, h, w)
        scores = self.aggregator(costs).view(b, D, h, w)
        scores = scores.squeeze(1)  # [B, D, H, W]

        # soft argmin
        disp_candidates = torch.arange(D, device=left.device, dtype=torch.float32)
        disp_candidates = disp_candidates.view(1, D, 1, 1)
        disparity = (disp_candidates * F.softmax(-scores, dim=1)).sum(dim=1, keepdim=True)

        # 上采样回输入尺寸
        disparity = F.interpolate(disparity, size=left.shape[2:], mode="bilinear", align_corners=False)

        return {"disparity": disparity}
