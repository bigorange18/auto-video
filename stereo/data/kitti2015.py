"""KITTI 2015 Stereo Dataset 加载器 (纯 Pillow 版，无 opencv 依赖).

数据集结构期望:
  root/
    training/
      image_2/        # 左图 (png)
      image_3/        # 右图 (png)
      disp_occ_0/     # 视差图 (uint16 png, /256.0 得到 float)
    testing/
      image_2/
      image_3/
"""

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset


class KITTI2015Dataset(Dataset):
    """KITTI 2015 stereo 数据集.

    Args:
        root: 数据集根目录
        split: "train" | "test"
        transform: 数据增强 (可 None)
        crop_size: (H, W) 随机裁剪尺寸，None 表示不裁剪
    """

    def __init__(self, root: str, split: str = "train", *, transform=None, crop_size=None):
        super().__init__()
        self.root = Path(root)
        self.split = split
        self.transform = transform
        self.crop_size = crop_size

        sub = "training" if split == "train" else "testing"
        left_dir = self.root / sub / "image_2"
        if not left_dir.exists():
            raise FileNotFoundError(f"KITTI 左图目录不存在: {left_dir}")

        self.files = sorted(left_dir.glob("*_10.png"))
        if not self.files:
            raise RuntimeError(f"在 {left_dir} 中没有找到 KITTI 图像（期望 *_10.png）")

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        stem = self.files[idx].stem

        # 加载左右图 (PIL)
        left = np.array(Image.open(self.files[idx]).convert("RGB"), dtype=np.uint8)
        right_path = str(self.files[idx]).replace("image_2", "image_3")
        right = np.array(Image.open(right_path).convert("RGB"), dtype=np.uint8)

        sample = {"left": left, "right": right, "stem": stem}

        # 视差 GT
        if self.split == "train":
            disp_path = str(self.files[idx]).replace("image_2", "disp_occ_0")
            disp_img = Image.open(disp_path)
            disp = np.array(disp_img, dtype=np.uint16).astype(np.float32) / 256.0
            disp_img.close()
            sample["disparity"] = disp

        if self.transform is not None:
            # transform 返回 torch.Tensor
            return self.transform(sample)

        if self.crop_size is not None and self.split == "train":
            sample = self._random_crop(sample)

        return self._to_tensor(sample)

    def _random_crop(self, sample):
        h, w = sample["left"].shape[:2]
        ch, cw = self.crop_size
        if h < ch or w < cw:
            return sample
        top = np.random.randint(0, h - ch + 1)
        left_crop = np.random.randint(0, w - cw + 1)
        for k in ("left", "right", "disparity"):
            if k in sample and sample[k] is not None:
                sample[k] = sample[k][top:top + ch, left_crop:left_crop + cw]
        return sample

    @staticmethod
    def _to_tensor(sample):
        out = {}
        for k in ("left", "right"):
            img = sample[k].astype(np.float32) / 255.0
            out[k] = torch.from_numpy(img).permute(2, 0, 1).contiguous()
        if "disparity" in sample and sample["disparity"] is not None:
            out["disparity"] = torch.from_numpy(sample["disparity"]).unsqueeze(0)
        out["stem"] = sample.get("stem", "")
        return out
