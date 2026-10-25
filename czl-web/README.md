# czl-web

基于 Vue 3 + Vite + Express 的个人主页与管理后台。

## 环境配置

复制 `.env.example` 为 `.env` 后，按需修改下面几个关键项即可：

```bash
HOST=0.0.0.0
PORT=8787
SITE_URL=http://127.0.0.1:8787
SESSION_SECRET=replace-with-a-long-random-string
TASKS_API_TOKEN=replace-with-a-long-random-token

DEV_HOST=0.0.0.0
DEV_PORT=5173
DEV_API_TARGET=http://127.0.0.1:8787
```

说明：

- `HOST` / `PORT`：生产服务监听地址和端口。
- `SITE_URL`：站点对外访问地址，便于部署时统一记录和启用安全 Cookie 判断。
- `SESSION_SECRET`：登录会话密钥。缺失时服务会拒绝启动，线上必须使用长随机值。
- `ALLOWED_ORIGINS`：可选，逗号分隔的额外管理接口来源。主来源自动使用 `SITE_URL`。
- `DEV_HOST` / `DEV_PORT` / `DEV_API_TARGET`：本地开发时的前端服务地址、端口和 API 代理地址。

## 开发

```bash
npm install
npm run dev:server
npm run dev
```

前端默认运行在 5173，后端运行在 8787。

## 构建

```bash
npm test
npm run build
npm run start
```

生产环境由 Express 提供 API 和 dist 静态文件。

项目数据字段和文章存储约定见 `data/README.md`。

登录会话使用签名 Cookie，服务重启后仍可保持登录，不依赖内存 Session 存储。

## 任务接口

完整字段、示例、幂等规则和错误码见 [`docs/API.md`](docs/API.md)。

公开只读接口：

```text
GET /api/public/tasks
GET /api/public/tasks?projectSlug=personal-site
GET /api/public/tasks?projectSlug=personal-site&status=in_progress
```

公开接口只返回 `visibility=public` 的任务，并排除内部备注。管理员继续使用 `/api/admin/tasks` 的 CRUD 接口。

开发工具或自动化脚本使用令牌写入接口：

```bash
curl -X POST http://127.0.0.1:8788/api/integration/tasks \
  -H "Authorization: Bearer $TASKS_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "externalId": "dev-task-001",
    "title": "完成项目工作台",
    "projectSlug": "personal-site",
    "status": "in_progress",
    "priority": "high",
    "visibility": "private",
    "tags": ["frontend", "api"]
  }'
```

`externalId` 是幂等键：第一次提交返回 `201` 并创建任务，后续相同 `externalId` 返回 `200` 并更新原任务。未配置 `TASKS_API_TOKEN` 时接口返回 `503`，令牌错误返回 `401`。

## 备份

```bash
npm run backup
```

备份默认写入仓库根目录的 `backups/czl-web/`，包含 `data/`、Markdown 文章和上传图片。可通过 `BACKUP_DIR` 指定目录，通过 `BACKUP_KEEP_DAYS` 控制保留天数，默认 30 天。

服务器定时任务示例：

```cron
15 3 * * * cd /home/orange/auto-video/czl-web && /path/to/node server/backup.js
```

站点同时提供 `/robots.txt`、`/sitemap.xml`，文章页会在服务端注入标题、描述、canonical 和 Open Graph 元信息。

## 本地部署

```bash
npm install
cp .env.example .env
npm run deploy:local
```

启动后默认访问 `http://127.0.0.1:8787`。
