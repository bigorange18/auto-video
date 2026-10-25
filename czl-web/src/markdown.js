import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import DOMPurify from 'dompurify'
import bash from 'highlight.js/lib/languages/bash'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('css', css)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('python', python)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)

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

  const stash = []

  let text = content

  // 1) 保护 $$ 块级公式
  //    marked 会把 $$ 里的换行变 <br>，下划线变 <em>
  //    用不可见的 span 占位，marked 不会碰 HTML 标签
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, formula) => {
    stash.push({ type: 'block', formula })
    return `<span data-kb="${stash.length - 1}"></span>`
  })

  // 2) 保护 $ 行内公式
  text = text.replace(/(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)/g, (_, formula) => {
    stash.push({ type: 'inline', formula })
    return `<span data-ki="${stash.length - 1}"></span>`
  })

  // 3) 渲染 markdown
  let html = marked.parse(text)

  // 4) 还原公式
  stash.forEach((item, i) => {
    const search = item.type === 'block'
      ? `<span data-kb="${i}"></span>`
      : `<span data-ki="${i}"></span>`
    const replacement = item.type === 'block'
      ? `$$${item.formula}$$`
      : `$${item.formula}$`
    html = html.split(search).join(replacement)
  })

  // 5) 块级公式不能被 <p> 包裹（KaTeX 无法渲染），去掉外层 <p>
  html = html.replace(/<p>\$\$([\s\S]*?)\$\$<\/p>/g, (_, formula) => {
    return `<div class="math-block">$$${formula}$$</div>`
  })

  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  })
}
