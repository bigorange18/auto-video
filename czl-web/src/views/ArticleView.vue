<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { renderMarkdown } from '../markdown.js'

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const error = ref('')

const tLabel = { blog: '博客', life: '生活', photo: '摄影' }

const html = computed(() => article.value ? renderMarkdown(article.value.content) : '')

async function loadArticle() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/public/articles/${route.params.id}`)
    const data = await res.json()
    if (!data.success) error.value = data.message || '文章不存在或已被删除'
    else {
      article.value = data.data
      document.title = `${data.data.title} — 大橘`
    }
  } catch {
    error.value = '加载失败，请稍后再试。'
  } finally { loading.value = false }
}

onMounted(loadArticle)
</script>

<template>
  <div class="article-shell">
    <nav class="article-nav">
      <router-link to="/" class="btn-ghost-sm">&larr; 返回首页</router-link>
    </nav>

    <!-- Loading skeleton -->
    <div v-if="loading" class="panel article-detail">
      <div class="skeleton" style="width:60px;height:12px;margin-bottom:24px" />
      <div class="skeleton" style="width:70%;height:36px;margin-bottom:16px" />
      <div class="skeleton" style="width:45%;height:22px;margin-bottom:36px" />
      <div class="skeleton" style="width:100%;aspect-ratio:2/1;margin-bottom:36px" />
      <div v-for="i in 8" :key="'sl'+i" class="skeleton" style="width:100%;height:14px;margin-bottom:12px" />
      <div class="skeleton" style="width:55%;height:14px" />
    </div>

    <div v-else-if="error" class="panel empty">
      <p>{{ error }}</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:16px">
        <button class="btn-ghost-sm" @click="loadArticle">重试</button>
        <router-link to="/" class="btn-ghost-sm">返回首页</router-link>
      </div>
    </div>

    <article v-else class="panel article-detail">
      <header class="article-header">
        <div class="article-meta">
          <span class="article-type-badge">{{ tLabel[article.type] || '博客' }}</span>
          <time>{{ article.createdAt.slice(0, 10) }}</time>
        </div>
        <h1>{{ article.title }}</h1>
        <p v-if="article.summary" class="article-summary">{{ article.summary }}</p>
        <div v-if="article.tags.length" class="article-tags">
          <span v-for="t in article.tags" :key="t" class="tag">{{ t }}</span>
        </div>
      </header>

      <div v-if="article.coverImage" class="article-cover">
        <img :src="article.coverImage" :alt="article.title" loading="lazy" decoding="async" />
      </div>

      <div class="article-body" v-html="html" />

      <footer class="article-footer">
        <p>发布于 {{ article.createdAt.slice(0, 10) }}</p>
      </footer>
    </article>
  </div>
</template>
