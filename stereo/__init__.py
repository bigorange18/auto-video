"""Stereo — 双目立体匹配训练框架.

Usage:
    python -m stereo.train

模块:
    data/       — 数据集加载器
    models/     — backbone 模型注册中心
    losses/     — loss 函数
    metrics/    — 评估指标
"""

# 触发 placeholder 模型注册
import stereo.models.placeholder  # noqa: F401
