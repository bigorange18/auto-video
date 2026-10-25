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
let _postsErrors = []
const POSTS_CACHE_TTL = 3000 // 3 seconds
const writeQueues = new Map()

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
    _postsErrors = []
    return []
  }
  const mdFiles = files.filter((f) => f.endsWith('.md'))
  const articles = []
  const errors = []
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
    } catch (error) {
      errors.push({
        file,
        message: error instanceof Error ? error.message : String(error),
      })
    }
  }
  articles.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  _postsCache = articles
  _postsCacheAt = now
  _postsErrors = errors
  return articles
}

export async function getArticleWarnings() {
  await readAllPosts(true)
  return [..._postsErrors]
}

function resolveFile(name) {
  return path.join(dataDir, name)
}

function withWriteQueue(key, task) {
  const previous = writeQueues.get(key) || Promise.resolve()
  const pending = previous.catch(() => undefined).then(task)
  writeQueues.set(key, pending)

  return pending.finally(() => {
    if (writeQueues.get(key) === pending) {
      writeQueues.delete(key)
    }
  })
}

async function readJson(name, fallback) {
  try {
    const raw = await fs.readFile(resolveFile(name), 'utf8')
    return JSON.parse(raw) ?? fallback
  } catch {
    return fallback
  }
}

async function writeJson(name, value) {
  await fs.mkdir(dataDir, { recursive: true })
  const target = resolveFile(name)
  const temp = path.join(
    dataDir,
    `.${path.basename(name)}.${process.pid}.${crypto.randomBytes(6).toString('hex')}.tmp`,
  )
  await fs.writeFile(temp, JSON.stringify(value, null, 2), 'utf8')
  try {
    await fs.rename(temp, target)
  } catch (error) {
    await fs.rm(temp, { force: true })
    throw error
  }
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
  return withWriteQueue('content.json', async () => {
    await writeJson('content.json', nextContent)
    return nextContent
  })
}

