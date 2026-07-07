#!/usr/bin/env python3
"""训练入口.

用法:
    # 默认配置
    python -m stereo.train

    # 指定配置
    python -m stereo.train --config config/my_experiment.yaml

    # 覆盖参数
    python -m stereo.train data.batch_size=8 optimizer.lr=0.0005
"""

import argparse
import sys
from pathlib import Path

import pytorch_lightning as pl
import torch
import yaml
from pytorch_lightning.callbacks import LearningRateMonitor, ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger

# 确保项目根目录在 path 中
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from stereo.lit_data import StereoDataModule
from stereo.lit_module import StereoModule


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _parse_dot_path_override(base: dict, dot_path: str, value: str) -> dict:
    """解析 "a.b.c=5" 格式的参数覆盖."""
    keys = dot_path.split(".")
    d = base
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    # 类型推断
    v = value
    try:
        v = int(v)
    except ValueError:
        try:
            v = float(v)
        except ValueError:
            if v.lower() in ("true", "false"):
                v = v.lower() == "true"
    d[keys[-1]] = v
    return base


def load_config(config_path: str = None, cli_overrides: list[str] = None) -> dict:
    """加载并合并配置."""
    root = Path(__file__).resolve().parent

    if config_path:
        cfg_path = Path(config_path)
    else:
        cfg_path = root / "config" / "default.yaml"

    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # CLI 覆盖
    if cli_overrides:
        for item in cli_overrides:
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            _parse_dot_path_override(cfg, k, v)

    return cfg


def main():
    parser = argparse.ArgumentParser(description="双目立体匹配训练")
    parser.add_argument("--config", type=str, default=None, help="YAML 配置文件路径")
    parser.add_argument("overrides", nargs="*", default=[], help="参数覆盖，如 data.batch_size=8")
    args = parser.parse_args()

    cfg = load_config(args.config, args.overrides)

    # 随机种子
    pl.seed_everything(42)

    # === 数据 ===
    dm = StereoDataModule(cfg["data"])

    # === 模型 ===
    model = StereoModule(cfg)

    # === Callbacks ===
    checkpoint_cb = ModelCheckpoint(
        monitor="val/epe",
        mode="min",
        save_top_k=3,
        filename="stereo-{epoch:02d}-{val/epe:.3f}",
    )
    lr_monitor = LearningRateMonitor(logging_interval="epoch")

    # === Logger ===
    logger_cfg = cfg.get("logger", {})
    logger_name = logger_cfg.get("name", "tensorboard")
    if logger_name == "tensorboard":
        logger = TensorBoardLogger(
            save_dir=logger_cfg.get("save_dir", "./checkpoints/logs"),
            name="stereo",
        )
    else:
        logger = True  # PyTorch Lightning 默认 logger

    # === Trainer ===
    trainer_cfg = cfg.get("trainer", {})
    trainer = pl.Trainer(
        max_epochs=trainer_cfg.get("max_epochs", 100),
        accelerator=trainer_cfg.get("accelerator", "auto"),
        devices=trainer_cfg.get("devices", "auto"),
        precision=trainer_cfg.get("precision", 32),
        log_every_n_steps=trainer_cfg.get("log_every_n_steps", 50),
        check_val_every_n_epoch=trainer_cfg.get("check_val_every_n_epoch", 5),
        default_root_dir=trainer_cfg.get("default_root_dir", "./checkpoints"),
        callbacks=[checkpoint_cb, lr_monitor],
        logger=logger,
    )

    # === Go ===
    print("=" * 60)
    print("  Stereo Training Framework")
    print(f"  Dataset:  {cfg['data']['name']}")
    print(f"  Model:    {cfg['model']['name']}")
    print(f"  Loss:     {cfg['loss']['name']}")
    print(f"  Epochs:   {trainer_cfg.get('max_epochs', 100)}")
    print(f"  Devices:  {trainer_cfg.get('devices', 'auto')}")
    print("=" * 60)

    trainer.fit(model, datamodule=dm)


if __name__ == "__main__":
    main()
