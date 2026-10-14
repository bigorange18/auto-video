# 开发流水

改动记录，按时间倒序。稳定约定与技术栈见 `AGENTS.md`。

---

## 2026-04-14  封面可靠性 + 结构重构

**数据源**
- 外盘 RSS 改为主备多源策略（CNBC、Dow Jones/MarketWatch、Nasdaq + Google News query 兜底）
- 抓取支持候选源自动降级，单源失败不导致整段失败

**代码结构**
- 抽出配置模块 `scripts/digest_config.py`
- 抽出日志模块 `scripts/digest_logging.py`
- 主流程重构为类编排（Fetcher / Renderer / Publisher）
- 入口精简为参数解析 + 服务调用

**日志体系**
- 统一 logging 双通道（终端 + 文件）
- 格式含日期、级别、文件名、行号
- 按天滚动 `logs/digest-YYYY-MM-DD.log`

**微信封面**
- 上传前增加封面候选采集、尺寸校验、比例校验、域名评分
- 优先取财经网站文章图（og:image / twitter:image）
- 增加主题一致性校验：按当次主主题对候选图加权评分
- 增加 40007（invalid media_id）自动重试，支持忽略缓存强制重传

**定时任务**
- crontab 每天 08:30 执行 `bash/run_digest.sh`

---

## 2026-04-13  骨架搭建

- 抓取 → 筛选 → 文案生成的最小可跑通链路
- 接入 PushPlus 与飞书推送
- 切换 CI 到自建 runner（需要固定 IP）