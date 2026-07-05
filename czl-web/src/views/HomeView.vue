<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import EntryCard from '../components/EntryCard.vue'

const activeType = ref('all')
const searchText = ref('')
const keyword = ref('')
const entries = ref([])
const stats = ref(null)
const loading = ref(true)
const loadError = ref(false)
const scrolled = ref(false)

let debounceTimer = null
watch(searchText, (val) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { keyword.value = val.trim().toLowerCase() }, 200)
})

function onScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => { loadData(); window.addEventListener('scroll', onScroll, { passive: true }) })
onUnmounted(() => { window.removeEventListener('scroll', onScroll) })

const filtered = computed(() => {
  return entries.value.filter(e => {
    const typeOk = activeType.value === 'all' || e.type === activeType.value
    const kwOk = !keyword.value || [e.title, e.summary, ...(e.tags || [])].join(' ').toLowerCase().includes(keyword.value)
    return typeOk && kwOk
  })
})

const photoEntries = computed(() => entries.value.filter(e => e.type === 'photo').slice(0, 4))
</script>

<template>
  <div class="shell">

    <!-- Nav -->
    <nav class="topnav" :class="{ scrolled }">
      <div class="topnav-brand">{{ stats?.site?.title || '大橘' }}</div>
      <div class="topnav-links">
        <a href="#" :class="{ active: activeType === 'all' }" @click.prevent="activeType = 'all'">全部</a>
        <a href="#" :class="{ active: activeType === 'blog' }" @click.prevent="activeType = 'blog'">博客</a>
        <a href="#" :class="{ active: activeType === 'life' }" @click.prevent="activeType = 'life'">生活</a>
        <a href="#" :class="{ active: activeType === 'photo' }" @click.prevent="activeType = 'photo'">摄影</a>
      </div>
      <div class="topnav-actions">
        <router-link to="/admin" class="btn-ghost-sm">管理</router-link>
      </div>
    </nav>

    <div class="home-layout">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-card">
          <div class="sidebar-avatar">
            <div class="avatar-circle">{{ (stats?.site?.title || '大')[0] }}</div>
          </div>
          <h2 class="sidebar-name">{{ stats?.site?.title || '大橘' }}</h2>
          <p class="sidebar-subtitle">{{ stats?.site?.subtitleName || '文字と生活' }}</p>
          <div class="sidebar-divider" />
          <p class="sidebar-intro" v-if="stats?.intro?.summary">{{ stats.intro.summary }}</p>
          <p class="sidebar-intro" v-else>个人博客与记录空间。</p>
          <div style="text-align:center;margin-top:8px">
            <span class="sidebar-loc">📍 中国</span>
          </div>
        </div>

        <div class="sidebar-card stats-card">
          <div class="stat-row">
            <div class="stat-icon">📝</div>
            <div class="stat-info">
              <strong>{{ stats?.articleCount || 0 }}</strong>
              <span>文章</span>
            </div>
          </div>
          <div class="stat-row">
            <div class="stat-icon">👁️</div>
            <div class="stat-info">
              <strong>{{ stats?.totalPV || 0 }}</strong>
              <span>浏览</span>
            </div>
          </div>
          <div class="stat-row">
            <div class="stat-icon">👤</div>
            <div class="stat-info">
              <strong>{{ stats?.totalUV || 0 }}</strong>
              <span>访客</span>
            </div>
          </div>
          <div class="stat-row">
            <div class="stat-icon">📅</div>
            <div class="stat-info">
              <strong>{{ stats?.runningDays || 0 }}</strong>
              <span>运行天数</span>
            </div>
          </div>
          <div class="stat-row">
            <div class="stat-icon">🔥</div>
            <div class="stat-info">
              <strong>{{ stats?.todayPV || 0 }}</strong>
              <span>今日访问</span>
            </div>
          </div>
        </div>

        <div class="sidebar-card" v-if="stats?.site?.pixelText">
          <p class="sidebar-motto">"{{ stats.site.pixelText }}"</p>
        </div>
      </aside>

      <!-- Main -->
      <main class="main-area">
        <!-- Hero -->
        <header class="hero">
          <div class="hero-deco">🌿</div>
          <h1>{{ stats?.intro?.headline || '文字与生活的记录空间' }}</h1>
          <p v-if="stats?.intro?.summary">{{ stats.intro.summary }}</p>
        </header>

        <!-- Search -->
        <div class="search-bar">
          <input v-model="searchText" type="search" placeholder="搜索文章..." />
        </div>

        <!-- Loading skeletons -->
        <div v-if="loading" class="entry-grid">
          <div v-for="i in 4" :key="'sk'+i" class="skeleton-card">
            <div class="skeleton skeleton-cover" />
            <div class="skeleton-body">
              <div class="skeleton skeleton-line short" />
              <div class="skeleton skeleton-line title" />
              <div class="skeleton skeleton-line" />
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="loadError" class="empty">
          <p>加载失败，请稍后再试。</p>
          <button class="btn-ghost-sm" @click="loadData">重试</button>
        </div>

        <div v-else-if="filtered.length === 0" class="empty">
          <p v-if="keyword">没有找到与 "{{ keyword }}" 相关的文章。</p>
          <p v-else>还没有文章，去后台发布第一篇吧。</p>
        </div>

        <!-- Entry grid -->
        <div v-else class="entry-grid">
          <EntryCard v-for="e in filtered" :key="e.id" :entry="e" />
        </div>

        <!-- Photo section -->
        <section v-if="photoEntries.length" class="photo-section">
          <div class="sec-head">
            <span class="kicker">Photography</span>
            <h2>摄影精选</h2>
          </div>
          <div class="photo-grid">
            <article v-for="p in photoEntries" :key="p.id" class="photo-card">
              <div class="photo-cover" :style="{ backgroundImage: `url(${p.coverImage || p.images?.[0]})` }" />
              <div class="photo-body">
                <h3>{{ p.title }}</h3>
                <p>{{ p.summary }}</p>
              </div>
            </article>
          </div>
        </section>

        <!-- Footer -->
        <footer class="page-footer">
          <p>&copy; {{ stats?.site?.title || '大橘' }}</p>
        </footer>
      </main>
    </div>
  </div>
</template>
