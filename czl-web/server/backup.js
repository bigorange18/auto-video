import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backupRoot = path.resolve(
  process.env.BACKUP_DIR || path.join(rootDir, '..', 'backups', 'czl-web'),
)
const keepDays = Math.max(1, Number(process.env.BACKUP_KEEP_DAYS) || 30)
const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
const destination = path.join(backupRoot, timestamp)
const sources = [
  { label: 'data', path: path.join(rootDir, 'data') },
  { label: 'content-posts', path: path.join(rootDir, 'content', 'posts') },
  { label: 'uploads', path: path.join(rootDir, 'public', 'uploads') },
]

if (path.parse(backupRoot).root === backupRoot) {
  throw new Error('BACKUP_DIR must not be a filesystem root')
}

await fs.mkdir(destination, { recursive: true })

const copied = []
for (const source of sources) {
  try {
    await fs.access(source.path)
    await fs.cp(source.path, path.join(destination, source.label), {
      recursive: true,
      force: true,
    })
    copied.push(source.label)
  } catch (error) {
    if (error?.code === 'ENOENT') continue
    throw error
  }
}

await fs.writeFile(
  path.join(destination, 'manifest.json'),
  JSON.stringify({
    createdAt: new Date().toISOString(),
    sources: copied,
    rootDir,
  }, null, 2),
)

const cutoff = Date.now() - keepDays * 24 * 60 * 60 * 1000
for (const entry of await fs.readdir(backupRoot, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue
  const target = path.join(backupRoot, entry.name)
  if (target === destination) continue
  const stats = await fs.stat(target)
  if (stats.mtimeMs < cutoff) {
    await fs.rm(target, { recursive: true, force: true })
  }
}

console.log(`backup created: ${destination}`)
