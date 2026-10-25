<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'
import { renderMarkdown } from '../markdown.js'
import { useMeta, setArticleMeta } from '../composables/useMeta.js'
import { fetchAllArticles } from '../api/articles.js'

const route = useRoute()
const router = useRouter()
const article = ref(null)
const loading = ref(true)
const error = ref('')
const labels = { blog: '博客', life: '生活', photo: '摄影' }
const html = computed(() => article.value ? renderMarkdown(article.value.content) : '')

// Scroll progress
const scrollProgress = ref(0)
function onScrollProgress() {
  const el = document.documentElement
  const scrolled = el.scrollTop || document.body.scrollTop
  const total = el.scrollHeight - el.clientHeight
  scrollProgress.value = total > 0 ? Math.min(100, (scrolled / total) * 100) : 0
  // also update TOC active slug
  const headings = document.querySelectorAll('.article-body h2, .article-body h3')
  let current = ''
  headings.forEach(h => {
    if (h.getBoundingClientRect().top <= 120) current = h.id
  })
  activeSlug.value = current
}

// Copy link toast
const copyToast = ref(false)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = window.location.href
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copyToast.value = true
  setTimeout(() => { copyToast.value = false }, 2000)
}

/* ---- TOC ---- */
const toc = computed(() => {
  if (!article.value) return []
  const raw = article.value.content
  const re = /^(#{2,3})\s+(.+)$/gm
  const items = []
  let m
  while ((m = re.exec(raw)) !== null) {
    const level = m[1].length
    const text = m[2]
    const slug = text
      .toLowerCase()
      .replace(/[^\w一-鿿\s-]/g, '')
      .replace(/\s+/g, '-')
    items.push({ level, text, slug })
  }
  return items
})

/* ---- Prev/Next navigation ---- */
const prevArticle = ref(null)
const nextArticle = ref(null)
async function loadAdjacentArticles() {
  try {
    const list = await fetchAllArticles()
    const idx = list.findIndex(a => a.id === route.params.id)
    if (idx > 0) nextArticle.value = list[idx - 1]
    if (idx < list.length - 1) prevArticle.value = list[idx + 1]
  } catch {}
}

/* ---- load ---- */
async function loadArticle() {
  loading.value = true
  error.value = ''
  prevArticle.value = null
  nextArticle.value = null
  try {
    const res = await fetch(`/api/public/articles/${route.params.id}`)
    const d = await res.json()
    if (!d.success) error.value = d.message || '文章不存在'
    else {
      article.value = d.data
      const a = d.data
      // Strip markdown syntax for a plain-text description
      const rawDesc = a.summary || a.content?.replace(/[#*`>\-_[\]()!]/g, '').slice(0, 120) || ''
      useMeta({
        title: `${a.title} — 大橘`,
        description: rawDesc,
        image: a.coverImage || '',
        url: window.location.href,
        type: 'article',
      })
      setArticleMeta({
        publishedTime: a.createdAt || '',
        tags: a.tags || [],
      })
      loadAdjacentArticles()
    }
  } catch { error.value = '加载失败' }
  finally { loading.value = false }
}

/* ---- KaTeX ---- */
function renderMath() {
  nextTick(() => {
    const el = document.querySelector('.article-body')
    if (!el) return
    try {
      renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
      })
    } catch {}
  })
}
watch(html, () => {
  renderMath()
})

/* ---- TOC active slug ---- */
const activeSlug = ref('')

watch(html, () => {
  nextTick(() => {
    window.removeEventListener('scroll', onScrollProgress)
    window.addEventListener('scroll', onScrollProgress, { passive: true })
  })
})

function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }

function scrollToHeading(slug) {
  const el = document.getElementById(slug)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  loadArticle()
  window.addEventListener('scroll', onScrollProgress, { passive: true })
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScrollProgress)
})
</script>

