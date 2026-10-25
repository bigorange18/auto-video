export const PROJECT_STATUSES = ['active', 'maintained', 'planned', 'archived']
export const PROJECT_CATEGORIES = ['web', 'ai', 'content', 'ops', 'learning', 'other']

function cleanText(value) {
  return String(value ?? '').trim()
}

function cleanUrl(value) {
  const raw = cleanText(value)
  if (!raw) return ''
  if (raw.startsWith('/') || raw.startsWith('#')) return raw

  try {
    const parsed = new URL(raw)
    return ['http:', 'https:'].includes(parsed.protocol) ? raw : ''
  } catch {
    return ''
  }
}

function cleanList(value) {
  const source = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.split(',')
      : []
  return [...new Set(source.map(cleanText).filter(Boolean))]
}

function slugify(value) {
  return cleanText(value)
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function normalizeProject(raw = {}, index = 0) {
  const name = cleanText(raw.name ?? raw.title)
  const summary = cleanText(raw.summary ?? raw.desc)
  const description = cleanText(raw.description ?? raw.desc)
  const status = PROJECT_STATUSES.includes(raw.status) ? raw.status : 'active'
  const category = PROJECT_CATEGORIES.includes(raw.category) ? raw.category : 'other'

  return {
    slug: cleanText(raw.slug) || slugify(name) || `project-${index + 1}`,
    name,
    category,
    summary: summary || description,
    description,
    stack: cleanList(raw.stack ?? raw.tech),
    repoUrl: cleanUrl(raw.repoUrl ?? raw.github),
    demoUrl: cleanUrl(raw.demoUrl ?? raw.url ?? raw.link),
    status,
    featured: raw.featured === true || raw.featured === 'true',
  }
}

export function normalizeProjects(value) {
  if (!Array.isArray(value)) return []
  return value.map((project, index) => normalizeProject(project, index))
}
