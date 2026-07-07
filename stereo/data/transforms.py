"""数据增强 — 双目图像同步变换 (纯 torchvision，无 opencv)."""

import random

import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF


class StereoAugmentation:
    """双目同步数据增强.

    Args:
        image_size: (H, W) 输出尺寸
        color_jitter: [brightness, contrast, saturation, hue] 抖动强度
        random_horizontal_flip: 水平翻转概率
    """

    def __init__(
        self,
        image_size=(256, 512),
        color_jitter=(0.2, 0.2, 0.2, 0.05),
        random_horizontal_flip=0.5,
    ):
        self.image_size = image_size
        self.jitter = color_jitter
        self.flip_prob = random_horizontal_flip

    def __call__(self, sample):
        import numpy as np

        left = sample["left"]      # np (H,W,3) uint8
        right = sample["right"]
        disp = sample.get("disparity")

        # to tensor
        left_t = TF.to_tensor(left)     # [3,H,W] float
        right_t = TF.to_tensor(right)
        if disp is not None:
            disp_t = torch.from_numpy(disp).unsqueeze(0)  # [1,H,W]

        # resize
        left_t = TF.resize(left_t, self.image_size, interpolation=TF.InterpolationMode.BILINEAR)
        right_t = TF.resize(right_t, self.image_size, interpolation=TF.InterpolationMode.BILINEAR)
        if disp is not None:
            s_h, s_w = self.image_size[0] / disp.shape[0], self.image_size[1] / disp.shape[1]
            disp_t = TF.resize(disp_t, self.image_size, interpolation=TF.InterpolationMode.BILINEAR) * s_w

        # 颜色抖动（左右独立）
        b, c, s, h = self.jitter
        left_t = TF.adjust_brightness(left_t, 1.0 + random.uniform(-b, b))
        left_t = TF.adjust_contrast(left_t, 1.0 + random.uniform(-c, c))
        if s > 0:
            left_t = TF.adjust_saturation(left_t, 1.0 + random.uniform(-s, s))
        if h > 0:
            left_t = TF.adjust_hue(left_t, random.uniform(-h, h))
        right_t = TF.adjust_brightness(right_t, 1.0 + random.uniform(-b, b))
        right_t = TF.adjust_contrast(right_t, 1.0 + random.uniform(-c, c))
        if s > 0:
            right_t = TF.adjust_saturation(right_t, 1.0 + random.uniform(-s, s))
        if h > 0:
            right_t = TF.adjust_hue(right_t, random.uniform(-h, h))

        # 水平翻转
        if random.random() < self.flip_prob:
            left_t = TF.hflip(left_t)
            right_t = TF.hflip(right_t)
            if disp is not None:
                disp_t = TF.hflip(disp_t)

        out = {"left": left_t.clamp(0, 1), "right": right_t.clamp(0, 1)}
        if disp is not None:
            out["disparity"] = disp_t
        out["stem"] = sample.get("stem", "")
        return out
