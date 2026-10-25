# 开发流水

改动记录，按时间倒序。稳定约定与技术栈见 `AGENTS.md`。

---

## 2026-10-25  博客收尾安全与稳定性修复

**安全**
- 管理员密码更新为新的 bcrypt 哈希，哈希成本提升到 12
- 轮换 `SESSION_SECRET`，使旧会话 Cookie 全部失效
- `/api/admin/*` 和 `/api/integration/*` 响应增加 `no-store`

**可靠性**
- 任务集成写入改为真正的局部更新，未提交字段不再被默认值覆盖
- `dist/index.html` 按修改时间自动刷新，构建后不再必须重启服务
- 公开内容读取不再写统计，页面访问改为受限的 `POST /api/public/visit`
- Markdown 上传遇到同名文件返回 `409`，确认后才允许覆盖
- Markdown 解析失败不再静默忽略，后台文章页会显示异常文件提示
- 客户端离开文章页时清理文章级元信息，避免分享预览残留

**验证**
- `npm test`：8 项通过
- `npm run build`：通过
- `npm audit`：0 个漏洞
- 新密码登录 200，旧密码 401
- 任务局部更新保留项目、状态、可见性、日期、标签和备注
- 管理接口返回 `Cache-Control: no-store`
- 同名 Markdown 上传返回 409
- 异常 Markdown 可被后台告警发现
- Playwright：文章元信息进入首页后正确清除，页面无控制台或资源错误

---

## 2026-10-25  任务 API 文档入口

- 新增 `czl-web/docs/API.md`，统一记录公开读取和集成写入接口
- 文档覆盖认证、字段、查询参数、幂等 upsert、响应结构和错误码
- 在根 AGENTS、czl-web AGENTS、INDEX 和 README 增加直接入口
- 明确任务路由或字段变更时必须同步更新 API 文档

---

## 2026-10-25  任务集成写入接口

- 新增 `POST /api/integration/tasks`，供开发工具和自动化脚本写入任务
- 使用 `TASKS_API_TOKEN` Bearer 令牌认证，未配置时接口关闭
- 使用 `externalId` 实现幂等 upsert，重复提交会更新原任务
- 写入时验证项目 slug、状态、优先级和可见性
- 公开任务接口继续隐藏备注、可见性和外部标识

**验证**
- 任务 schema 和公开字段测试通过
- 实际 API 测试覆盖令牌认证、创建、更新、项目关联和清理

---

## 2026-10-25  任务公开接口与项目关联

- 任务字段由自由文本 `project` 迁移为稳定的 `projectSlug`
- 新增任务可见性 `private/public`，默认仅后台可见
- 新增 `GET /api/public/tasks`，支持按项目和状态筛选
- 公开接口不返回备注、可见性等内部字段
- 后台任务编辑增加项目下拉框和可见性切换

**验证**
- 任务 API 单元测试覆盖私有任务过滤、备注隐藏、项目和状态筛选

---

## 2026-10-25  项目卡片筛选与编辑入口

- 项目 schema 新增 `category` 字段，支持 Web、AI、内容、运维、学习和其他分类
- 项目页增加分类按钮、状态筛选和项目/技术栈搜索
- 登录管理员会在项目卡片上看到“编辑项目”入口
- 编辑入口可直达后台内容管理中的对应项目并自动定位、高亮
- 后台项目编辑器增加分类选择

**验证**
- `npm test`：5 项通过
- `npm run build`：通过
- Vue SFC 编译检查：16 个文件通过
- Playwright：分类、状态和搜索筛选正确，桌面/移动端无横向溢出
- Playwright：管理员编辑入口直达 `?tab=content&project=personal-site` 并定位对应项目

---

## 2026-10-24  个人站会话、部署与 SEO 加固

**会话与安全**
- 使用签名 Cookie Session 替换内存 Session Store，服务重启后登录状态仍可保留
- 管理接口增加同源来源校验，支持通过 `ALLOWED_ORIGINS` 配置开发地址
- 增加 CSP、点击劫持防护、MIME 嗅探防护、Referrer Policy 和 Permissions Policy
- KaTeX 内嵌字体加入 CSP 白名单

**备份**
- 新增 `npm run backup`，备份 `data/`、Markdown 文章和上传图片
- 默认写入 `backups/czl-web/`，支持 `BACKUP_DIR` 与 `BACKUP_KEEP_DAYS`
- 备份目录已加入 `.gitignore`

**SEO**
- 新增 `/robots.txt` 和 `/sitemap.xml`
- 首页、项目、关于、文章、后台和 404 页面由服务端注入标题、描述、canonical 和 Open Graph 元信息
- 后台页面设置 `noindex,nofollow`

**验证**
- `npm test`：4 项通过
- `npm run build`：通过
- `npm audit`：0 个漏洞
- 跨站管理请求返回 403，同源请求进入正常认证流程
- Playwright：首页桌面/移动端、项目页、文章页和后台均无控制台错误或横向溢出
- 备份脚本实际生成包含 data、文章和 uploads 的备份

---

## 2026-10-24  个人站数据契约与安全加固

**数据契约**
- 统一项目字段为 `slug/name/summary/description/stack/repoUrl/demoUrl/status/featured`
- 前后台、服务端和 `content.json` 使用同一套项目结构，并兼容旧字段读取
- 示例文章改为未发布，清理内容数据中的示例邮箱、微信号和 GitHub 地址

**安全与可靠性**
- Markdown 输出增加 DOMPurify 清理
- 移除固定会话密钥回退，缺少 `SESSION_SECRET` 时拒绝启动
- 限流和访问统计改用 Express 的可信客户端 IP
- JSON 写入改为串行队列加临时文件原子替换
- 新增 `/api/health` 健康检查

**前端与依赖**
- 首页、标签页和上下篇导航改为自动读取全部文章分页
- highlight.js 改为按需注册常用语言
- KaTeX 与代码高亮样式改为本地打包，移除运行时 CDN 依赖
- 升级 Vite 8、Vue 插件及受影响的传递依赖，`npm audit` 清零
- 新增项目 schema 和文章分页单元测试

**验证**
- `npm test`：4 项通过
- `npm run build`：通过
- Playwright：首页桌面/移动端、项目页、文章页、管理后台均返回 200，无控制台错误或移动端横向溢出
- `node --check server/index.js server/store.js`：通过

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
