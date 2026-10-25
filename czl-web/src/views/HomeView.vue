<script setup>
import { onMounted, reactive, ref, computed, watch } from 'vue'
import EntryCard from '../components/EntryCard.vue'
import { useMeta } from '../composables/useMeta.js'
import { fetchAllArticles } from '../api/articles.js'

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

const typeCounts = computed(() => ({
  all:   articles.value.length,
  blog:  articles.value.filter(a => a.type === 'blog').length,
  life:  articles.value.filter(a => a.type === 'life').length,
  photo: articles.value.filter(a => a.type === 'photo').length,
}))

onMounted(async () => {
  loading.value = true
  try {
    const [contentRes, statsRes, allArticles] = await Promise.all([
      fetch('/api/public/content'),
      fetch('/api/public/stats'),
      fetchAllArticles(),
    ])
    const [c, s] = await Promise.all([contentRes.json(), statsRes.json()])
    if (c.success) Object.assign(content, c.data)
    articles.value = allArticles.map(x => ({
      ...x,
      date: x.createdAt?.slice(0, 10) || '',
    }))
    if (s.success) stats.value = s.data
    useMeta({
      title: `${content.site?.title || '大橘'} — ${content.intro?.headline || '把个人主页改造成持续更新的工作前台。'}`,
      description: content.intro?.summary || '把个人主页改造成持续更新的工作前台。',
      url: window.location.href,
    })
  } catch { /* */ }
  loading.value = false
})
</script>

<template>
  <!-- ===== Main (loaded) ===== -->
  <div id="main-content" class="home-layout" v-if="!loading">
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
        <div class="stat-grid">
          <div class="stat-cell">
            <span class="stat-icon">📝</span>
            <strong>{{ stats.articleCount }}</strong>
            <span>文章</span>
          </div>
          <div class="stat-cell">
            <span class="stat-icon">👁️</span>
            <strong>{{ stats.totalPV }}</strong>
            <span>浏览</span>
          </div>
          <div class="stat-cell">
            <span class="stat-icon">👤</span>
            <strong>{{ stats.totalUV }}</strong>
            <span>访客</span>
          </div>
          <div class="stat-cell">
            <span class="stat-icon">📅</span>
            <strong>{{ stats.runningDays }}</strong>
            <span>天运行</span>
          </div>
          <div class="stat-cell">
            <span class="stat-icon">🔥</span>
            <strong>{{ stats.todayPV }}</strong>
            <span>今日</span>
          </div>
        </div>
      </div>

      <div class="sidebar-card skills-card" v-if="content.skills && content.skills.length">
        <p class="skills-label">技能 & 工具</p>
        <div class="skills-chips-sidebar">
          <span
            v-for="(s, i) in content.skills"
            :key="s"
            class="skill-chip-sm"
            :style="{ '--chip-color': `var(--c${(i % 8) + 1})` }"
          >{{ s }}</span>
        </div>
      </div>

    </aside>

    <!-- main -->
    <main class="main-area">
      <!-- filter bar -->
      <div class="filter-bar">
        <div class="type-filters">
          <button :class="{ active: activeType === 'all' }" @click="setType('all')">
            全部<span class="filter-badge">{{ typeCounts.all }}</span>
          </button>
          <button :class="{ active: activeType === 'blog' }" @click="setType('blog')">
            博客<span class="filter-badge">{{ typeCounts.blog }}</span>
          </button>
          <button :class="{ active: activeType === 'life' }" @click="setType('life')">
            生活<span class="filter-badge">{{ typeCounts.life }}</span>
          </button>
          <button :class="{ active: activeType === 'photo' }" @click="setType('photo')">
            摄影<span class="filter-badge">{{ typeCounts.photo }}</span>
          </button>
        </div>
        <input v-model="searchText" type="search" placeholder="搜索文章..." class="search-input" />
      </div>

      <!-- article list with transition -->
      <Transition name="list-fade" mode="out-in">
        <div v-if="filtered.length" :key="activeType + '|' + keyword" class="blog-list">
          <EntryCard v-for="a in filtered" :key="a.id" :entry="a" />
        </div>
        <div v-else :key="'empty|' + activeType + '|' + keyword" class="empty-state">
          <template v-if="keyword">
            <span class="empty-emoji">🔍</span>
            <p>没找到与"{{ keyword }}"相关的文章</p>
          </template>
          <template v-else>
            <span class="empty-emoji">📭</span>
            <p>还没有文章，敬请期待。</p>
          </template>
        </div>
      </Transition>

    </main>
  </div>

  <!-- ===== Loading skeleton ===== -->
  <div v-else>
    <div class="home-layout">
      <aside class="sidebar">
        <div class="sidebar-card">
          <div class="skeleton" style="width:64px;height:64px;border-radius:50%;margin:0 auto 12px" />
          <div class="skeleton" style="width:80px;height:18px;margin:0 auto 6px" />
          <div class="skeleton" style="width:120px;height:13px;margin:0 auto" />
        </div>
      <div class="sidebar-card skills-card">
        <p class="skills-label">技能 & 工具</p>
        <div class="skills-chips-sidebar">
          <span
            v-for="(s, i) in content.skills"
            :key="s"
            class="skill-chip-sm"
            :style="{ '--chip-color': `var(--c${(i % 8) + 1})` }"
          >{{ s }}</span>
        </div>
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
  </div>
</template>

<style scoped>
/* article grid transition */
.list-fade-enter-active,
.list-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.list-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.list-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* skills sidebar */
.skills-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted, #aaa);
  margin: 0 0 10px;
}
.skills-chips-sidebar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.skill-chip-sm {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: color-mix(in srgb, var(--chip-color) 12%, transparent);
  color: var(--chip-color);
  border: 1px solid color-mix(in srgb, var(--chip-color) 25%, transparent);
  transition: background 0.15s;
}
.skill-chip-sm:hover {
  background: color-mix(in srgb, var(--chip-color) 22%, transparent);
}

/* stats grid */
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 12px 8px;
  background: rgba(255,255,255,0.5);
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.05);
  text-align: center;
  transition: background 0.15s;
}

.stat-cell:hover {
  background: rgba(255,255,255,0.85);
}

:global(html.dark) .stat-cell {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.08);
}

.stat-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.stat-cell strong {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--c1);
}

.stat-cell span {
  font-size: 0.7rem;
  color: var(--text-muted, #999);
  letter-spacing: 0.02em;
}
</style>
