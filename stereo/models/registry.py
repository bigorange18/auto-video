"""模型注册中心 — 装饰器方式注册 backbone.

用法:
    @register_model("psmnet")
    class PSMNet(nn.Module):
        ...

训练时:
    model = get_model("psmnet", max_disp=192)
"""

import torch.nn as nn

MODEL_REGISTRY: dict[str, type[nn.Module]] = {}


def register_model(name: str):
    """装饰器：将一个 backbone 类注册到指定名称."""

    def wrapper(cls):
        if name in MODEL_REGISTRY:
            raise ValueError(f"模型 '{name}' 已被注册")
        MODEL_REGISTRY[name] = cls
        return cls

    return wrapper


def get_model(name: str, **kwargs) -> nn.Module:
    """按名称实例化模型.

    Args:
        name: 注册时的名称
        **kwargs: 传递给模型构造函数的参数
    """
    if name not in MODEL_REGISTRY:
        raise KeyError(f"未知模型: {name}，可选: {list(MODEL_REGISTRY.keys())}")
    return MODEL_REGISTRY[name](**kwargs)


class BaseStereoModel(nn.Module):
    """双目模型基类.

    所有 backbone 继承此类，统一 forward 接口：
        forward(left, right) → Tensor[B, 1, H, W]
    """

    def forward(self, left, right):
        """前向传播.

        Args:
            left:  [B, 3, H, W] 左图
            right: [B, 3, H, W] 右图

        Returns:
            dict: {"disparity": [B, 1, H, W]} 或其他输出
        """
        raise NotImplementedError
