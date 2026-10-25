import 'dotenv/config'
import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import crypto from 'node:crypto'
import bcrypt from 'bcryptjs'
import express from 'express'
import session from 'cookie-session'
import { normalizeProjects } from '../shared/projectSchema.js'
import {
  addTask,
  addMessage,
  createArticle,
  deleteArticle,
  deleteTask,
  deleteMessage,
  getAdmin,
  getAllArticlesAdmin,
  getArticleWarnings,
  getArticleById,
  getArticles,
  getContent,
  getMessages,
  getPublicTasks,
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
  upsertTask,
} from './store.js'

// Simple in-memory rate limiter
function makeRateLimiter(maxRequests, windowMs) {
  const map = new Map()
  return function (req, res, next) {
    const ip = req.ip || 'unknown'
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
const tasksWriteLimiter = makeRateLimiter(60, 60 * 1000)      // 60/min
const visitLimiter = makeRateLimiter(120, 60 * 1000)          // 120/min

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
const sessionSecret = process.env.SESSION_SECRET
const tasksApiToken = String(process.env.TASKS_API_TOKEN || '').trim()
const rootDir = process.cwd()
const distDir = path.join(rootDir, 'dist')
const uploadsDir = path.join(rootDir, 'public', 'uploads')
const canonicalSiteUrl = siteUrl.replace(/\/+$/, '')
const allowedOrigins = new Set()

try {
  allowedOrigins.add(new URL(canonicalSiteUrl).origin)
} catch {
  throw new Error('SITE_URL must be a valid absolute URL')
}

for (const origin of String(process.env.ALLOWED_ORIGINS || '').split(',')) {
  const value = origin.trim()
  if (!value) continue
  try {
    allowedOrigins.add(new URL(value).origin)
  } catch {
    throw new Error(`Invalid ALLOWED_ORIGINS entry: ${value}`)
  }
}

// Ensure uploads directory exists
if (!existsSync(uploadsDir)) {
  fs.mkdir(uploadsDir, { recursive: true }).catch(() => {})
}

if (trustProxy) {
  app.set('trust proxy', 1)
}

if (!sessionSecret) {
  throw new Error('SESSION_SECRET is required')
}

app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('X-Frame-Options', 'DENY')
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin')
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
  res.setHeader(
    'Content-Security-Policy',
    [
      "default-src 'self'",
      "base-uri 'self'",
      "connect-src 'self'",
      "font-src 'self' data:",
      "form-action 'self'",
      "frame-ancestors 'none'",
      "img-src 'self' data: https:",
      "object-src 'none'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
    ].join('; '),
  )
  if (cookieSecure) {
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
  }
  next()
})

app.use(['/api/admin', '/api/integration'], (_req, res, next) => {
  res.setHeader('Cache-Control', 'no-store')
  res.setHeader('Pragma', 'no-cache')
  res.setHeader('Expires', '0')
  next()
})

app.use(express.json())
app.use(
  session({
    name: 'czl_web_session',
    secret: sessionSecret,
    maxAge: 1000 * 60 * 60 * 8,
    httpOnly: true,
    sameSite: 'lax',
    secure: cookieSecure,
    path: '/',
  }),
)

const mutationMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function requireSameOrigin(req, res, next) {
  if (!mutationMethods.has(req.method)) return next()

  const fetchSite = String(req.headers['sec-fetch-site'] || '')
  if (fetchSite && !['same-origin', 'none'].includes(fetchSite)) {
    return res.status(403).json({ success: false, message: '拒绝跨站请求' })
  }

  const origin = req.headers.origin
  if (!origin) return next()

  try {
    if (!allowedOrigins.has(new URL(origin).origin)) {
      return res.status(403).json({ success: false, message: '请求来源不受信任' })
    }
  } catch {
    return res.status(403).json({ success: false, message: '请求来源无效' })
  }

  next()
}

