2026-04-08

# 海外热点股市自动化工作流

这个仓库现在提供一套最小可用的自动化流程，用于：

- 自动抓取海外股市热点新闻
- 自动筛选高热度市场主题
- 自动生成中文文案素材
- 通过 GitHub Actions 定时执行并产出结果文件
- 每天自动推送结果到飞书
- 每天自动推送结果到微信
- 自动创建微信公众号图文草稿

## 目录

- `scripts/foreign_market_digest.py`：抓取 RSS、筛选热点、生成文案
- `bin/run_digest.sh`：服务器本地 cron 运行入口
- `.github/workflows/foreign-market-content.yml`：定时运行工作流
- `output/`：脚本运行后的产物目录（默认不入库）

## 数据来源

脚本当前使用 Google News RSS 搜索，覆盖：

- 美股主线：NASDAQ、NYSE、S&P 500、Dow Jones
- 欧股主线：STOXX 600、FTSE、DAX
- 亚太主线：Nikkei、Hang Seng、MSCI Asia

## 本地运行

仓库不依赖第三方 Python 包，直接运行即可：

```bash
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5
```

推送飞书：

```bash
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5 --feishu-webhook "$FEISHU_WEBHOOK_URL"
```

推送微信（PushPlus）：

```bash
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5 --pushplus-token "$PUSHPLUS_TOKEN"
```

创建微信公众号草稿：

```bash
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5 --wechat-app-id "$WECHAT_APP_ID" --wechat-app-secret "$WECHAT_APP_SECRET" --wechat-author "你的公众号作者名"
```

启用大模型梳理（OpenAI 兼容接口）：

```bash
python scripts/foreign_market_digest.py \
	--hours 24 --limit 10 --select-limit 5 \
	--llm-enabled \
	--llm-provider openai \
	--llm-base-url "$LLM_BASE_URL" \
	--llm-api-key "$LLM_API_KEY" \
	--llm-model "${LLM_MODEL:-gpt-4o-mini}"
```

启用千问（阿里云 DashScope 兼容接口）：

```bash
python scripts/foreign_market_digest.py \
	--hours 24 --limit 10 --select-limit 5 \
	--llm-enabled \
	--llm-provider qwen \
	--llm-api-key "$DASHSCOPE_API_KEY" \
	--llm-model "${QWEN_MODEL:-qwen-plus}"
```

如果不显式传 `--llm-base-url`，`qwen` 会默认使用：

```text
https://dashscope.aliyuncs.com/compatible-mode/v1
```

启用 DeepSeek（OpenAI 兼容接口）：

```bash
python scripts/foreign_market_digest.py \
	--hours 24 --limit 10 --select-limit 5 \
	--llm-enabled \
	--llm-provider deepseek \
	--llm-api-key "$DEEPSEEK_API_KEY" \
	--llm-model "${DEEPSEEK_MODEL:-deepseek-chat}"
```

如果不显式传 `--llm-base-url`，`deepseek` 会默认使用：

```text
https://api.deepseek.com/v1
```

说明：默认会先抓取最多 10 条候选（`--limit`），再由大模型打分筛选 5 条（`--select-limit`）用于最终公众号内容。

也可以通过环境变量配置：

- `LLM_PROVIDER`（`openai`、`qwen` 或 `deepseek`）
- `LLM_BASE_URL`（默认 `https://api.openai.com/v1`）
- `LLM_API_KEY`
- `LLM_MODEL`（默认 `gpt-4o-mini`）
- `LLM_TIMEOUT`（默认 `25` 秒）
- `DIGEST_LLM_ENABLED=1`（用于 `bin/run_digest.sh` 启用）

千问也支持下面这些更直观的环境变量：

- `DASHSCOPE_API_KEY`
- `DASHSCOPE_BASE_URL`（默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
- `QWEN_API_KEY`（可作为 `DASHSCOPE_API_KEY` 的别名）
- `QWEN_MODEL`（默认 `qwen-plus`）

DeepSeek 也支持下面这些环境变量：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com/v1`）
- `DEEPSEEK_KEY`（可作为 `DEEPSEEK_API_KEY` 的别名）
- `DEEPSEEK_MODEL`（默认 `deepseek-chat`）

服务器上推荐这样配置 `.env.digest`：

```bash
DIGEST_LLM_ENABLED=1
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=你的千问Key
QWEN_MODEL=qwen-plus
```

如果你用 DeepSeek，可以改为：

```bash
DIGEST_LLM_ENABLED=1
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的DeepSeekKey
DEEPSEEK_MODEL=deepseek-chat
```

默认输出：

- `output/foreign_market_hotspots.json`
- `output/foreign_market_copy.md`

## 服务器 Cron

如果你不想继续折腾 GitHub Actions，推荐直接在服务器上用 `cron` 定时执行。

1. 复制环境模板：

```bash
cp .env.digest.example .env.digest
```

2. 编辑 `.env.digest`，填入你的：

- `PUSHPLUS_TOKEN`
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`
- `WECHAT_AUTHOR`

3. 先手动执行一次：

```bash
bash bin/run_digest.sh
```

4. 配置定时任务：

```bash
crontab -e
```

例如每天早上 `08:30` 执行：

```cron
30 8 * * * /bin/bash /home/orange/auto-video/bin/run_digest.sh
```

5. 查看日志：

```bash
tail -f /home/orange/auto-video/cron.log
```

## 输出内容

`json` 文件包含：

- 热点文章列表
- 主题分类
- 一句话摘要
- 标题建议
- 短视频口播文案
- 社媒短文案

`markdown` 文件适合直接给运营、剪辑或内容团队使用。

## GitHub Actions

工作流文件：`.github/workflows/foreign-market-content.yml`

触发方式：

- 手动触发：`workflow_dispatch`
- 定时触发：每天 UTC `07:30`

执行完成后，结果会作为 Actions artifact 上传。

## 微信配置

如果你要把消息直接推到自己的微信，推荐用 PushPlus。

1. 打开 `https://www.pushplus.plus/`
2. 用微信扫码登录
3. 在后台复制你的 `token`
4. 在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 添加：`PUSHPLUS_TOKEN`

脚本会把日报以 Markdown 形式推送到你的微信。

## 飞书配置

需要先在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加：

- `FEISHU_WEBHOOK_URL`

脚本会在生成日报后，自动把摘要、热点清单、标题建议和社媒文案以飞书卡片消息推送到机器人。

## 微信公众号配置

如果你要把内容同步到微信公众号后台草稿箱，需要在 GitHub 中配置：

- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

可选变量：

- `WECHAT_AUTHOR`

配置路径：`Settings -> Secrets and variables -> Actions`

脚本会自动：

- 获取公众号 `access_token`
- 上传默认封面图
- 创建一篇图文草稿到公众号后台

创建完成后，你可以在微信公众号后台的草稿箱中查看并决定是否群发。
