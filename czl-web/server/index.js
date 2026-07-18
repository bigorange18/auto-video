import path from 'node:path'
import bcrypt from 'bcryptjs'
import express from 'express'
import session from 'express-session'
import {
  addTask,
  addMessage,
  createArticle,
  deleteTask,
  deleteMessage,
  deleteArticle,
  getAdmin,
  getArticleById,
  getArticles,
  getContent,
  getMessages,
  getPublicMessages,
  getPublicStats,
  getStats,
  getTasks,
  getTaskSummary,
  markMessageRead,
  readJson,
  saveContent,
  trackVisit,
  updateArticle,
  updateTask,
} from './store.js'

function readBoolean(value, fallback = false) {
  if (value === undefined) {
    return fallback
  }
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase())
}

const app = express()
const host = process.env.HOST || '0.0.0.0'
const port = Number(process.env.PORT || 8787)
const siteUrl = process.env.SITE_URL || `http://127.0.0.1:${port}`
const trustProxy = readBoolean(process.env.TRUST_PROXY)
const cookieSecure = readBoolean(process.env.COOKIE_SECURE, siteUrl.startsWith('https://'))
const rootDir = process.cwd()
const distDir = path.join(rootDir, 'dist')

if (trustProxy) {
  app.set('trust proxy', 1)
}

app.use(express.json())
app.use(
  session({
    secret: process.env.SESSION_SECRET || 'czl-web-session-secret',
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: cookieSecure,
      maxAge: 1000 * 60 * 60 * 8,
    },
  }),
)

function requireAuth(req, res, next) {
  if (!req.session.user) {
    return res.status(401).json({ success: false, message: '未登录' })
  }
  next()
}

const rateLimitMap = new Map()
function rateLimit(maxRequests = 3, windowMs = 60000) {
  return (req, res, next) => {
    const ip = req.ip || 'unknown'
    const now = Date.now()
    const record = rateLimitMap.get(ip)
    if (record && now - record.start < windowMs) {
      record.count++
      if (record.count > maxRequests) {
        return res.status(429).json({ success: false, message: '请求过于频繁，请稍后再试' })
      }
    } else {
      rateLimitMap.set(ip, { start: now, count: 1 })
    }
    next()
  }
}

function sanitizeContent(raw) {
  return {
    site: raw.site || {},
    intro: raw.intro || {},
    skills: Array.isArray(raw.skills) ? raw.skills : [],
    projects: Array.isArray(raw.projects) ? raw.projects : [],
    contact: raw.contact || {},
  }
}

app.get('/api/public/content', async (req, res) => {
  const forwardedFor = req.headers['x-forwarded-for']
  const ip = typeof forwardedFor === 'string' ? forwardedFor.split(',')[0].trim() : req.ip
  await trackVisit(ip || 'unknown', req.headers['user-agent'] || 'unknown')
  const content = await getContent()
  res.json({ success: true, data: sanitizeContent(content) })
})

app.post('/api/public/messages', rateLimit(3, 60000), async (req, res) => {
  const { name, email, body } = req.body || {}
  if (!name || !email || !body) {
    return res.status(400).json({ success: false, message: '请完整填写留言信息' })
  }
  if (String(body).trim().length < 5) {
    return res.status(400).json({ success: false, message: '留言内容至少 5 个字' })
  }
  await addMessage({
    name: String(name).trim(),
    email: String(email).trim(),
    body: String(body).trim(),
  })
  res.json({ success: true, message: '留言已提交' })
})

app.get('/api/public/articles', async (req, res) => {
  const page = Math.max(1, parseInt(req.query.page) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit) || 0))
  const all = await getArticles()

  if (!limit) {
    const data = all.map(({ content, ...rest }) => rest)
    return res.json({ success: true, data })
  }
  const total = all.length
  const totalPages = Math.ceil(total / limit)
  const start = (page - 1) * limit
  res.json({
    success: true,
    data: all.slice(start, start + limit).map(({ content, ...rest }) => rest),
    total,
    page,
    totalPages,
  })
})

app.get('/api/public/articles/:id', async (req, res) => {
  const article = await getArticleById(req.params.id)
  if (!article) {
    return res.status(404).json({ success: false, message: '文章不存在' })
  }
  res.json({ success: true, data: article })
})

app.get('/api/public/stats', async (_req, res) => {
  const stats = await getPublicStats()
  res.json({ success: true, data: stats })
})

app.post('/api/admin/login', async (req, res) => {
  const { username, password } = req.body || {}
  const admin = await getAdmin()
  if (!username || !password || username !== admin.username) {
    return res.status(401).json({ success: false, message: '账号或密码错误' })
  }
  const ok = await bcrypt.compare(String(password), String(admin.passwordHash || ''))
  if (!ok) {
    return res.status(401).json({ success: false, message: '账号或密码错误' })
  }
  req.session.user = { username: admin.username }
  res.json({ success: true, data: req.session.user })
})

app.post('/api/admin/logout', (req, res) => {
  req.session.destroy(() => {
    res.json({ success: true })
  })
})

app.get('/api/admin/session', (req, res) => {
  res.json({ success: true, data: req.session.user || null })
})

