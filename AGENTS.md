# AGENTS.md

海外热点股市自动推送工作流的常驻说明书。**本文件是给 AI 助手和未来的自己看的项目上下文**，内容按主题组织，长期有效。

改动流水记在 git log 与 `DEVLOG.md`。

---

## 这是什么

**不是** `auto-video` 视频搬运项目——仓库名是历史遗留，视频线只到Phase 1 草稿。

这里唯一在跑的东西是一条每日定时工作流：

```
抓外盘 RSS + 国内热榜 → 筛选评分 → AI 改写中文文案 → 投递到 PushPlus / 飞书 / 微信公众号草稿箱
```

配套还有一条同类的科技日报线（`wechat_tech/`），尚未收敛成同一套代码。

---

## 技术栈

- **Python 3.10+**（代码用了 PEP 604 `str | None` 和 `tuple[str, ...]` 语法）
- 标准库为主：`urllib` / `xml.etree` / `json` / `logging` / `argparse`
- 第三方依赖**只有两个**，且都跟 LLM、封面生成有关：

| 包 | 用途 | 必需性 |
|---|---|---|
| `Pillow` | 微信封面自动生成（`ImageDraw` / `ImageFont`） | 用封面就必需 |
| `beautifulsoup4` | 抓取时解析文章页取og:image | 不用封面可省 |

LLM 走HTTP + OpenAI 兼容协议，**没有 SDK 依赖**。仓库根目录目前**没有 requirements.txt**，换机器部署需手动装上面两个包。

`stereo/` 是另一条独立的学习线（PyTorch 立体匹配），依赖 torch / lightning，与本工作流无关。

---

## 目录职责

```
scripts/
  foreign_market_digest.py           入口，仅做参数解析 + 调服务
  foreign_market_digest_service.py   主体 1988 行，四个类：
      DigestFetcher                  抓取、解析、评分（~430 行）
      DigestRenderer                 渲染 Markdown / 标题 / 短视频脚本（~380 行）
      DigestLLMRefiner               LLM 调用、JSON 清洗、降级兜底（~450 行）
      DigestPublisher                推送、微信草稿、封面生成（~600 行）
  digest_config.py                   所有阈值、URL、prompt 路径集中在此
  digest_logging.py                  双通道日志配置
  digest_llm_config.json             LLM 接口与评分权重
  digest_article_scoring_prompt.md   选稿评分 prompt（输出 JSON）
  digest_copywriting_prompt.md       文案改写 prompt（输出 JSON）
  README_VIDEO.md / video_pipeline.py  视频搬运草稿，未闭环
bash/
  run_digest.sh                      本地 crontab 入口（08:30）
  deploy.sh                          czl-web PM2 部署
  setup-nginx.sh / setup-caddy.sh    反代与 HTTPS
.github/workflows/
  foreign-market-content.yml         定时 07:30，跑在自建 runner
```

---

## 常用命令

```bash
# 本地跑完整流程（需要 DIGEST_ENV_FILE 指向的环境变量文件）
bash bash/run_digest.sh

# 手动跑，不带推送
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5

# 启用 LLM 精炼
python scripts/foreign_market_digest.py \
  --llm-enabled --llm-provider qwen --llm-model qwen-plus

# 只看抓取结果，不推送
python scripts/foreign_market_digest.py --hours 24 --limit 10
```

**关键参数语义**（容易搞混）：
- `--limit 10` — 抓取阶段保留的候选条数
- `--select-limit 5` — LLM 评分后最终保留几条
- `--hours 24` — 只要24 小时内发布的文章
- `--strict-wechat` / `--strict-fetch` — 出错时非零退出，CI 用

---

## 环境变量

密钥从 `DIGEST_ENV_FILE` 指向的文件读取（脚本默认找 `.env.digest`，**仓库里实际是 `.diag.env`**，已被 gitignore）。所有密钥只走环境变量，**不要写进代码或提交**。

| 变量 | 用途 |
|---|---|
| `PUSHPLUS_TOKEN` | PushPlus 推微信 |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 |
| `WECHAT_APP_ID` / `WECHAT_APP_SECRET` | 公众号草稿接口 |
| `WECHAT_AUTHOR` | 草稿作者名 |
| `WECHAT_THUMB_MEDIA_ID` | 固定封面 media_id，优先于自动生成 |
| `DIGEST_LLM_ENABLED` | 设 `1` 才启用 LLM |
| `LLM_PROVIDER` | `openai` / `qwen` / `deepseek` |

provider 未显式设置时，代码会按 `DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY` 是否存在自动推断。

---

## 约定

- **配置不硬编码**：URL、阈值、prompt 路径一律加到 `digest_config.py`，不要散落各处
- **prompt 外置**：评分和文案 prompt 都是独立 md 文件，可独立改文案不动代码
- **日志统一走 `logging`**，不要用 `print`。格式固定为 `日期 [级别] 文件:行号 | 内容`
- **单源失败不中断**：抓取是主备降级逻辑，任何单个源挂掉都不能让整段失败
- **LLM 输出必须容错**：模型返回的 JSON 有概率带markdown 包裹或多余字段，需要清洗 + 降级兜底
- **不引入重依赖**：目前只依赖 PIL 和 bs4，加包前先想清楚能不能用标准库解决

---

## 坑

1. **`.agent.md` 里曾把脚本路径写成 `bin/`**，实际目录是 `bash/`，文档已过时。

2. **`.env.digest` 这个名字容易混淆**——`run_digest.sh` 默认找它，但仓库里真实存在的是 `.diag.env`。服务器上的文件名可能不一样，别硬编码。

3. **封面是微信草稿失败的头号原因**。`DigestPublisher` 里那套候选图采集 → 尺寸校验（最小 640×360）→ 域名评分 → 主题一致性加权 → 40007 自动重试，是踩了很多次坑堆出来的。改动这块之前先读那段逻辑。

4. **微信封面尺寸硬约束 900×500**，最小 640×360。生成的图不对会被微信拒收。

5. **`stereo/` 的 `models/` 还是空壳**（`placeholder.py`），整套代码没跑通。`docs/stereo/survey.md` 才是真正有价值的东西。

6. **CI 跑在自建 runner**，路径写死 `/home/orange/miniconda3/bin/python3`。换机器要改 workflow。

7. **secret 在 CI 里通过命令行参数传递**，会出现在进程列表里。同机其他用户 `ps` 可见。

---

## 排障

| 症状 | 先看 |
|---|---|
| 微信草稿创建失败 | 日志搜 `errcode`，看 `cover candidate score` 评分过程 |
| 外盘条目为 0 | 先看网络连通性，再看 `source_urls` 和 fetch warnings |
| 封面相关性差 | 调 `digest_config.py` 的主题关键词与一致性分值阈值 |
| LLM 没生效 | 确认 `DIGEST_LLM_ENABLED=1`，看日志是否进到 refiner |

日志文件按天滚动：`logs/digest-YYYY-MM-DD.log`
关键日志关键词：`cover dominant themes`、`cover candidate score`、`selected wechat cover`、`wechat draft created`

---

## 维护建议

- 改完逻辑同步更新本文件的「约定」和「坑」两节，这是本文档唯一的维护要求
- 改动细节记到 `DEVLOG.md`，别塞进这里
- `readme.md` 是对外说明（数据源、运行方式），本文件是对内约定，两者不要混