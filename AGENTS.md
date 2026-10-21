# AGENTS.md

海外热点股市自动推送工作流的常驻说明书。改动流水见 `DEVLOG.md`。

**这里不是视频项目**——仓库名是历史遗留，`scripts/video_pipeline.py` 只到Phase 1 草稿。

## 这个仓库的特殊性

五个互不相关的子项目共存，依赖和约定都不互通：

| 目录 | 是什么 | 详细约定 |
|---|---|---|
| `scripts/` | 股市推送工作流，唯一有 CI 定时任务的 | [scripts/AGENTS.md](scripts/AGENTS.md) |
| `stereo/` | 双目立体匹配学习代码（PyTorch） | [stereo/AGENTS.md](stereo/AGENTS.md) |
| `czl-web/` | Vue 3 + Express 个人站 | [czl-web/AGENTS.md](czl-web/AGENTS.md) |
| `wechat_tech/` | 科技日报自动化 | 尚无独立文件 |
| `project/ccstart/` | C++ 刷题练习 | 尚无独立文件 |

**改动某条线之前，先读该目录下的 AGENTS.md。** 各条线之间没有共享约定，不要把一条线的规则套用到另一条线上。

## 全局约定

- 密钥只走环境变量，**不要写进代码、不要提交**。仓库里的 `.diag.env` 已被 gitignore
- Python 侧需要 **3.10+**（`scripts/` 和 `stereo/` 都用了 PEP 604 语法）
- 根 `requirements.txt` 只覆盖股市线（`Pillow`）。新增第三方依赖前先确认是否真需要，且**不要引入重依赖**
- 改动细节记到 `DEVLOG.md`，不要堆进本文件
- `readme.md` 是对外说明，`INDEX.md` 是全仓库导航，两者不要和本文件混

## 提交规范

这个仓库的 git log 是唯一的思考考古线索，**不要写 `update` / `1` / `test` 这类无信息量的信息**。

```
<类型>: <一句话说明为什么改>

背景 / 问题 / 影响范围 / 验证方式
```

例：`fix: 微信封面 40007 重试漏掉缓存刷新导致重复上传`

## 验证

全仓**没有测试**，也没有 CI 校验。所以每次改完必须手动确认：

```bash
python -c "import ast,sys; [ast.parse(open(f).read()) for f in sys.argv[1:]]" <改动的py 文件>
bash -n <改动的 sh 脚本>
```

改动`czl-web/` 时另外跑 `npm run build`。

**定时任务失败是静默的**——每天 07:30 跑，出错只有日志能看到。改完推送链路要手动验一次。

## 目录卫生

- 自动产物别放进源码目录：`scripts/report/`、`output/`、`logs/` 已被 gitignore，但文件仍在磁盘上，搜东西会命中
- C++ 编译产物已加入 gitignore（`main_test` / `p2` / `*.o` / `*.exe`）
- `docs/stereo/code/` 是第三方参考代码副本，不是自写代码