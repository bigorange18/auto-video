# WeChat Tech 自动化说明

这个目录集中放和“科技日报公众号自动化”相关的配置、样例和脚本，方便后续在 OpenClaw 中配置定时任务。

## 目录说明

1. [wechat_tech/wechat-tech-daily.md](wechat_tech/wechat-tech-daily.md)
   自动化提示词模板，LLM 输入为结构化 JSON，输出为 Markdown 初稿。

2. [wechat_tech/wechat-tech-daily-input-example.json](wechat_tech/wechat-tech-daily-input-example.json)
   清洗脚本目标输出样例，字段结构需要和这个文件保持一致或高度兼容。

3. [wechat_tech/wechat_tech_daily_cleaner.py](wechat_tech/wechat_tech_daily_cleaner.py)
   科技资讯清洗脚本骨架，支持从 URL 或本地 HTML 提取新闻并输出结构化 JSON。

4. [wechat_tech/render_wechat_tech_prompt.py](wechat_tech/render_wechat_tech_prompt.py)
   将结构化 JSON 渲染成最终发给模型的 prompt 文本，方便 OpenClaw 直接调用。

5. [wechat_tech/generate_wechat_tech_draft.py](wechat_tech/generate_wechat_tech_draft.py)
   读取 prompt 文本，调用 OpenAI 兼容接口生成科技日报 Markdown 初稿。

6. [wechat_tech/run_wechat_tech_pipeline.sh](wechat_tech/run_wechat_tech_pipeline.sh)
   一键串联清洗、渲染和生成流程，适合给 OpenClaw 或 cron 直接调用。

7. [wechat_tech/openclaw-schedule-example.md](wechat_tech/openclaw-schedule-example.md)
   OpenClaw 定时任务配置样例，包含单任务和分阶段两种方式。

## 推荐工作流

1. 定时抓取科技资讯页面 HTML
2. 调用清洗脚本生成结构化 JSON
3. 用渲染脚本将 JSON 填入提示词中的 `{{structured_news_payload}}`
4. 调用 LLM 生成科技日报 Markdown 初稿
5. 将 Markdown 转成微信公众号 HTML
6. 上传封面和正文到微信公众号草稿箱

如果你只是先把“定时生成 Markdown 草稿”跑通，直接调用 `run_wechat_tech_pipeline.sh` 就够了。

## 清洗脚本用法

### 从网页直接清洗

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate

python /mnt/f/fun_project/auto-video/wechat_tech/wechat_tech_daily_cleaner.py \
  --input-url "https://news.10jqka.com.cn/" \
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json" \
  --source-name "同花顺科技" \
  --limit 12
```

### 从本地 HTML 清洗

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate

python /mnt/f/fun_project/auto-video/wechat_tech/wechat_tech_daily_cleaner.py \
  --input-html "/tmp/tech-raw.html" \
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json" \
  --source-name "同花顺科技" \
  --limit 12
```

## Prompt 渲染脚本用法

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate

python /mnt/f/fun_project/auto-video/wechat_tech/render_wechat_tech_prompt.py \
   --input-json "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json" \
   --prompt-template "/mnt/f/fun_project/auto-video/wechat_tech/wechat-tech-daily.md" \
   --output "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt"
```

默认行为：

1. 自动从提示词文档里提取“提示词正文”代码块
2. 只替换 `{{structured_news_payload}}` 占位符
3. 输出纯文本 prompt，适合 OpenClaw 直接读取或提交给模型

如果你想直接输出整份 markdown 文档而不是只取代码块，可以加：

```bash
--full-doc
```

## Markdown 生成脚本用法

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate

python /mnt/f/fun_project/auto-video/wechat_tech/generate_wechat_tech_draft.py \
   --input-prompt "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt" \
   --output "/mnt/f/fun_project/auto-video/output/wechat-tech/draft-$(date +%F).md"
```

默认会从环境变量里读取 LLM 配置，兼容这些变量：

1. `LLM_PROVIDER`
2. `LLM_BASE_URL`
3. `LLM_API_KEY`
4. `LLM_MODEL`
5. `OPENAI_API_KEY`
6. `DASHSCOPE_API_KEY`
7. `DEEPSEEK_API_KEY`

如果你想保留接口原始响应用于排查，可以加：

```bash
--save-raw-response "/mnt/f/fun_project/auto-video/output/wechat-tech/raw-llm-$(date +%F).json"
```

## 一键流水线脚本用法

```bash
/bin/bash /mnt/f/fun_project/auto-video/wechat_tech/run_wechat_tech_pipeline.sh
```

这个脚本会顺序执行：

1. 清洗网页为 JSON
2. 渲染 prompt 文本
3. 调用模型生成 Markdown 草稿

如果你要给 OpenClaw 直接配置一个命令，优先用这个脚本。

## 输出文件建议

建议在项目中固定一个输出目录，例如：

```bash
/mnt/f/fun_project/auto-video/output/wechat-tech/
```

推荐产物：

1. `raw-YYYY-MM-DD.html`
2. `cleaned-YYYY-MM-DD.json`
3. `prompt-YYYY-MM-DD.txt`
4. `draft-YYYY-MM-DD.md`
5. `draft-YYYY-MM-DD.html`
6. `raw-llm-YYYY-MM-DD.json`（可选）

## OpenClaw 定时任务建议

如果你后续要在 OpenClaw 中配定时任务，建议拆成两个阶段：

1. 采集和清洗任务
   负责抓网页、生成结构化 JSON

2. 生成和发布任务
   负责渲染 prompt、调用模型生成 Markdown，再转 HTML 并推到公众号草稿箱

这样排查问题会更容易，不会把“采集失败”“模型输出异常”“微信上传失败”混在同一个任务里。

完整样例见：

1. [wechat_tech/openclaw-schedule-example.md](wechat_tech/openclaw-schedule-example.md)

## 定时任务最小命令示例

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate && \
python /mnt/f/fun_project/auto-video/wechat_tech/wechat_tech_daily_cleaner.py \
  --input-url "https://news.10jqka.com.cn/" \
  --output "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json" \
  --source-name "同花顺科技" \
  --limit 12
```

生成 prompt 的最小命令示例：

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate && \
python /mnt/f/fun_project/auto-video/wechat_tech/render_wechat_tech_prompt.py \
   --input-json "/mnt/f/fun_project/auto-video/output/wechat-tech/cleaned-$(date +%F).json" \
   --output "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt"
```

生成 Markdown 草稿的最小命令示例：

```bash
source /mnt/f/fun_project/auto-video/.venv/bin/activate && \
python /mnt/f/fun_project/auto-video/wechat_tech/generate_wechat_tech_draft.py \
   --input-prompt "/mnt/f/fun_project/auto-video/output/wechat-tech/prompt-$(date +%F).txt" \
   --output "/mnt/f/fun_project/auto-video/output/wechat-tech/draft-$(date +%F).md"
```

## 后续建议

1. 给不同站点补专用选择器和时间解析规则
2. 增加基于链接和语义的重复事件合并
3. 增加板块行情和政策动态的专门抓取脚本
4. 再补一个 JSON 到 prompt 文本的渲染脚本
5. 再补一个 Markdown 转微信公众号 HTML 的转换脚本