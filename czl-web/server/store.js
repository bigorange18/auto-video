import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import matter from 'gray-matter'

const dataDir = path.resolve(process.cwd(), 'data')
const postsDir = path.resolve(process.cwd(), 'content', 'posts')

async function ensurePostsDir() {
  if (!existsSync(postsDir)) {
    await fs.mkdir(postsDir, { recursive: true })
  }
}

// Short-lived in-memory cache to avoid re-reading disk on every request
let _postsCache = null
let _postsCacheAt = 0
const POSTS_CACHE_TTL = 3000 // 3 seconds

function invalidatePostsCache() {
  _postsCache = null
  _postsCacheAt = 0
}

function idToFilename(id) {
  // Sanitize id to safe filename chars
  return `${id.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`
}

function filenameToId(filename) {
  return filename.replace(/\.md$/, '')
}

function articleToMd(article) {
  const { content, id, ...frontmatter } = article
  // gray-matter stringify: first arg is body, second is data
  return matter.stringify(content || '', frontmatter)
}

async function readAllPosts(force = false) {
  const now = Date.now()
  if (!force && _postsCache && now - _postsCacheAt < POSTS_CACHE_TTL) {
    return _postsCache
  }
  await ensurePostsDir()
  let files
  try {
    files = await fs.readdir(postsDir)
  } catch {
    return []
  }
  const mdFiles = files.filter((f) => f.endsWith('.md'))
  const articles = []
  for (const file of mdFiles) {
    try {
      const raw = await fs.readFile(path.join(postsDir, file), 'utf8')
      const parsed = matter(raw)
      const d = parsed.data || {}
      const mapped = chineseTypeMap[d.type] || d.type
      const type = allowedEnglishTypes.includes(mapped) ? mapped : 'blog'
      const tags = Array.isArray(d.tags)
        ? d.tags.map((t) => String(t).trim()).filter(Boolean)
        : typeof d.tags === 'string'
          ? d.tags.split(',').map((t) => t.trim()).filter(Boolean)
          : []
      articles.push({
        id: filenameToId(file),
        title: String(d.title || '').trim(),
        summary: String(d.summary || '').trim(),
        type,
        tags,
        coverImage: String(d.coverImage || '').trim(),
        published: d.published !== false,
        createdAt: d.createdAt ? new Date(d.createdAt).toISOString() : new Date().toISOString(),
        updatedAt: d.updatedAt ? new Date(d.updatedAt).toISOString() : new Date().toISOString(),
        content: parsed.content.trim(),
      })
    } catch {
      // skip malformed files silently
    }
  }
  articles.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  _postsCache = articles
  _postsCacheAt = now
  return articles
}

function resolveFile(name) {
  return path.join(dataDir, name)
}

