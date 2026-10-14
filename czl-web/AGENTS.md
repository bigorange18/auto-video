# AGENTS.md — czl-web/

Vue 3 + Vite + Express 的个人主页与内容管理后台。**这条线与仓库其他部分无关**，是独立的 Node 项目。

## 结构

```
src/
  App.vue / main.js / markdown.js / styles.css
  views/           HomeView · AboutView · ProjectsView · TagView · ArticleView
  components/admin/  AdminArticles(776) · AdminShell(578) · AdminContent(565)
                    AdminTasks(541) · AdminMessages(363) · AdminTraffic(346)
server/
  index.js         Express 入口（356 行）
  store.js         JSON 数据读写（393 行）
content/posts/     博客源文件（frontmatter + markdown）
data/              内容数据 JSON（articles / messages / tasks / stats / admin）
```

## 命令

```bash
npm install
npm run dev        # 开发，Vite 5173
npm run build      # 构建到 dist/
bash bash/deploy.sh build|start|stop|restart|status|logs
bash bash/setup-nginx.sh    # 反代 + HTTPS（需要 root）
```

部署走 PM2，服务名 `czl-web`，端口默认 8787。

## 环境变量

复制 `.env.example` 为 `.env`。关键项：

```
HOST / PORT           监听地址与端口
SITE_URL              站点对外地址
SESSION_SECRET        会话密钥，线上必改
DEV_API_TARGET        开发时前端代理的后端地址
```

`.env` 不入库。

## 约定

- 文章源文件放 `content/posts/`，frontmatter 必需字段：`title` · `summary` · `type`
- `type` 现阶段只用 `blog` 和 `photo`
- 数据一律存 JSON，由 `server/store.js` 读写，**不要引入数据库**
- 改 admin 组件前先看 `data/` 里现有字段结构，别凭猜测改结构

## 坑

1. **`data/*.json` 的 gitignore 很脆**。`.gitignore` 有全局 `*.json` 规则，靠 11 条 `!` 逐个放行。新增数据文件必须同时加 `!` 例外，否则本地能跑、提交后挂掉且难排查。**加数据文件时请一并检查 .gitignore。**

2. **`AdminArticles.vue` 776 行**，是最大的单文件。改之前先读全，字段联动多。

3. **`content/posts/` 里 `article_001/002/003.md` 是示例文章**，不是真实内容（"欢迎来到我的博客"、"第一篇示例文章"）。`stereo_vision_001.md` 和 `stereo_datasets.md` 才是真文章。

4. `dist/` 和 `public/uploads/` 已在 gitignore，`dist/` 里的东西不要手改，下次构建会覆盖。