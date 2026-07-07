"""LightningDataModule — 封装数据集加载."""

import pytorch_lightning as pl
from torch.utils.data import DataLoader

from .data import get_dataset
from .data.transforms import StereoAugmentation


class StereoDataModule(pl.LightningDataModule):
    """双目数据 LightningDataModule.

    配置格式 (YAML):
        data:
          name: kitti2015
          root: /data/kitti2015
          image_size: [256, 512]
          batch_size: 4
          num_workers: 4
    """

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.image_size = tuple(cfg.get("image_size", (256, 512)))
        self.batch_size = cfg.get("batch_size", 4)
        self.num_workers = cfg.get("num_workers", 4)
        self.root = cfg["root"]
        self.dataset_name = cfg.get("name", "kitti2015")

    def setup(self, stage=None):
        train_transform = StereoAugmentation(
            image_size=self.image_size,
            color_jitter=(0.2, 0.2, 0.2, 0.05),
            random_horizontal_flip=0.5,
        )

        DatasetCls = get_dataset(self.dataset_name)

        if stage in ("fit", None):
            self.train_dataset = DatasetCls(
                root=self.root, split="train",
                transform=train_transform, crop_size=None,
            )
            # 验证集：用验证变换，不翻不裁
            self.val_dataset = DatasetCls(
                root=self.root, split="train",
                transform=StereoAugmentation(image_size=self.image_size, color_jitter=(0, 0, 0, 0),
                                             random_horizontal_flip=0),
                crop_size=None,
            )
        elif stage in ("validate", "test"):
            self.val_dataset = DatasetCls(
                root=self.root, split="train",
                transform=StereoAugmentation(image_size=self.image_size, color_jitter=(0, 0, 0, 0),
                                             random_horizontal_flip=0),
                crop_size=None,
            )

    def train_dataloader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size,
                          shuffle=True, num_workers=self.num_workers,
                          pin_memory=True, drop_last=True)

    def val_dataloader(self):
        return DataLoader(self.val_dataset, batch_size=self.batch_size,
                          shuffle=False, num_workers=self.num_workers,
                          pin_memory=True)