app.get('/api/admin/content', requireAuth, async (_req, res) => {
  const content = await getContent()
  res.json({ success: true, data: sanitizeContent(content) })
})

app.put('/api/admin/content', requireAuth, async (req, res) => {
  const nextContent = sanitizeContent(req.body || {})
  await saveContent(nextContent)
  res.json({ success: true, message: '站点内容已保存', data: nextContent })
})

app.get('/api/admin/messages', requireAuth, async (_req, res) => {
  const messages = await getMessages()
  res.json({ success: true, data: messages })
})

app.patch('/api/admin/messages/:id', requireAuth, async (req, res) => {
  await markMessageRead(req.params.id, req.body || {})
  res.json({ success: true, message: '留言状态已更新' })
})

app.delete('/api/admin/messages/:id', requireAuth, async (req, res) => {
  await deleteMessage(req.params.id)
  res.json({ success: true, message: '留言已删除' })
})

app.get('/api/admin/stats', requireAuth, async (_req, res) => {
  const [stats, messages] = await Promise.all([getStats(), getMessages()])
  const statRows = Object.entries(stats)
    .sort((a, b) => b[0].localeCompare(a[0]))
    .slice(0, 14)
    .map(([date, value]) => ({
      date,
      pv: value.pv || 0,
      uv: Array.isArray(value.uv) ? value.uv.length : 0,
    }))
  res.json({
    success: true,
    data: {
      recent: statRows,
      messageCount: messages.length,
      unreadCount: messages.filter((item) => !item.read).length,
    },
  })
})

app.get('/api/admin/tasks', requireAuth, async (_req, res) => {
  const tasks = await getTasks()
  res.json({ success: true, data: tasks })
})

app.get('/api/admin/tasks/summary', requireAuth, async (_req, res) => {
  const summary = await getTaskSummary()
  res.json({ success: true, data: summary })
})

app.post('/api/admin/tasks', requireAuth, async (req, res) => {
  const payload = req.body || {}
  if (!payload.title || !String(payload.title).trim()) {
    return res.status(400).json({ success: false, message: '任务标题不能为空' })
  }
  const nextTask = await addTask(payload)
  res.json({ success: true, message: '任务已创建', data: nextTask })
})

app.patch('/api/admin/tasks/:id', requireAuth, async (req, res) => {
  const nextTask = await updateTask(req.params.id, req.body || {})
  if (!nextTask) {
    return res.status(404).json({ success: false, message: '任务不存在' })
  }
  res.json({ success: true, message: '任务已更新', data: nextTask })
})

app.delete('/api/admin/tasks/:id', requireAuth, async (req, res) => {
  await deleteTask(req.params.id)
  res.json({ success: true, message: '任务已删除' })
})

// === 文章 CRUD（需认证）===

app.get('/api/admin/articles', requireAuth, async (_req, res) => {
  const articles = await readJson('articles.json', [])
  const sorted = [...articles].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  res.json({ success: true, data: sorted })
})

app.post('/api/admin/articles', requireAuth, async (req, res) => {
  const payload = req.body || {}
  if (!payload.title || !String(payload.title).trim()) {
    return res.status(400).json({ success: false, message: '文章标题不能为空' })
  }
  if (!payload.content || !String(payload.content).trim()) {
    return res.status(400).json({ success: false, message: '文章内容不能为空' })
  }
  const article = await createArticle(payload)
  res.json({ success: true, data: article })
})

app.put('/api/admin/articles/:id', requireAuth, async (req, res) => {
  const updated = await updateArticle(req.params.id, req.body || {})
  if (!updated) return res.status(404).json({ success: false, message: '文章不存在' })
  res.json({ success: true, data: updated })
})

app.delete('/api/admin/articles/:id', requireAuth, async (req, res) => {
  await deleteArticle(req.params.id)
  res.json({ success: true, message: '文章已删除' })
})

// === 公开接口 ===

app.get('/api/public/guestbook', async (_req, res) => {
  const messages = await getPublicMessages()
  res.json({ success: true, data: messages })
})

app.get('/api/public/rss', async (_req, res) => {
  const articles = await getArticles()
  const content = await getContent()
  const siteTitle = content.site?.title || '大橘'
  const siteUrl = process.env.SITE_URL || `http://127.0.0.1:${port}`

  const items = articles.slice(0, 20).map(a => `
    <item>
      <title><![CDATA[${a.title}]]></title>
      <link>${siteUrl}/article/${a.id}</link>
      <description><![CDATA[${a.summary || ''}]]></description>
      <pubDate>${new Date(a.createdAt).toUTCString()}</pubDate>
      <guid>${siteUrl}/article/${a.id}</guid>
    </item>`).join('\n')

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>${siteTitle}</title>
    <link>${siteUrl}</link>
    <description>${content.site?.subtitleName || '个人博客'}</description>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${items}
  </channel>
</rss>`

  res.type('application/rss+xml').send(xml)
})

app.use(express.static(distDir))
app.use((req, res) => {
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ success: false, message: '接口不存在' })
  }
  res.sendFile(path.join(distDir, 'index.html'))
})

app.listen(port, host, () => {
  console.log(`czl-web server listening on ${siteUrl}`)
})
