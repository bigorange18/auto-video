import 'dotenv/config'
import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import crypto from 'node:crypto'
import bcrypt from 'bcryptjs'
import express from 'express'
import session from 'express-session'
import {
  addTask,
  addMessage,
  createArticle,
  deleteArticle,
  deleteTask,
  deleteMessage,
  getAdmin,
  getAllArticlesAdmin,
  getArticleById,
  getArticles,
  getContent,
  getMessages,
  getPublicStats,
  getStats,
  getTasks,
  getTaskSummary,
  markMessageRead,
  saveArticleFile,
  saveContent,
  trackVisit,
  updateArticle,
  updateTask,
} from './store.js'

// Simple in-memory rate limiter
function makeRateLimiter(maxRequests, windowMs) {
  const map = new Map()
  return function (req, res, next) {
    const ip =
      (typeof req.headers['x-forwarded-for'] === 'string'
        ? req.headers['x-forwarded-for'].split(',')[0].trim()
        : req.ip) || 'unknown'
    const now = Date.now()
    const entry = map.get(ip) || { count: 0, resetAt: now + windowMs }
    if (now > entry.resetAt) {
      entry.count = 0
      entry.resetAt = now + windowMs
    }
    entry.count++
    map.set(ip, entry)
    if (entry.count > maxRequests) {
      return res.status(429).json({ success: false, message: '请求过于频繁，请稍后再试' })
    }
    next()
  }
}
const messagesLimiter = makeRateLimiter(3, 10 * 60 * 1000)   // 3/10min
const loginLimiter = makeRateLimiter(5, 15 * 60 * 1000)       // 5/15min

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
const uploadsDir = path.join(rootDir, 'public', 'uploads')

// Ensure uploads directory exists
if (!existsSync(uploadsDir)) {
  fs.mkdir(uploadsDir, { recursive: true }).catch(() => {})
}

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

app.post('/api/public/messages', messagesLimiter, async (req, res) => {
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
  const all = await getArticles()
  const stripped = all.map(({ content, ...rest }) => rest)
  const page = Math.max(1, parseInt(req.query.page) || 1)
  const pageSize = Math.min(50, Math.max(1, parseInt(req.query.pageSize) || 10))
  const total = stripped.length
  const totalPages = Math.ceil(total / pageSize)
  const articles = stripped.slice((page - 1) * pageSize, page * pageSize)
  res.json({ success: true, data: { articles, total, page, pageSize, totalPages } })
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

app.post('/api/admin/login', loginLimiter, async (req, res) => {
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
  await markMessageRead(req.params.id, Boolean(req.body?.read))
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

app.get('/api/admin/articles', requireAuth, async (_req, res) => {
  const articles = await getAllArticlesAdmin()
  res.json({ success: true, data: articles })
})

app.post('/api/admin/articles', requireAuth, async (req, res) => {
  const { title, content, summary, type, tags, coverImage, published } = req.body || {}
  try {
    const article = await createArticle({ title, content, summary, type, tags, coverImage, published })
    res.json({ success: true, message: '文章已创建', data: article })
  } catch (err) {
    res.status(400).json({ success: false, message: err.message || '创建失败' })
  }
})

app.put('/api/admin/articles/:id', requireAuth, async (req, res) => {
  const { title, content, summary, type, tags, coverImage, published } = req.body || {}
  const article = await updateArticle(req.params.id, { title, content, summary, type, tags, coverImage, published })
  if (!article) {
    return res.status(404).json({ success: false, message: '文章不存在' })
  }
  res.json({ success: true, message: '文章已更新', data: article })
})

app.delete('/api/admin/articles/:id', requireAuth, async (req, res) => {
  const ok = await deleteArticle(req.params.id)
  if (!ok) {
    return res.status(404).json({ success: false, message: '文章不存在' })
  }
  res.json({ success: true, message: '文章已删除' })
})

// Upload a raw .md file — body is raw text, filename passed as query param
app.post('/api/admin/articles/upload', requireAuth, express.text({ type: '*/*', limit: '2mb' }), async (req, res) => {
  const filename = String(req.query.filename || '').trim()
  if (!filename) {
    return res.status(400).json({ success: false, message: '请提供文件名 ?filename=xxx.md' })
  }
  if (!filename.endsWith('.md')) {
    return res.status(400).json({ success: false, message: '只支持 .md 文件' })
  }
  const content = req.body
  if (!content || typeof content !== 'string' || !content.trim()) {
    return res.status(400).json({ success: false, message: '文件内容为空' })
  }
  try {
    const id = await saveArticleFile(filename, content)
    res.json({ success: true, message: '文件已上传', data: { id } })
  } catch (err) {
    res.status(500).json({ success: false, message: err.message || '上传失败' })
  }
})

// Image upload — accepts raw binary body, filename in query param
app.post('/api/admin/upload/image', requireAuth, express.raw({ type: ['image/*'], limit: '10mb' }), async (req, res) => {
  const original = String(req.query.filename || '').trim()
  if (!original) {
    return res.status(400).json({ success: false, message: '请提供文件名 ?filename=xxx.jpg' })
  }
  const ext = path.extname(original).toLowerCase()
  const allowed = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']
  if (!allowed.includes(ext)) {
    return res.status(400).json({ success: false, message: '仅支持 jpg/png/gif/webp/avif 格式' })
  }
  if (!Buffer.isBuffer(req.body) || req.body.length === 0) {
    return res.status(400).json({ success: false, message: '文件内容为空' })
  }
  const hash = crypto.createHash('sha1').update(req.body).digest('hex').slice(0, 8)
  const filename = `${Date.now()}_${hash}${ext}`
  const dest = path.join(uploadsDir, filename)
  try {
    await fs.writeFile(dest, req.body)
    res.json({ success: true, url: `/uploads/${filename}` })
  } catch (err) {
    res.status(500).json({ success: false, message: '保存失败' })
  }
})

app.use(express.static(distDir))
app.use('/uploads', express.static(uploadsDir))
app.use((req, res) => {
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ success: false, message: '接口不存在' })
  }
  res.sendFile(path.join(distDir, 'index.html'))
})

app.listen(port, host, () => {
  console.log(`czl-web server listening on ${siteUrl}`)
})
