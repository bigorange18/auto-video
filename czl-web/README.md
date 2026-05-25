# czl-web

基于 Vue 3 + Vite + Express 的个人主页与管理后台。

## 环境配置

复制 `.env.example` 为 `.env` 后，按需修改下面几个关键项即可：

```bash
HOST=0.0.0.0
PORT=8787
SITE_URL=http://127.0.0.1:8787
SESSION_SECRET=replace-with-a-long-random-string

DEV_HOST=0.0.0.0
DEV_PORT=5173
DEV_API_TARGET=http://127.0.0.1:8787
```

说明：

- `HOST` / `PORT`：生产服务监听地址和端口。
- `SITE_URL`：站点对外访问地址，便于部署时统一记录和启用安全 Cookie 判断。
- `SESSION_SECRET`：登录会话密钥，线上必须修改。
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
npm run build
npm run start
```

生产环境由 Express 提供 API 和 dist 静态文件。

## 本地部署

```bash
npm install
cp .env.example .env
npm run deploy:local
```

启动后默认访问 `http://127.0.0.1:8787`。
