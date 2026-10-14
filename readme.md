# auto-video

个人知识库 + 一条在跑的自动化工作流。

这个仓库最初想做 YouTube 视频搬运（`scripts/video_pipeline.py` 是那份草稿，只到 Phase 1），但实际跑起来的是另一条线：**海外热点股市资讯 → 中文文案 → 多平台推送**。视频搬运一直没推进，仓库名也就成了历史遗留。

## 仓库里有什么

五个互不相关的子项目共存，各自依赖和约定都不互通：

| 目录 | 是什么 | 详细约定 |
|---|---|---|
| `scripts/` | 股市推送工作流，唯一有 CI 定时任务的 | [scripts/AGENTS.md](scripts/AGENTS.md) |
| `czl-web/` | Vue 3 + Express 个人站与内容后台 | [czl-web/AGENTS.md](czl-web/AGENTS.md) |
| `stereo/` | 双目立体匹配学习代码（PyTorch） | [stereo/AGENTS.md](stereo/AGENTS.md) |
| `wechat_tech/` | 科技日报自动化 | [wechat_tech/README.md](wechat_tech/README.md) |
| `project/ccstart/` | C++ 刷题练习 | — |

**全仓库导航看 [INDEX.md](INDEX.md)** —— 想知道某个东西记在哪，从那里进。

约定与坑分布在各目录的 `AGENTS.md`，改某条线之前先读对应那份。

---

## 海外热点股市自动化工作流

抓外盘 RSS + 国内热榜 → 筛选评分 → AI 改写中文文案 → 投递到 PushPlus / 飞书 / 微信公众号草稿箱。

每天 07:30（UTC）定时执行，结果作为 artifact 上传。

## 需要什么

**Python 3.10+**（代码用了 PEP 604 语法）。

**`Pillow` 是必装的**——`scripts/foreign_market_digest_service.py` 顶层直接 import，装不上就跑不起来：

```bash
pip install Pillow
```

`beautifulsoup4` 只有 `wechat_tech/` 那条线需要，跑股市推送用不到。

其余全部用标准库，LLM 走 HTTP 调OpenAI 兼容接口，不需要 SDK。

> 仓库根目录没有 requirements.txt，要手动装。
>
> 注意：仓库里的 `.venv/` 是 Linux 布局（`bin/` 而非 Windows 的 `Scripts/`），在 Windows 上用不了。Windows 下建议另建虚拟环境：
>
> ```bash
> python -m venv .venv-win
> .venv-win/Scripts/pip install Pillow
> ```

密钥只走环境变量，不要写进代码或提交。

## 快速开始

确认已装好 Pillow 后（见上）：

```bash
# 不带推送，只生成产物
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5
```

启用 LLM 精炼：

```bash
python scripts/foreign_market_digest.py \
  --llm-enabled \
  --llm-provider qwen \
  --llm-api-key "$DASHSCOPE_API_KEY" \
  --llm-model qwen-plus
```

`--llm-provider` 支持 `openai` / `qwen` / `deepseek`，都是 OpenAI 兼容协议。不显式传 `--llm-base-url` 时会自动用各家默认地址。

完整参数见 [scripts/AGENTS.md](scripts/AGENTS.md)。

## 数据来源

外盘走主备多源策略（CNBC、Dow Jones/MarketWatch、Nasdaq、Yahoo Finance、Google News 兜底），单源失败不中断整体。国内热榜走抖音、头条、百度三个 API。

评分权重、主题关键词、feed 地址都在 `scripts/digest_config.py`，改配置不用动代码。

## 输出

| 文件 | 内容 |
|---|---|
| `output/foreign_market_hotspots.json` | 热点列表、主题分类、摘要、标题建议、短视频口播、社媒文案 |
| `output/foreign_market_copy.md` | 适合直接给运营/剪辑看的 Markdown |

`markdown` 面向人工使用，`json` 供下游程序消费。两者都不入库。

日志按天滚动：`logs/digest-YYYY-MM-DD.log`。

## 定时任务

### 方式一：GitHub Actions（推荐）

工作流文件 `.github/workflows/foreign-market-content.yml`，跑在自建 runner 上（需要固定 IP）。

在仓库 `Settings -> Secrets and variables -> Actions` 配置：

| Key | 说明 |
|---|---|
| `PUSHPLUS_TOKEN` | PushPlus token，推送到自己微信 |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 webhook |
| `WECHAT_APP_ID` | 公众号 AppID |
| `WECHAT_APP_SECRET` | 公众号 AppSecret |
| `WECHAT_AUTHOR` | 草稿作者名（用 `vars` 而非 `secrets`） |

推送渠道都可选，不配就不推那个渠道。

### 方式二：服务器 cron

```bash
# 照着 AGENTS.md 里的环境变量表建一个 .env.digest
$EDITOR .env.digest
bash bash/run_digest.sh              # 先手动验一次
```

脚本默认读 `DIGEST_ENV_FILE` 指向的文件（默认 `.env.digest`，可用该变量覆盖）。

```cron
30 8 * * * /bin/bash /home/orange/auto-video/bash/run_digest.sh
```

> ⚠️ 定时任务失败是静默的，只有日志能看到。改完推送链路一定要手动验一次。

## 环境变量

除了上面五个推送凭据，LLM 部分支持：

| 变量 | 说明 |
|---|---|
| `DIGEST_LLM_ENABLED` | 设 `1` 才启用 LLM（`run_digest.sh` 用） |
| `LLM_PROVIDER` | `openai` / `qwen` / `deepseek`，不设则按 key 是否存在自动推断 |
| `LLM_BASE_URL` · `LLM_API_KEY` · `LLM_MODEL` | 通用覆盖项 |
| `DASHSCOPE_API_KEY` · `QWEN_MODEL` | 千问专用，等价写法 |
| `DEEPSEEK_API_KEY` · `DEEPSEEK_MODEL` | DeepSeek 专用 |
| `LLM_TIMEOUT` | 请求超时，默认 25 秒 |

完整列表见 [scripts/AGENTS.md](scripts/AGENTS.md)。

## 已知问题

- **封面是微信草稿失败的头号原因。** 尺寸硬约束 900×500（最小 640×360），尺寸不对微信直接拒收。排查看日志里的 `errcode` 和 `cover candidate score`
- **CI 里 secret 走命令行参数传递**，会出现在进程列表里，同机其他用户 `ps` 可见
- **全仓没有测试**，改完用 `python -c "import ast..."` 做语法检查，推送链路改动手动验