function requireAuth(req, res, next) {
  if (!req.session.user) {
    return res.status(401).json({ success: false, message: '未登录' })
  }
  next()
}

function requireTasksApiToken(req, res, next) {
  if (!tasksApiToken) {
    return res.status(503).json({ success: false, message: '任务写入接口未启用' })
  }

  const authorization = String(req.headers.authorization || '')
  const match = authorization.match(/^Bearer\s+(.+)$/i)
  if (!match) {
    return res.status(401).json({ success: false, message: '缺少任务写入令牌' })
  }

  const provided = Buffer.from(match[1])
  const expected = Buffer.from(tasksApiToken)
  if (provided.length !== expected.length || !crypto.timingSafeEqual(provided, expected)) {
    return res.status(401).json({ success: false, message: '任务写入令牌无效' })
  }

  next()
}

app.use('/api/admin', requireSameOrigin)

function sanitizeContent(raw) {
  return {
    site: raw.site || {},
    intro: raw.intro || {},
    skills: Array.isArray(raw.skills) ? raw.skills : [],
    projects: normalizeProjects(raw.projects),
    contact: raw.contact || {},
  }
}

let indexTemplateCache = {
  mtimeMs: 0,
  html: '',
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function escapeXml(value) {
  return escapeHtml(value)
}

function absoluteUrl(value, fallback = '') {
  const raw = String(value || fallback || '').trim()
  if (!raw) return canonicalSiteUrl
  try {
    return new URL(raw, `${canonicalSiteUrl}/`).toString()
  } catch {
    return canonicalSiteUrl
  }
}

async function getIndexTemplate() {
  const filePath = path.join(distDir, 'index.html')
  const stats = await fs.stat(filePath)
  if (!indexTemplateCache.html || stats.mtimeMs !== indexTemplateCache.mtimeMs) {
    indexTemplateCache = {
      mtimeMs: stats.mtimeMs,
      html: await fs.readFile(filePath, 'utf8'),
    }
  }
  return indexTemplateCache.html
}

async function renderAppShell(meta = {}) {
  const template = await getIndexTemplate()
  const title = escapeHtml(meta.title || '大橘')
  const description = escapeHtml(meta.description || '把个人主页改造成持续更新的工作前台。')
  const url = escapeHtml(meta.url || canonicalSiteUrl)
  const image = meta.image ? escapeHtml(absoluteUrl(meta.image)) : ''
  const type = escapeHtml(meta.type || 'website')
  const robots = escapeHtml(meta.robots || 'index,follow')

  return template
    .replace(/<title>.*?<\/title>/s, `<title>${title}</title>`)
    .replace(
      /<meta name="description" content="[^"]*"\s*\/?>/,
      `<meta name="description" content="${description}" />`,
    )
    .replace(
      /<meta property="og:title" content="[^"]*"\s*\/?>/,
      `<meta property="og:title" content="${title}" />`,
    )
    .replace(
      /<meta property="og:description" content="[^"]*"\s*\/?>/,
      `<meta property="og:description" content="${description}" />`,
    )
    .replace(
      /<meta property="og:type" content="[^"]*"\s*\/?>/,
      `<meta property="og:type" content="${type}" />`,
    )
    .replace(
      /<meta property="og:image" content="[^"]*"\s*\/?>/,
      `<meta property="og:image" content="${image}" />`,
    )
    .replace(
      /<meta property="og:url" content="[^"]*"\s*\/?>/,
      `<meta property="og:url" content="${url}" />`,
    )
    .replace(
      /<meta name="twitter:title" content="[^"]*"\s*\/?>/,
      `<meta name="twitter:title" content="${title}" />`,
    )
    .replace(
      /<meta name="twitter:description" content="[^"]*"\s*\/?>/,
      `<meta name="twitter:description" content="${description}" />`,
    )
    .replace(
      /<meta name="twitter:image" content="[^"]*"\s*\/?>/,
      `<meta name="twitter:image" content="${image}" />`,
    )
    .replace(
      /<meta name="robots" content="[^"]*"\s*\/?>/,
      `<meta name="robots" content="${robots}" />`,
    )
    .replace(/<link rel="canonical" href="[^"]*"\s*\/?>/, `<link rel="canonical" href="${url}" />`)
}

