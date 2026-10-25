/**
 * useMeta — update <head> meta tags for Open Graph, Twitter Card, and SEO.
 * Works in a pure SPA (no SSR). Creates tags if they don't exist yet.
 */
export function useMeta({ title, description, image = '', url = '', type = 'website' }) {
  document.querySelectorAll('meta[property^="article:"]').forEach((el) => el.remove())

  // --- helpers ---
  function setMeta(selector, attr, value) {
    let el = document.querySelector(selector)
    if (!el) {
      el = document.createElement('meta')
      // parse the attribute key/value from the selector, e.g. [property="og:title"]
      const match = selector.match(/\[(\w+)="([^"]+)"\]/)
      if (match) el.setAttribute(match[1], match[2])
      document.head.appendChild(el)
    }
    el.setAttribute(attr, value ?? '')
  }

  function setLink(rel, href) {
    let el = document.querySelector(`link[rel="${rel}"]`)
    if (!el) {
      el = document.createElement('link')
      el.setAttribute('rel', rel)
      document.head.appendChild(el)
    }
    el.setAttribute('href', href ?? '')
  }

  // --- document title ---
  if (title) document.title = title

  // --- Open Graph ---
  setMeta('[property="og:title"]',       'content', title)
  setMeta('[property="og:description"]', 'content', description)
  setMeta('[property="og:image"]',       'content', image)
  setMeta('[property="og:url"]',         'content', url)
  setMeta('[property="og:type"]',        'content', type)

  // --- Twitter Card ---
  setMeta('[name="twitter:title"]',       'content', title)
  setMeta('[name="twitter:description"]', 'content', description)
  setMeta('[name="twitter:image"]',       'content', image)

  // --- General description ---
  setMeta('[name="description"]', 'content', description)

  // --- Canonical link ---
  if (url) setLink('canonical', url)
}

/**
 * setArticleMeta — add article-specific OG tags on top of useMeta.
 */
export function setArticleMeta({ publishedTime, tags = [] }) {
  function setMeta(selector, attr, value) {
    let el = document.querySelector(selector)
    if (!el) {
      el = document.createElement('meta')
      const match = selector.match(/\[(\w+)="([^"]+)"\]/)
      if (match) el.setAttribute(match[1], match[2])
      document.head.appendChild(el)
    }
    el.setAttribute(attr, value ?? '')
  }

  if (publishedTime) {
    setMeta('[property="article:published_time"]', 'content', publishedTime)
  }

  // Remove previous article:tag metas before re-adding
  document.querySelectorAll('meta[property="article:tag"]').forEach(el => el.remove())
  tags.forEach(tag => {
    const el = document.createElement('meta')
    el.setAttribute('property', 'article:tag')
    el.setAttribute('content', tag)
    document.head.appendChild(el)
  })
}
