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
