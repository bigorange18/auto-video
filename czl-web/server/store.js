import crypto from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'

const dataDir = path.resolve(process.cwd(), 'data')

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
