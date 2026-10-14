# AGENTS.md — scripts/

海外热点股市推送工作流。抓外盘 RSS + 国内热榜 → 筛选评分 → AI 改写中文文案 → 投递PushPlus / 飞书 / 微信公众号草稿箱。

## 入口与分层

```
foreign_market_digest.py           入口：参数解析 + 调服务，不含业务逻辑
foreign_market_digest_service.py   主体 1988 行，四个类：
    DigestFetcher      抓取、解析、评分      76-535 行
    DigestRenderer     渲染文案/标题/脚本    537-915 行
    DigestLLMRefiner   LLM 调用、清洗、兜底  916-1369 行
    DigestPublisher推送、微信草稿、封面    1370-1988 行
digest_config.py                   所有阈值、URL、prompt 路径集中在此
digest_logging.py                  双通道日志配置
```

`README_VIDEO.md` 和 `video_pipeline.py` 是视频搬运草稿，未闭环，与本线无关。

## 运行

```bash
# 完整流程（需要 DIGEST_ENV_FILE 指向的环境变量文件）
bash bash/run_digest.sh

# 手动，不推送
python scripts/foreign_market_digest.py --hours 24 --limit 10 --select-limit 5

# 启用 LLM
python scripts/foreign_market_digest.py --llm-enabled --llm-provider qwen
```

脚本默认找 `.env.digest`，但仓库里实际是 `.diag.env`，服务器上可能又不同——用 `DIGEST_ENV_FILE` 覆盖，别硬编码。

`PYTHON_BIN` 默认写死 `/home/orange/miniconda3/bin/python3`，换机器要改。

## 参数语义（容易搞混）

| 参数 | 含义 |
|---|---|
| `--hours 24` | 只要 24 小时内发布的 |
| `--limit 10` | 抓取阶段保留的候选条数 |
| `--select-limit 5` | LLM 评分后**最终**保留几条 |
| `--hot-limit 10` | 每个平台保留的热榜条数 |
| `--strict-wechat` / `--strict-fetch` | 出错非零退出，CI 用 |

## 约定

- **配置不硬编码**：URL、阈值、prompt 路径一律加到 `digest_config.py`
- **prompt 外置**：评分和文案 prompt 是独立 md，改文案不动代码
- **日志走 `logging`**，不用 `print`。格式由 `digest_logging.py` 统一
- **单源失败不中断**：抓取是主备降级逻辑，任一源挂掉不能让整段失败
- **LLM 输出必须容错**：模型返回的 JSON 有概率带 markdown 包裹或多余字段，需清洗 + 降级兜底
- **不引入重依赖**：`Pillow` 是顶层 import，必装。`beautifulsoup4` 只有 `wechat_tech/` 用，本目录不需要。加包前先想清楚能不能用标准库

## 坑

1. **封面是微信草稿失败的头号原因**。`DigestPublisher` 里那套候选图采集 → 尺寸校验 → 域名评分 → 主题一致性加权 → 40007 重试，是踩坑堆出来的。改之前先读那段。

2. **封面尺寸硬约束 900×500**，最小 640×360。`digest_config.py` 里的 `WECHAT_COVER_*` 常量。尺寸不对微信会拒收。

3. **可重试 errcode 白名单** `WECHAT_RETRYABLE_DRAFT_ERRCODES = {40007, 53401, 53402}`。新增错误码前先确认含义，别一股脑加进去。

4. **CI 在 workflow 里传 secret 走命令行参数**，会出现在进程列表里。同机其他用户 `ps` 可见。

5. **workflow 里还有一段临时调试代码**（打印源码是否含某关键字），排查完应该删掉。

## 排障

| 症状 | 先看 |
|---|---|
| 微信草稿失败 | 日志搜 `errcode`，看 `cover candidate score` |
| 外盘条目为 0 | 网络连通性 → `source_urls` 与 fetch warnings |
| 封面不相关 | 调 `digest_config.py` 的 `THEMES` 关键词与一致性阈值 |
| LLM 没生效 | 确认 `DIGEST_LLM_ENABLED=1`，日志是否进 refiner |

日志按天滚动 `logs/digest-YYYY-MM-DD.log`。
关键词：`cover dominant themes`、`cover candidate score`、`selected wechat cover`、`wechat draft created`。