export async function getMessages() {
  const messages = await readJson('messages.json', [])
  return [...messages].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

export async function addMessage(payload) {
  return withWriteQueue('messages.json', async () => {
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
  })
}

export async function markMessageRead(id, read) {
  return withWriteQueue('messages.json', async () => {
    const messages = await readJson('messages.json', [])
    const nextMessages = messages.map((message) =>
      message.id === id ? { ...message, read } : message,
    )
    await writeJson('messages.json', nextMessages)
  })
}

export async function deleteMessage(id) {
  return withWriteQueue('messages.json', async () => {
    const messages = await readJson('messages.json', [])
    const nextMessages = messages.filter((message) => message.id !== id)
    await writeJson('messages.json', nextMessages)
  })
}

export async function getAdmin() {
  return readJson('admin.json', {})
}

export async function getStats() {
  return readJson('stats.json', {})
}

export async function trackVisit(ip, userAgent) {
  return withWriteQueue('stats.json', async () => {
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
  })
}

function normalizeTask(raw = {}) {
  const status = ['todo', 'in_progress', 'done'].includes(raw.status) ? raw.status : 'todo'
  const priority = ['low', 'medium', 'high'].includes(raw.priority) ? raw.priority : 'medium'
  const visibility = ['private', 'public'].includes(raw.visibility) ? raw.visibility : 'private'
  const tags = Array.isArray(raw.tags)
    ? raw.tags.map((item) => String(item).trim()).filter(Boolean).slice(0, 8)
    : []
  return {
    id: raw.id || makeId('task'),
    title: String(raw.title || '').trim(),
    externalId: String(raw.externalId || '').trim(),
    projectSlug: String(raw.projectSlug || '').trim(),
    visibility,
    priority,
    status,
    dueDate: String(raw.dueDate || '').trim(),
    tags,
    notes: String(raw.notes || '').trim(),
    createdAt: raw.createdAt || new Date().toISOString(),
    updatedAt: raw.updatedAt || new Date().toISOString(),
  }
}

export async function getTasks() {
  const tasks = await readJson('tasks.json', [])
  return tasks
    .map((task) => normalizeTask(task))
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

export function toPublicTask(task) {
  const normalized = normalizeTask(task)
  return {
    id: normalized.id,
    title: normalized.title,
    projectSlug: normalized.projectSlug,
    priority: normalized.priority,
    status: normalized.status,
    dueDate: normalized.dueDate,
    tags: normalized.tags,
    createdAt: normalized.createdAt,
    updatedAt: normalized.updatedAt,
  }
}

export function filterPublicTasks(tasks, { projectSlug = '', status = 'all' } = {}) {
  return tasks
    .map((task) => normalizeTask(task))
    .filter((task) => task.visibility === 'public')
    .filter((task) => !projectSlug || task.projectSlug === projectSlug)
    .filter((task) => status === 'all' || task.status === status)
    .map(toPublicTask)
}

export async function getPublicTasks(filters = {}) {
  return filterPublicTasks(await getTasks(), filters)
}

export async function addTask(payload) {
  return withWriteQueue('tasks.json', async () => {
    const tasks = await readJson('tasks.json', [])
    const nextTask = normalizeTask(payload)
    tasks.push(nextTask)
    await writeJson('tasks.json', tasks)
    return nextTask
  })
}

export function mergeTask(existing, payload = {}, now = new Date().toISOString()) {
  return normalizeTask({
    ...existing,
    ...payload,
    id: existing?.id || makeId('task'),
    createdAt: existing?.createdAt || now,
    updatedAt: now,
  })
}

export async function upsertTask(payload = {}) {
  return withWriteQueue('tasks.json', async () => {
    const tasks = await readJson('tasks.json', [])
    const externalId = String(payload.externalId || '').trim()
    const index = tasks.findIndex((task) => task.externalId === externalId)
    const existing = index >= 0 ? tasks[index] : null
    const task = mergeTask(existing, payload)

    if (index >= 0) {
      tasks[index] = task
    } else {
      tasks.push(task)
    }
    await writeJson('tasks.json', tasks)
    return { task, created: !existing }
  })
}

export async function updateTask(id, payload = {}) {
  return withWriteQueue('tasks.json', async () => {
    const tasks = await readJson('tasks.json', [])
    let updated = null
    const nextTasks = tasks.map((task) => {
      if (task.id !== id) {
        return task
      }
      updated = normalizeTask({
        ...task,
        ...payload,
        id: task.id,
        createdAt: task.createdAt,
        updatedAt: new Date().toISOString(),
      })
      return updated
    })
    await writeJson('tasks.json', nextTasks)
    return updated
  })
}

export async function deleteTask(id) {
  return withWriteQueue('tasks.json', async () => {
    const tasks = await readJson('tasks.json', [])
    const nextTasks = tasks.filter((task) => task.id !== id)
    await writeJson('tasks.json', nextTasks)
  })
}

const chineseTypeMap = { '博客': 'blog', '生活': 'life', '摄影': 'photo' }
const allowedEnglishTypes = ['blog', 'life', 'photo']

export async function getAllArticlesAdmin() {
  return readAllPosts(true)
}

export async function createArticle(data = {}) {
  if (!String(data.title || '').trim()) throw new Error('文章标题不能为空')
  if (!String(data.content || '').trim()) throw new Error('文章内容不能为空')
  return withWriteQueue('articles', async () => {
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
  })
}

export async function updateArticle(id, data = {}) {
  return withWriteQueue('articles', async () => {
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
  })
}

export async function deleteArticle(id) {
  return withWriteQueue('articles', async () => {
    const filePath = path.join(postsDir, idToFilename(id))
    try {
      await fs.unlink(filePath)
      invalidatePostsCache()
      return true
    } catch {
      return false
    }
  })
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
export async function saveArticleFile(filename, content, { overwrite = false } = {}) {
  return withWriteQueue('articles', async () => {
    await ensurePostsDir()
    // Sanitize filename
    const safe = path.basename(filename).replace(/[^a-zA-Z0-9_.-]/g, '_')
    const dest = path.join(postsDir, safe.endsWith('.md') ? safe : `${safe}.md`)
    if (!overwrite) {
      try {
        await fs.access(dest)
        return { conflict: true, id: filenameToId(path.basename(dest)) }
      } catch (error) {
        if (error?.code !== 'ENOENT') throw error
      }
    }
    await fs.writeFile(dest, content, 'utf8')
    invalidatePostsCache()
    return { conflict: false, id: filenameToId(path.basename(dest)) }
  })
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