<template>
  <!-- Scroll progress bar -->
  <div class="scroll-progress-bar" :style="{ width: scrollProgress + '%' }" />

  <!-- Copy toast -->
  <Transition name="toast-fade">
    <div v-if="copyToast" class="copy-toast">已复制链接!</div>
  </Transition>

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
            @click.prevent="scrollToHeading(h.slug)"
          >{{ h.text }}</a>
        </nav>
      </aside>

      <article class="article-panel">
        <!-- Cover image banner -->
        <div v-if="article.coverImage" class="article-cover-banner">
          <img :src="article.coverImage" :alt="article.title" loading="lazy" decoding="async" />
        </div>

        <header class="article-header">
          <div class="article-meta">
            <span class="article-badge" :class="`badge-${article.type || 'blog'}`">{{ labels[article.type] || '博客' }}</span>
            <time>{{ article.createdAt?.slice(0, 10) }}</time>
            <button class="copy-link-btn" @click="copyLink" title="复制链接">🔗 复制链接</button>
          </div>
          <h1>{{ article.title }}</h1>
          <p v-if="article.summary" class="article-subtitle">{{ article.summary }}</p>
          <div v-if="article.tags?.length" class="article-tags">
            <router-link v-for="t in article.tags" :key="t" :to="'/tag/' + t" class="article-tag">{{ t }}</router-link>
          </div>
        </header>

        <div class="article-body" v-html="html" />

        <!-- Prev / Next navigation -->
        <nav class="article-nav" v-if="prevArticle || nextArticle">
          <router-link v-if="prevArticle" :to="`/article/${prevArticle.id}`" class="article-nav-prev">
            <span class="nav-label">← 上一篇</span>
            <span class="nav-title">{{ prevArticle.title }}</span>
          </router-link>
          <div v-else class="article-nav-placeholder" />
          <router-link v-if="nextArticle" :to="`/article/${nextArticle.id}`" class="article-nav-next">
            <span class="nav-label">下一篇 →</span>
            <span class="nav-title">{{ nextArticle.title }}</span>
          </router-link>
          <div v-else class="article-nav-placeholder" />
        </nav>

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

<style scoped>
.scroll-progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  background: var(--c1);
  z-index: 9999;
  transition: width 0.1s linear;
  border-radius: 0 2px 2px 0;
}

.copy-toast {
  position: fixed;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(30,30,30,0.85);
  color: #fff;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 0.85rem;
  z-index: 9999;
  pointer-events: none;
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.3s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; }

.article-cover-banner {
  width: 100%;
  max-height: 360px;
  overflow: hidden;
  border-radius: 14px;
  margin-bottom: 24px;
}
.article-cover-banner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.copy-link-btn {
  margin-left: auto;
  background: none;
  border: 1px solid #ddd;
  border-radius: 20px;
  padding: 3px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  color: #888;
  transition: all 0.18s;
}
.copy-link-btn:hover {
  background: var(--c1);
  color: #fff;
  border-color: var(--c1);
}

.badge-blog { background: var(--c1) !important; }
.badge-life { background: var(--c4) !important; }
.badge-photo { background: var(--c6) !important; }

.article-nav {
  display: flex;
  gap: 12px;
  margin: 36px 0 20px;
  border-top: 1px solid #eee;
  padding-top: 24px;
}
.article-nav-prev,
.article-nav-next {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 10px;
  background: rgba(255,255,255,0.6);
  border: 1px solid #eee;
  text-decoration: none;
  color: inherit;
  transition: all 0.18s;
}
.article-nav-next { text-align: right; align-items: flex-end; }
.article-nav-prev:hover, .article-nav-next:hover {
  background: rgba(255,255,255,0.95);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: var(--c1);
}
.nav-label {
  font-size: 0.75rem;
  color: var(--c1);
  font-weight: 600;
}
.nav-title {
  font-size: 0.88rem;
  color: #444;
  font-weight: 500;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.article-nav-placeholder { flex: 1; }
</style>
