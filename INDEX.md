# 索引

> 这是一页地图，回答一个问题：**这个东西我记在哪了。**
> 最后更新：2026-10-15

---

## 一、正在跑的自动化

唯一有 CI 定时任务、能自己产出东西的一条线。

| 路径 | 是什么 |
|---|---|
| `readme.md` | 股市推送工作流的对外说明：数据源、运行命令、推送方式 |
| `AGENTS.md` | **项目说明书（AI 常驻上下文）**：技术栈、目录职责、命令、环境变量、约定、坑、排障 |
| `DEVLOG.md` | 改动流水，按时间倒序 |
| `.github/workflows/foreign-market-content.yml` | 每天 07:30 定时执行，跑在自建 runner |
| `bash/run_digest.sh` | 服务器本地 crontab 入口（08:30） |
| `scripts/foreign_market_digest.py` | 入口：参数解析 + 调服务 |
| `scripts/foreign_market_digest_service.py` | 主体 1988 行：Fetcher / Renderer / LLMRefiner / Publisher 四个类 |
| `scripts/digest_config.py` · `digest_logging.py` | 配置与日志模块 |
| `scripts/digest_llm_config.json` | LLM 接口配置 |
| `scripts/digest_article_scoring_prompt.md` | 选稿评分 prompt：市场影响力 / 时效性 / 来源可信度 |
| `scripts/digest_copywriting_prompt.md` | 文案改写 prompt：财经编辑口吻，只输出 JSON |
| `scripts/README_VIDEO.md` · `video_pipeline.py` | 视频搬运线草稿，Phase 1 未闭环，暂存 |

**产出物**（不入库，仅供查看）：`output/` · `logs/digest-YYYY-MM-DD.log`

---

## 二、学习笔记

自己写的东西，有观点、能独立读懂。

### 双目立体视觉
| 路径 | 是什么 |
|---|---|
| `docs/stereo/survey.md` | **749 行算法综述**，从 SAD 到 2025 基础模型，含公式推导与架构对比。仓库里质量最高的一份 |
| `docs/stereo/base.md` | 195 行核心原理速查：双目图 → 视差图 → 深度图 → 点云 |
| `stereo/` | PyTorch 训练框架骨架（data / losses / metrics / models），`models/` 仍是空壳，未跑通 |
| `docs/stereo/code/` | 参考代码副本（第三方来源，非自写） |

### AI 应用工程师路线图
| 路径 | 是什么 |
|---|---|
| `ai-engineer/engineer-roadmap.md` | 515 行，按岗位要求设计，目标是 6 个月后能拿出可演示项目 |
| `ai-engineer/engineer-roadmap.html` | 同上，HTML 版 |

> ⚠️ `wechat_tech/` 下有一份同名同内容的副本，建议删掉一份。

### 多智能体提示词设计
| 路径 | 是什么 |
|---|---|
| `auto-agent/main.md` | 253 行，HTML 幻灯片多智能体系统的**主智能体提示词**。核心是多 Agent 编排纪律：主 Agent 只调度不干活、不读子 Agent 产出、只收 PASS/FAIL 判定 |
| `auto-agent/wechat-tech-daily-demo-template.md` | 科技日报输出模板，可直接给客户看样例 |

---

## 三、内容生产

把资讯变成中文内容的另一套尝试，和第一条线是同类活。

| 路径 | 是什么 |
|---|---|
| `wechat_tech/README.md` | 这条线的说明文档，OpenClaw 定时任务接入方式 |
| `wechat_tech/wechat-tech-daily.md` | 科技日报 prompt 模板：结构化 JSON 进，Markdown 初稿出 |
| `wechat_tech/wechat-tech-daily-input-example.json` | 清洗脚本的目标输出样例，字段结构要对齐 |
| `wechat_tech/openclaw-schedule-example.md` | 定时任务配置样例，三步串成一条命令 |
| `wechat_tech/generate_wechat_tech_draft.py` | 渲染 prompt + 调 LLM 生成草稿 |
| `wechat_tech/publish_wechat_tech_draft.py` | 发布到公众号草稿箱 |
| `wechat_tech/wechat_tech_daily_cleaner.py` | 资讯清洗，472 行版本 |
| `scripts/wechat_tech_daily_cleaner.py` | 同一份清洗脚本的 390 行旧版，留作版本对照 |
| `tiktok/meta/` | TikTok 视频元数据样本（含 video_info / bili_info 结构） |

---

## 四、网站

| 路径 | 是什么 |
|---|---|
| `czl-web/README.md` | Vue 3 + Vite + Express 个人站说明 |
| `czl-web/content/posts/` | 博客文章源文件（frontmatter + markdown） |
| `czl-web/server/` | Express 后端，`store.js` 管 JSON 数据读写 |
| `czl-web/src/components/admin/` | 管理后台（文章 776 行 / Shell 578 / 内容 565 / 任务 541 / 消息 363 / 流量 346） |
| `czl-web/data/` | 内容数据：articles / posts / messages / tasks / stats / admin |
| `bash/deploy.sh` | PM2 部署脚本，支持 build/start/stop/restart/status/logs |
| `bash/setup-nginx.sh` · `setup-caddy.sh` | Nginx / Caddy 反代与 HTTPS 配置 |

**已发布的文章**：

- `stereo_vision_001.md` — 双目立体视觉 & 点云生成（3D 方向代表作）
- `stereo_datasets.md` — 主流数据集梳理
- `article_001/002/003.md` — 博客系统示例文章（入门、Composition API 实践、城市夜景拍摄）

---

## 五、其他

| 路径 | 是什么 |
|---|---|
| `gradio/test.py` | 只有文件头注释的空文件，可删 |
| `project/ccstart/` | C++ 刷题练习，与主线无关 |
| `ai-engineer/api/` · `auto-agent/doc/` | 空目录 |
| `.diag.env` | ⚠️ 明文密钥，已 gitignore，建议移出仓库并轮换 |

---

## 六、流水层（自动生成，不入索引）

搜东西时会命中，建议忽略这几个目录：

- `scripts/report/` — 40+ 个草稿 html/md 与封面图
- `output/` · `logs/` — 运行产物与日志
- `czl-web/node_modules/` · `.venv/` — 依赖

---

## 待办

- [ ] `wechat_tech/ai-application-engineer-roadmap.*` 与 `ai-engineer/` 下同名文件重复，删一份
- [ ] `docs/stereo/code/` 是第三方代码副本，确认后可删
- [ ] `gradio/test.py` 空文件，删
- [ ] `ai-engineer/api/` · `auto-agent/doc/` 空目录，删
- [ ] `auto-video-v2.zip`（20M）冗余，删
- [ ] `project/ccstart/main_test` · `p2` 未跟踪的编译产物，加 gitignore
- [ ] 视频搬运线决定去留