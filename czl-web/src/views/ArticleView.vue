<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { renderMarkdown } from '../markdown.js'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const error = ref('')
const labels = { blog: '博客', life: '生活', photo: '摄影' }
const html = computed(() => article.value ? renderMarkdown(article.value.content) : '')

onMounted(async () => {
  try {
    const res = await fetch(`/api/public/articles/${route.params.id}`)
    const d = await res.json()
    if (!d.success) error.value = d.message || '文章不存在'
    else { article.value = d.data; document.title = `${d.data.title} — 大橘` }
  } catch { error.value = '加载失败' }
  finally { loading.value = false }
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

    <article v-else class="article-panel">
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
      </footer>
    </article>
  </div>
</template>
