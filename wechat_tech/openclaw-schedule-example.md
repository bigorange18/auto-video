# OpenClaw 定时任务配置样例

这份文档给的是可直接照抄的样例思路，目标是把下面三步串起来：

1. 清洗科技资讯页面，生成结构化 JSON
2. 渲染 prompt 文本
3. 调用 LLM 生成 Markdown 草稿

## 推荐方式

优先让 OpenClaw 只调用一个命令：

```bash
/bin/bash /mnt/f/fun_project/auto-video/wechat_tech/run_wechat_tech_pipeline.sh
```

这样定时系统只负责调度，真正的业务逻辑都留在项目里维护，后续改路径和参数也更容易。

## 前置环境

任务执行前建议保证这些条件已经满足：

1. 已创建 Python 虚拟环境：`/mnt/f/fun_project/auto-video/.venv`
2. `.diag.env` 中已配置 LLM 相关环境变量
3. 需要时已在 `.diag.env` 中增加以下变量：

```bash
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
WECHAT_TECH_SOURCE_URL=https://news.10jqka.com.cn/
WECHAT_TECH_SOURCE_NAME=同花顺科技
REPORT_OUTPUT_DIR=/mnt/f/fun_project/auto-video/output/wechat-tech
```

## 样例一：OpenClaw 单任务方式

如果你的 OpenClaw 支持“名称 + Cron + 命令 + 工作目录”这种基础模式，可以按下面填：

```yaml
name: wechat-tech-daily
enabled: true
schedule: "30 8 * * *"
workingDirectory: /mnt/f/fun_project/auto-video
command: /bin/bash /mnt/f/fun_project/auto-video/wechat_tech/run_wechat_tech_pipeline.sh
timeoutSeconds: 900
env:
  WORK_DIR: /mnt/f/fun_project/auto-video
  ENV_FILE: /mnt/f/fun_project/auto-video/.diag.env
  VENV_ACTIVATE: /mnt/f/fun_project/auto-video/.venv/bin/activate
  WECHAT_TECH_SOURCE_URL: https://news.10jqka.com.cn/
  WECHAT_TECH_SOURCE_NAME: 同花顺科技
  WECHAT_TECH_ITEM_LIMIT: "12"
```

说明：

1. `schedule` 用的是标准 cron 表达式，这里表示每天早上 08:30 执行
2. `timeoutSeconds` 建议给到 10 到 15 分钟，避免模型接口慢时被过早中断
3. 如果 OpenClaw 不支持 `env` 字段，就把这些变量直接写进 `.diag.env`

## 样例二：OpenClaw 分阶段任务方式

如果你的 OpenClaw 支持多个任务拆开执行，建议拆成两个：

### 任务 A：采集 + 清洗

```yaml
name: wechat-tech-clean
enabled: true
schedule: "20 8 * * *"
workingDirectory: /mnt/f/fun_project/auto-video
command: >
  /bin/bash -lc 'source /mnt/f/fun_project/auto-video/.venv/bin/activate &&
  python /mnt/f/fun_project/auto-video/wechat_tech/wechat_tech_daily_cleaner.py
  --input-url "https://news.10jqka.com.cn/"
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json"
  --source-name "同花顺科技"
  --limit 12'
timeoutSeconds: 300
```

### 任务 B：渲染 + 生成草稿

```yaml
name: wechat-tech-generate
enabled: true
schedule: "30 8 * * *"
workingDirectory: /mnt/f/fun_project/auto-video
command: >
  /bin/bash -lc 'source /mnt/f/fun_project/auto-video/.venv/bin/activate &&
  python /mnt/f/fun_project/auto-video/wechat_tech/render_wechat_tech_prompt.py
  --input-json "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json"
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt" &&
  python /mnt/f/fun_project/auto-video/wechat_tech/generate_wechat_tech_draft.py
  --input-prompt "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt"
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/draft-$(date +%F).md"
  --save-raw-response "/mnt/f/fun_project/auto-video/output/wechat-tech/raw-llm-$(date +%F).json"'
timeoutSeconds: 900
```

说明：

1. 任务 A 和任务 B 错开 10 分钟，便于定位问题
2. 如果清洗速度很快，也可以合成一个任务，直接用脚本方式跑

## 样例三：OpenClaw JSON 风格配置

如果你的 OpenClaw 配置界面接近 JSON，可以参考：

```json
{
  "name": "wechat-tech-daily",
  "enabled": true,
  "schedule": "30 8 * * *",
  "workingDirectory": "/mnt/f/fun_project/auto-video",
  "command": "/bin/bash /mnt/f/fun_project/auto-video/wechat_tech/run_wechat_tech_pipeline.sh",
  "timeoutSeconds": 900,
  "env": {
    "WORK_DIR": "/mnt/f/fun_project/auto-video",
    "ENV_FILE": "/mnt/f/fun_project/auto-video/.diag.env",
    "WECHAT_TECH_SOURCE_URL": "https://news.10jqka.com.cn/",
    "WECHAT_TECH_SOURCE_NAME": "同花顺科技",
    "WECHAT_TECH_ITEM_LIMIT": "12"
  }
}
```

## 输出产物

任务正常执行后，默认会产出：

1. `/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-YYYY-MM-DD.json`
2. `/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-YYYY-MM-DD.txt`
3. `/mnt/f/fun_project/auto-video/output/wechat-tech/draft-YYYY-MM-DD.md`
4. `/mnt/f/fun_project/auto-video/output/wechat-tech/raw-llm-YYYY-MM-DD.json`

## 排查建议

1. 如果没有生成 cleaned JSON，先看源站页面是否能访问
2. 如果 prompt 文件存在但 draft 没生成，重点检查 `.diag.env` 里的 LLM 配置
3. 如果定时任务执行失败，先手动执行下面这条命令确认脚本本身没问题：

```bash
/bin/bash /mnt/f/fun_project/auto-video/wechat_tech/run_wechat_tech_pipeline.sh
```

4. 如果 OpenClaw 支持日志路径，建议把 stdout/stderr 单独落到日志文件