# AGENTS.md — stereo/

双目立体匹配的学习代码。**这条线与仓库其他部分无关**，依赖独立（torch / pytorch_lightning / numpy）。

## 当前状态：未跑通

`models/placeholder.py` 是空壳，整套训练流程没有可用的模型实现。

**这里唯一有实质价值的东西是 `docs/stereo/survey.md`**（749 行算法综述，从 SAD 到2025 基础模型）和 `docs/stereo/base.md`（核心原理速查）。如果只是要理解双目匹配，读文档就够了，不用碰代码。

`docs/stereo/code/` 是第三方参考代码副本（带 `__pycache__`），不是自写代码，依赖 torch。

## 结构

基于 Lightning 的训练框架骨架：

```
train.py          训练入口
lit_data.py       数据模块
lit_module.py     模型/损失封装
data/             dataset 与 transform（kitti2015 / dummy / factory）
losses/           composite / epe / smooth_l1
metrics/          stereo.py
models/           registry + placeholder（待实现）
config/default.yaml
```

`data/dummy.py` 说明预期数据接口是 `(左图, 右图, 视差图)` 三元组。

## 依赖

```bash
pip install torch torchvision pytorch_lightning numpy
pip install -e .  # 无 pyproject.toml，需手动处理
```

根目录没有 requirements.txt。这条线的依赖**不要**和 `scripts/` 的混在一起。

## 约定

- 配置走 `config/default.yaml`，不要在代码里硬编码超参
- dataset 走 `data/factory.py` 注册，新数据集实现 `__init__.py` 里的接口
- loss / metric 各自有 `factory.py`，新增要在 `losses/factory.py` 注册

## 注意

- `docs/stereo/code/` 与本目录有重复代码，但那份是外部来源，不要反向同步
- `checkpoints/logs/stereo/version_0/` 里有 Lightning 留下的 tfevents 与 `hparams.yaml`，说明框架被跑起来验证过（用的 dummy 数据）。训练产出建议继续指到仓库外，别再往这里堆