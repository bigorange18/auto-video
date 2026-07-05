import { marked } from 'marked'
import hljs from 'highlight.js'

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(code, { language: lang }).value } catch {}
    }
    try { return hljs.highlightAuto(code).value } catch { return code }
  },
  breaks: true,
  gfm: true,
})

export function renderMarkdown(content) {
  if (!content) return ''
  return marked.parse(content)
}
