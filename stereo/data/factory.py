"""数据集工厂 — 根据名称字符串返回 Dataset 类."""

from .dummy import DummyStereoDataset
from .kitti2015 import KITTI2015Dataset

_DATASETS = {
    "kitti2015": KITTI2015Dataset,
    "kitti": KITTI2015Dataset,
    "dummy": DummyStereoDataset,
}


def register_dataset(name: str, cls):
    """注册新数据集."""
    _DATASETS[name] = cls
    return cls


def get_dataset(name: str):
    """按名称获取数据集类."""
    if name not in _DATASETS:
        raise KeyError(f"未知数据集: {name}，可选: {list(_DATASETS.keys())}")
    return _DATASETS[name]


def list_datasets():
    return list(_DATASETS.keys())