async function readJson(name, fallback) {
  try {
    const raw = await fs.readFile(resolveFile(name), 'utf8')
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

async function writeJson(name, value) {
  await fs.writeFile(resolveFile(name), JSON.stringify(value, null, 2), 'utf8')
}

function makeId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function getToday() {
  return new Date().toISOString().slice(0, 10)
}

function hashVisitor(input) {
  return crypto.createHash('sha256').update(input).digest('hex')
}

export async function getContent() {
  return readJson('content.json', {})
}

export async function saveContent(nextContent) {
  await writeJson('content.json', nextContent)
  return nextContent
}

export async function getMessages() {
  const messages = await readJson('messages.json', [])
  return [...messages].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

export async function addMessage(payload) {
  const messages = await readJson('messages.json', [])
  const nextMessage = {
    id: makeId('msg'),
    name: payload.name,
    email: payload.email,
    body: payload.body,
    read: false,
    createdAt: new Date().toISOString(),
  }
  messages.push(nextMessage)
  await writeJson('messages.json', messages)
  return nextMessage
}

export async function markMessageRead(id, read) {
  const messages = await readJson('messages.json', [])
  const nextMessages = messages.map((message) =>
    message.id === id ? { ...message, read } : message,
  )
  await writeJson('messages.json', nextMessages)
}

export async function deleteMessage(id) {
  const messages = await readJson('messages.json', [])
  const nextMessages = messages.filter((message) => message.id !== id)
  await writeJson('messages.json', nextMessages)
}

export async function getAdmin() {
  return readJson('admin.json', {})
}

export async function getStats() {
  return readJson('stats.json', {})
}

export async function trackVisit(ip, userAgent) {
  const stats = await readJson('stats.json', {})
  const today = getToday()
  const visitorKey = hashVisitor(`${ip}:${userAgent}`)
  const current = stats[today] || { pv: 0, uv: [] }
  current.pv += 1
  if (!current.uv.includes(visitorKey)) {
    current.uv.push(visitorKey)
  }
  stats[today] = current
  await writeJson('stats.json', stats)
  return stats
}

function normalizeTask(raw = {}) {
  const status = ['todo', 'in_progress', 'done'].includes(raw.status) ? raw.status : 'todo'
  const priority = ['low', 'medium', 'high'].includes(raw.priority) ? raw.priority : 'medium'
  const tags = Array.isArray(raw.tags)
    ? raw.tags.map((item) => String(item).trim()).filter(Boolean).slice(0, 8)
    : []
  return {
    id: raw.id || makeId('task'),
    title: String(raw.title || '').trim(),
    project: String(raw.project || '').trim(),
    priority,
    status,
    dueDate: String(raw.dueDate || '').trim(),
    tags,
    notes: String(raw.notes || '').trim(),
    createdAt: raw.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export async function getTasks() {
  const tasks = await readJson('tasks.json', [])
  return [...tasks].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

export async function addTask(payload) {
  const tasks = await readJson('tasks.json', [])
  const nextTask = normalizeTask(payload)
  tasks.push(nextTask)
  await writeJson('tasks.json', tasks)
  return nextTask
}

export async function updateTask(id, payload = {}) {
  const tasks = await readJson('tasks.json', [])
  let updated = null
  const nextTasks = tasks.map((task) => {
    if (task.id !== id) {
      return task
    }
    updated = normalizeTask({ ...task, ...payload, id: task.id, createdAt: task.createdAt })
    return updated
  })
  await writeJson('tasks.json', nextTasks)
  return updated
}

export async function deleteTask(id) {
  const tasks = await readJson('tasks.json', [])
  const nextTasks = tasks.filter((task) => task.id !== id)
  await writeJson('tasks.json', nextTasks)
}

const chineseTypeMap = { '博客': 'blog', '生活': 'life', '摄影': 'photo' }
const allowedEnglishTypes = ['blog', 'life', 'photo']

export async function getAllArticlesAdmin() {
  return readAllPosts(true)
}

export async function createArticle(data = {}) {
  if (!String(data.title || '').trim()) throw new Error('文章标题不能为空')
  if (!String(data.content || '').trim()) throw new Error('文章内容不能为空')
  await ensurePostsDir()
  const id = makeId('art')
  const now = new Date().toISOString()
  const mapped = chineseTypeMap[data.type] || data.type
  const type = allowedEnglishTypes.includes(mapped) ? mapped : 'blog'
  const tags = Array.isArray(data.tags)
    ? data.tags.map((t) => String(t).trim()).filter(Boolean)
    : typeof data.tags === 'string'
      ? data.tags.split(',').map((t) => t.trim()).filter(Boolean)
      : []
  const article = {
    id,
    title: String(data.title).trim(),
    summary: String(data.summary || '').trim(),
    type,
    tags,
    coverImage: String(data.coverImage || '').trim(),
    published: data.published !== false,
    createdAt: now,
    updatedAt: now,
    content: String(data.content).trim(),
  }
  const md = articleToMd(article)
  await fs.writeFile(path.join(postsDir, idToFilename(id)), md, 'utf8')
  invalidatePostsCache()
  return article
}

export async function updateArticle(id, data = {}) {
  const all = await readAllPosts(true)
  const existing = all.find((a) => a.id === id)
  if (!existing) return null
  const mapped = chineseTypeMap[data.type] || data.type
  const type = allowedEnglishTypes.includes(mapped) ? mapped : existing.type
  const tags = data.tags !== undefined
    ? (Array.isArray(data.tags)
        ? data.tags.map((t) => String(t).trim()).filter(Boolean)
        : String(data.tags).split(',').map((t) => t.trim()).filter(Boolean))
    : existing.tags
  const updated = {
    ...existing,
    title: data.title !== undefined ? String(data.title).trim() : existing.title,
    summary: data.summary !== undefined ? String(data.summary).trim() : existing.summary,
    type,
    tags,
    coverImage: data.coverImage !== undefined ? String(data.coverImage).trim() : existing.coverImage,
    published: data.published !== undefined ? (data.published !== false && data.published !== 'false') : existing.published,
    content: data.content !== undefined ? String(data.content).trim() : existing.content,
    updatedAt: new Date().toISOString(),
  }
  const md = articleToMd(updated)
  await fs.writeFile(path.join(postsDir, idToFilename(id)), md, 'utf8')
  invalidatePostsCache()
  return updated
}

export async function deleteArticle(id) {
  const filePath = path.join(postsDir, idToFilename(id))
  try {
    await fs.unlink(filePath)
    invalidatePostsCache()
    return true
  } catch {
    return false
  }
}

export async function getArticles() {
  const all = await readAllPosts()
  return all.filter((a) => a.published !== false)
}

export async function getArticleById(id) {
  const all = await readAllPosts()
  return all.find((a) => a.id === id && a.published !== false) || null
}

// Save a raw .md file directly (used by file upload endpoint)
export async function saveArticleFile(filename, content) {
  await ensurePostsDir()
  // Sanitize filename
  const safe = path.basename(filename).replace(/[^a-zA-Z0-9_.-]/g, '_')
  const dest = path.join(postsDir, safe.endsWith('.md') ? safe : `${safe}.md`)
  await fs.writeFile(dest, content, 'utf8')
  invalidatePostsCache()
  return filenameToId(path.basename(dest))
}

export async function getPublicStats() {
  const stats = await readJson('stats.json', {})
  const articles = await getArticles()
  const content = await readJson('content.json', {})

  let totalPV = 0
  const allUVs = new Set()
  const dates = Object.keys(stats).sort()

  Object.values(stats).forEach((day) => {
    totalPV += day.pv || 0
    if (Array.isArray(day.uv)) day.uv.forEach((u) => allUVs.add(u))
  })

  const today = getToday()
  const todayData = stats[today] || { pv: 0 }

  let runningDays = 0
  if (dates.length > 0) {
    runningDays = Math.max(1, Math.floor((Date.now() - new Date(dates[0]).getTime()) / 86400000) + 1)
  }

  return {
    articleCount: articles.filter((a) => a.published !== false).length,
    totalPV,
    totalUV: allUVs.size,
    runningDays,
    todayPV: todayData.pv || 0,
    site: content.site || {},
    intro: content.intro || {},
  }
}

export async function getTaskSummary() {
  const tasks = await readJson('tasks.json', [])
  const status = { todo: 0, in_progress: 0, done: 0 }
  const priority = { high: 0, medium: 0, low: 0 }
  let overdue = 0

  const now = new Date()
  tasks.forEach((task) => {
    const taskStatus = ['todo', 'in_progress', 'done'].includes(task.status) ? task.status : 'todo'
    const taskPriority = ['high', 'medium', 'low'].includes(task.priority) ? task.priority : 'medium'
    status[taskStatus] += 1
    priority[taskPriority] += 1
    if (task.dueDate && taskStatus !== 'done') {
      const due = new Date(task.dueDate)
      if (!Number.isNaN(due.getTime()) && due < now) {
        overdue += 1
      }
    }
  })

  return {
    total: tasks.length,
    status,
    priority,
    overdue,
  }
}
