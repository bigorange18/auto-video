<script setup>
import { onMounted, reactive, ref, computed, watch } from 'vue'
import EntryCard from '../components/EntryCard.vue'

const activeType = ref('all')
const searchText = ref('')
const keyword = ref('')
let timer = null

function setType(t) { activeType.value = t }
watch(searchText, (v) => {
  clearTimeout(timer)
  timer = setTimeout(() => { keyword.value = v.trim().toLowerCase() }, 200)
})

/* ---- data ---- */
const content = reactive({ site: {}, intro: {}, skills: [], projects: [], contact: {} })
const articles = ref([])
const loading = ref(true)
const stats = ref({ articleCount: 0, totalPV: 0, totalUV: 0, runningDays: 0, todayPV: 0 })

const filtered = computed(() => {
  return articles.value.filter(a => {
    if (activeType.value !== 'all' && a.type !== activeType.value) return false
    if (keyword.value && ![a.title, a.summary, ...(a.tags || [])].join(' ').toLowerCase().includes(keyword.value)) return false
    return true
  })
})

onMounted(async () => {
  loading.value = true
  try {
    const [contentRes, articlesRes, statsRes] = await Promise.all([
      fetch('/api/public/content'),
      fetch('/api/public/articles'),
      fetch('/api/public/stats'),
    ])
    const [c, a, s] = await Promise.all([contentRes.json(), articlesRes.json(), statsRes.json()])
    if (c.success) Object.assign(content, c.data)
    if (a.success) articles.value = a.data.map(x => ({ ...x, date: x.createdAt?.slice(0, 10) || '' }))
    if (s.success) stats.value = s.data
  } catch { /* */ }
  loading.value = false
})
</script>

<template>
  <div class="home-layout" v-if="!loading">
    <!-- sidebar -->
    <aside class="sidebar">
      <div class="sidebar-card">
        <div class="avatar-circle">🍊</div>
        <div class="sidebar-name">{{ content.site.title || '大橘' }}</div>
        <div class="sidebar-subtitle">{{ content.site.subtitleName || '文字と生活' }}</div>
        <div class="sidebar-divider" />
        <p class="sidebar-intro" v-if="content.intro.summary">{{ content.intro.summary }}</p>
        <p class="sidebar-intro" v-else>个人博客与记录空间。分享技术笔记、项目心得与生活随想。</p>
      </div>

      <div class="sidebar-card stats-card">
        <div class="stat-row"><span class="stat-icon">📝</span><strong>{{ stats.articleCount }}</strong><span>文章</span></div>
        <div class="stat-row"><span class="stat-icon">👁️</span><strong>{{ stats.totalPV }}</strong><span>浏览</span></div>
        <div class="stat-row"><span class="stat-icon">👤</span><strong>{{ stats.totalUV }}</strong><span>访客</span></div>
        <div class="stat-row"><span class="stat-icon">📅</span><strong>{{ stats.runningDays }}</strong><span>天运行</span></div>
        <div class="stat-row"><span class="stat-icon">🔥</span><strong>{{ stats.todayPV }}</strong><span>今日</span></div>
      </div>

      <div class="sidebar-card">
        <div class="section-head"><p class="kicker">Skills</p><h3>能力面</h3></div>
        <div class="chip-list">
          <span v-for="s in content.skills" :key="s" class="chip">{{ s }}</span>
        </div>
      </div>
    </aside>

    <!-- main -->
    <main class="main-area">
      <!-- type filter + search -->
      <div class="filter-bar">
        <div class="type-filters">
          <button :class="{ active: activeType === 'all' }" @click="setType('all')">全部</button>
          <button :class="{ active: activeType === 'blog' }" @click="setType('blog')">博客</button>
          <button :class="{ active: activeType === 'life' }" @click="setType('life')">生活</button>
          <button :class="{ active: activeType === 'photo' }" @click="setType('photo')">摄影</button>
        </div>
        <input v-model="searchText" type="search" placeholder="搜索文章..." class="search-input" />
      </div>

      <!-- blog list -->
      <div v-if="filtered.length" class="blog-list">
        <EntryCard v-for="a in filtered" :key="a.id" :entry="a" />
      </div>
      <div v-else class="empty-state">
        <p v-if="keyword">没找到与"{{ keyword }}"相关的文章</p>
        <p v-else>还没有文章。</p>
      </div>
    </main>
  </div>

  <!-- loading -->
  <div class="home-layout" v-else>
    <aside class="sidebar">
      <div class="sidebar-card">
        <div class="skeleton" style="width:64px;height:64px;border-radius:50%;margin:0 auto 12px" />
        <div class="skeleton" style="width:80px;height:18px;margin:0 auto 6px" />
        <div class="skeleton" style="width:120px;height:13px;margin:0 auto" />
      </div>
    </aside>
    <main class="main-area">
      <div class="blog-list">
        <div v-for="i in 3" :key="i" class="skeleton-card">
          <div class="skeleton" style="width:200px;height:130px;border-radius:12px;flex-shrink:0" />
          <div style="display:grid;gap:8px;padding:16px 0">
            <div class="skeleton" style="width:60px;height:12px" />
            <div class="skeleton" style="width:70%;height:20px" />
            <div class="skeleton" style="width:100%;height:13px" />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
