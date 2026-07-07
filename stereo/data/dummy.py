"""Dummy 数据集 — 用于验证训练框架可运行，无需真实数据."""

import numpy as np
import torch
from torch.utils.data import Dataset


class DummyStereoDataset(Dataset):
    """生成随机双目图 + 恒定视差 GT，用于快速测试框架。

    Args:
        size: 数据集样本数
        image_size: (H, W)
    """

    def __init__(self, size: int = 160, image_size: tuple = (256, 512),
                 root: str = None, split: str = "train", transform=None, crop_size=None):
        self.size = size
        self.image_size = image_size

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        h, w = self.image_size
        # 随机噪声作为"图像"
        left = np.random.rand(h, w, 3).astype(np.float32)
        right = np.random.rand(h, w, 3).astype(np.float32)
        # 模拟一个简单的视差图
        disp = np.full((h, w), 10.0 + np.random.rand(h, w) * 5, dtype=np.float32)

        return {
            "left": torch.from_numpy(left).permute(2, 0, 1),
            "right": torch.from_numpy(right).permute(2, 0, 1),
            "disparity": torch.from_numpy(disp).unsqueeze(0),
            "stem": f"dummy_{idx:06d}",
        }
