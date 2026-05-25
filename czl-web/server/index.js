import path from 'node:path'
import bcrypt from 'bcryptjs'
import express from 'express'
import session from 'express-session'
import {
  addMessage,
  deleteMessage,
  getAdmin,
  getContent,
  getMessages,
  getStats,
  markMessageRead,
  saveContent,
  trackVisit,
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

app.post('/api/public/messages', async (req, res) => {
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
