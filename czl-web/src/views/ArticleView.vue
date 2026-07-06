<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { renderMarkdown } from '../markdown.js'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const error = ref('')
const labels = { blog: '博客', life: '生活', photo: '摄影' }
const html = computed(() => article.value ? renderMarkdown(article.value.content) : '')

/* ---- TOC ---- */
const toc = computed(() => {
  if (!article.value) return []
  const raw = article.value.content
  const re = /^(#{2,3})\s+(.+)$/gm
  const items = []
  let m
  while ((m = re.exec(raw)) !== null) {
    const level = m[1].length  // 2 or 3
    const text = m[2]
    // 生成 slug（和 marked 默认行为一致）
    const slug = text
      .toLowerCase()
      .replace(/[^\w一-鿿\s-]/g, '')
      .replace(/\s+/g, '-')
    items.push({ level, text, slug })
  }
  return items
})

/* ---- load ---- */
async function loadArticle() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/public/articles/${route.params.id}`)
    const d = await res.json()
    if (!d.success) error.value = d.message || '文章不存在'
    else { article.value = d.data; document.title = `${d.data.title} — 大橘` }
  } catch { error.value = '加载失败' }
  finally { loading.value = false }
}

/* ---- KaTeX ---- */
function renderMath() {
  nextTick(() => {
    const el = document.querySelector('.article-body')
    if (!el) return
    try {
      window.renderMathInElement?.(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      })
    } catch {}
  })
}
let _timer = null
watch(html, () => {
  clearInterval(_timer)
  let tries = 0
  _timer = setInterval(() => {
    if (window.renderMathInElement || window._katexReady || tries > 20) {
      clearInterval(_timer)
      renderMath()
    }
    tries++
  }, 150)
})

/* ---- TOC 高亮当前可见标题 ---- */
const activeSlug = ref('')
function onScroll() {
  const headings = document.querySelectorAll('.article-body h2, .article-body h3')
  let current = ''
  headings.forEach(h => {
    if (h.getBoundingClientRect().top <= 120) current = h.id
  })
  activeSlug.value = current
}

let _tocScrollHandler = null
watch(html, () => {
  nextTick(() => {
    window.removeEventListener('scroll', onScroll)
    window.addEventListener('scroll', onScroll, { passive: true })
    _tocScrollHandler = onScroll
  })
})

function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }

onMounted(loadArticle)
onUnmounted(() => {
  clearInterval(_timer)
  window.removeEventListener('scroll', _tocScrollHandler)
})
</script>

<template>
  <div class="article-shell">
    <nav class="article-back"><router-link to="/">&larr; 返回首页</router-link></nav>

    <div v-if="loading" class="article-panel">
      <div class="skeleton" style="width:60px;height:12px;margin-bottom:20px" />
      <div class="skeleton" style="width:70%;height:32px;margin-bottom:14px" />
      <div class="skeleton" style="width:45%;height:18px;margin-bottom:32px" />
      <div class="skeleton" style="width:100%;aspect-ratio:2/1;margin-bottom:32px;border-radius:16px" />
      <div v-for="i in 8" :key="i" class="skeleton" style="width:100%;height:13px;margin-bottom:10px" />
    </div>

    <div v-else-if="error" class="article-panel empty">
      <p>{{ error }}</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:16px">
        <router-link to="/">&larr; 返回首页</router-link>
      </div>
    </div>

    <div v-else class="article-with-toc">
      <!-- TOC sidebar -->
      <aside class="toc-sidebar" v-if="toc.length > 1">
        <div class="toc-title">目录</div>
        <nav class="toc-nav">
          <a
            v-for="h in toc"
            :key="h.slug"
            :href="`#${h.slug}`"
            :class="['toc-link', `toc-lv${h.level}`, { active: activeSlug === h.slug }]"
          >{{ h.text }}</a>
        </nav>
      </aside>

      <article class="article-panel">
        <header class="article-header">
          <div class="article-meta">
            <span class="article-badge">{{ labels[article.type] || '博客' }}</span>
            <time>{{ article.createdAt?.slice(0, 10) }}</time>
          </div>
          <h1>{{ article.title }}</h1>
          <p v-if="article.summary" class="article-subtitle">{{ article.summary }}</p>
          <div v-if="article.tags?.length" class="article-tags">
            <span v-for="t in article.tags" :key="t" class="article-tag">{{ t }}</span>
          </div>
        </header>
        <div v-if="article.coverImage" class="article-cover">
          <img :src="article.coverImage" :alt="article.title" loading="lazy" decoding="async" />
        </div>
        <div class="article-body" v-html="html" />
        <footer class="article-footer">
          <p>发布于 {{ article.createdAt?.slice(0, 10) }}</p>
          <router-link to="/" class="article-home-link">&larr; 返回首页</router-link>
        </footer>
      </article>
    </div>
  </div>

  <!-- 悬浮返回按钮 -->
  <div class="float-actions" v-if="!loading">
    <router-link to="/" class="float-btn" title="返回首页">🏠</router-link>
    <button class="float-btn" @click="scrollToTop" title="回到顶部">⬆</button>
  </div>
</template>
