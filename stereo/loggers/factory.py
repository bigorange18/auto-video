"""Logger 工厂 — 从配置字典构建 TensorBoard / Wandb 日志器.

配置格式 (YAML):
    logger:
      name: tensorboard              # tensorboard | wandb
      save_dir: ./checkpoints/logs
      project: stereo                # (wandb 时必填)
      entity: null                   # (wandb 时可选)
"""

from pytorch_lightning.loggers import Logger, TensorBoardLogger


def _build_tensorboard(cfg: dict) -> Logger:
    return TensorBoardLogger(
        save_dir=cfg.get("save_dir", "./checkpoints/logs"),
        name=cfg.get("project", "stereo"),
    )


def _build_wandb(cfg: dict) -> Logger:
    from pytorch_lightning.loggers import WandbLogger

    return WandbLogger(
        save_dir=cfg.get("save_dir", "./checkpoints/logs"),
        project=cfg.get("project", "stereo"),
        name=cfg.get("run_name", None),
        entity=cfg.get("entity", None),
    )


_BUILDERS = {
    "tensorboard": _build_tensorboard,
    "wandb": _build_wandb,
}


def build_logger(cfg: dict) -> Logger:
    """从配置构建日志器.

    cfg 示例:
        {name: "tensorboard", save_dir: "./checkpoints/logs"}
        {name: "wandb", project: "stereo", entity: "my_team"}
    """
    name = cfg.get("name", "tensorboard")
    if name not in _BUILDERS:
        raise KeyError(f"未知 logger: {name}，可选: {list(_BUILDERS.keys())}")
    return _BUILDERS[name](cfg)