app.get('/api/health', (_req, res) => {
  res.json({ success: true, data: { status: 'ok' } })
})

app.get('/api/public/content', async (req, res) => {
  const content = await getContent()
  res.json({ success: true, data: sanitizeContent(content) })
})

app.post('/api/public/visit', visitLimiter, async (req, res) => {
  await trackVisit(req.ip || 'unknown', req.headers['user-agent'] || 'unknown')
  res.status(204).end()
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

app.get('/api/public/tasks', async (req, res) => {
  const projectSlug = String(req.query.projectSlug || '').trim()
  const requestedStatus = String(req.query.status || 'all').trim()
  const status = ['all', 'todo', 'in_progress', 'done'].includes(requestedStatus)
    ? requestedStatus
    : 'all'
  const tasks = await getPublicTasks({ projectSlug, status })
  res.json({
    success: true,
    data: {
      tasks,
      total: tasks.length,
      filters: { projectSlug, status },
    },
  })
})

app.post(
  '/api/integration/tasks',
  tasksWriteLimiter,
  requireTasksApiToken,
  async (req, res) => {
    const payload = req.body || {}
    const externalId = String(payload.externalId || '').trim()
    const title = String(payload.title || '').trim()
    const projectSlug = String(payload.projectSlug || '').trim()

    if (!externalId || externalId.length > 128 || !/^[a-zA-Z0-9._:-]+$/.test(externalId)) {
      return res.status(400).json({
        success: false,
        message: 'externalId 必填，且只能包含字母、数字、点、下划线、冒号或连字符',
      })
    }
    if (!title) {
      return res.status(400).json({ success: false, message: '任务标题不能为空' })
    }
    if (payload.status && !['todo', 'in_progress', 'done'].includes(payload.status)) {
      return res.status(400).json({ success: false, message: '任务状态无效' })
    }
    if (payload.priority && !['low', 'medium', 'high'].includes(payload.priority)) {
      return res.status(400).json({ success: false, message: '任务优先级无效' })
    }
    if (payload.visibility && !['private', 'public'].includes(payload.visibility)) {
      return res.status(400).json({ success: false, message: '任务可见性无效' })
    }
    if (projectSlug) {
      const content = await getContent()
      const projects = normalizeProjects(content.projects)
      if (!projects.some((project) => project.slug === projectSlug)) {
        return res.status(400).json({ success: false, message: '关联项目不存在' })
      }
    }

    const taskPatch = { externalId, title }
    for (const field of [
      'projectSlug',
      'visibility',
      'status',
      'priority',
      'dueDate',
      'tags',
      'notes',
    ]) {
      if (Object.prototype.hasOwnProperty.call(payload, field)) {
        taskPatch[field] = payload[field]
      }
    }
    const result = await upsertTask(taskPatch)

    res.status(result.created ? 201 : 200).json({
      success: true,
      message: result.created ? '任务已创建' : '任务已更新',
      data: result,
    })
  },
)

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
  req.session = null
  res.json({ success: true })
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

app.get('/api/admin/articles/warnings', requireAuth, async (_req, res) => {
  const warnings = await getArticleWarnings()
  res.json({ success: true, data: warnings })
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
    const result = await saveArticleFile(filename, content, {
      overwrite: req.query.overwrite === 'true',
    })
    if (result.conflict) {
      return res.status(409).json({
        success: false,
        code: 'ARTICLE_EXISTS',
        message: '同名文章已存在，是否覆盖？',
      })
    }
    res.json({ success: true, message: '文件已上传', data: { id: result.id } })
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

const staticPageMeta = {
  '/': {
    title: '大橘 — 把个人主页改造成持续更新的工作前台。',
    description: '这里展示正在推进的项目、长期积累的技术文章，以及可持续维护的个人工作台。',
  },
  '/about': {
    title: '关于 — 大橘',
    description: '认识大橘，了解正在关注的技术方向和长期目标。',
  },
  '/projects': {
    title: '项目 — 大橘',
    description: '大橘正在推进的开源项目、个人作品和实践记录。',
  },
  '/tags': {
    title: '文章标签 — 大橘',
    description: '按标签浏览大橘的技术笔记和生活记录。',
  },
}

app.get('/sitemap.xml', async (_req, res) => {
  const articles = await getArticles()
  const staticPaths = ['/', '/about', '/projects', '/tags']
  const entries = [
    ...staticPaths.map((pathname) => ({
      loc: absoluteUrl(pathname),
      lastmod: new Date().toISOString().slice(0, 10),
    })),
    ...articles.map((article) => ({
      loc: absoluteUrl(`/article/${encodeURIComponent(article.id)}`),
      lastmod: String(article.updatedAt || article.createdAt || '').slice(0, 10),
    })),
  ]
  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...entries.map((entry) => [
      '  <url>',
      `    <loc>${escapeXml(entry.loc)}</loc>`,
      entry.lastmod ? `    <lastmod>${escapeXml(entry.lastmod)}</lastmod>` : '',
      '  </url>',
    ].filter(Boolean).join('\n')),
    '</urlset>',
  ].join('\n')

  res.type('application/xml').send(body)
})

app.get('/robots.txt', (_req, res) => {
  res.type('text/plain').send([
    'User-agent: *',
    'Allow: /',
    'Disallow: /admin',
    'Disallow: /api/',
    '',
    `Sitemap: ${canonicalSiteUrl}/sitemap.xml`,
    '',
  ].join('\n'))
})

app.get('/article/:id', async (req, res, next) => {
  try {
    const article = await getArticleById(req.params.id)
    if (!article) {
      const html = await renderAppShell({
        title: '文章不存在 — 大橘',
        description: '请求的文章不存在或尚未发布。',
        url: absoluteUrl(`/article/${encodeURIComponent(req.params.id)}`),
        robots: 'noindex,follow',
      })
      return res.status(404).type('html').send(html)
    }

    const description = (article.summary || article.content || '')
      .replace(/[#*_`>\[\]()!-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 160)
    const html = await renderAppShell({
      title: `${article.title} — 大橘`,
      description,
      image: article.coverImage,
      url: absoluteUrl(`/article/${encodeURIComponent(article.id)}`),
      type: 'article',
    })
    res.type('html').send(html)
  } catch (error) {
    next(error)
  }
})

app.get(['/', '/about', '/projects', '/tags'], async (req, res, next) => {
  try {
    const meta = staticPageMeta[req.path]
    const html = await renderAppShell({
      ...meta,
      url: absoluteUrl(req.path),
    })
    res.type('html').send(html)
  } catch (error) {
    next(error)
  }
})

app.get('/admin', async (_req, res, next) => {
  try {
    const html = await renderAppShell({
      title: '管理后台 — 大橘',
      description: '大橘个人站管理后台。',
      url: absoluteUrl('/admin'),
      robots: 'noindex,nofollow',
    })
    res.type('html').send(html)
  } catch (error) {
    next(error)
  }
})

app.use(express.static(distDir))
app.use('/uploads', express.static(uploadsDir))
app.use(async (req, res, next) => {
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ success: false, message: '接口不存在' })
  }
  try {
    const html = await renderAppShell({
      title: '页面不存在 — 大橘',
      description: '请求的页面不存在。',
      url: absoluteUrl(req.path),
      robots: 'noindex,follow',
    })
    res.status(404).type('html').send(html)
  } catch (error) {
    next(error)
  }
})

app.listen(port, host, () => {
  console.log(`czl-web server listening on ${siteUrl}`)
})
