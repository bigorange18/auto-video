"""LightningModule — 封装模型 + Loss + 优化器 + 指标."""

import torch
import pytorch_lightning as pl

from .losses import build_loss
from .metrics import compute_metrics
from .models import get_model


class StereoModule(pl.LightningModule):
    """双目训练 LightningModule.

    配置格式 (YAML):
        model:
          name: placeholder    # backbone 名称（暂时占位）
          max_disp: 192

        loss:
          name: composite
          items:
            - {name: smooth_l1, weight: 1.0}

        optimizer:
          name: adam
          lr: 0.001
          weight_decay: 0.0001

        scheduler:
          name: cosine
          t_max: 100
    """

    def __init__(self, cfg: dict):
        super().__init__()
        self.save_hyperparameters()
        self.cfg = cfg

        # 模型
        model_cfg = cfg.get("model", {})
        model_name = model_cfg.get("name", "placeholder")
        model_kwargs = {k: v for k, v in model_cfg.items() if k != "name"}

        self.model = get_model(model_name, **model_kwargs)

        # Loss
        self.criterion = build_loss(cfg.get("loss", {"name": "smooth_l1"}))

        self.opt_cfg = cfg.get("optimizer", {"name": "adam", "lr": 1e-3})
        self.sched_cfg = cfg.get("scheduler", {})

    def forward(self, left, right):
        return self.model(left, right)

    def training_step(self, batch, batch_idx):
        left, right, disp_gt = batch["left"], batch["right"], batch["disparity"]
        output = self(left, right)

        pred = output["disparity"] if isinstance(output, dict) else output
        loss, detail = self.criterion(pred, disp_gt)

        self.log("train/loss", loss, prog_bar=True)
        for k, v in detail.items():
            self.log(f"train/{k}", v)

        # 每 500 步记一次 EPE
        if batch_idx % 500 == 0:
            metrics = compute_metrics(pred, disp_gt)
            for k, v in metrics.items():
                if not (isinstance(v, float) and v != v):  # skip NaN
                    self.log(f"train/{k}", v)

        return loss

    def validation_step(self, batch, batch_idx):
        left, right, disp_gt = batch["left"], batch["right"], batch["disparity"]
        output = self(left, right)

        pred = output["disparity"] if isinstance(output, dict) else output
        loss, _ = self.criterion(pred, disp_gt)

        metrics = compute_metrics(pred, disp_gt)
        metrics["val_loss"] = loss

        for k, v in metrics.items():
            if not (isinstance(v, float) and v != v):
                self.log(f"val/{k}", v, sync_dist=True)

        return metrics

    def configure_optimizers(self):
        opt_name = self.opt_cfg.get("name", "adam").lower()
        lr = self.opt_cfg.get("lr", 1e-3)
        wd = self.opt_cfg.get("weight_decay", 0.0)

        if opt_name == "adam":
            opt = torch.optim.Adam(self.parameters(), lr=lr, weight_decay=wd)
        elif opt_name == "adamw":
            opt = torch.optim.AdamW(self.parameters(), lr=lr, weight_decay=wd)
        elif opt_name == "sgd":
            opt = torch.optim.SGD(self.parameters(), lr=lr, momentum=0.9, weight_decay=wd)
        else:
            raise ValueError(f"未知优化器: {opt_name}")

        if not self.sched_cfg:
            return opt

        sched_name = self.sched_cfg.get("name", "cosine")
        if sched_name == "cosine":
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                opt, T_max=self.sched_cfg.get("t_max", 100))
        elif sched_name == "step":
            scheduler = torch.optim.lr_scheduler.StepLR(
                opt, step_size=self.sched_cfg.get("step_size", 30),
                gamma=self.sched_cfg.get("gamma", 0.1))
        elif sched_name == "plateau":
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                opt, patience=self.sched_cfg.get("patience", 10))
            return {"optimizer": opt, "lr_scheduler": {"scheduler": scheduler, "monitor": "val/epe"}}
        else:
            raise ValueError(f"未知 scheduler: {sched_name}")

        return {"optimizer": opt, "lr_scheduler": scheduler}
