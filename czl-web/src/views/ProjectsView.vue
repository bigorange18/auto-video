<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMeta } from '../composables/useMeta.js'
import {
  normalizeProjects,
  PROJECT_CATEGORIES,
} from '../../shared/projectSchema.js'

const router = useRouter()
const projects = ref([])
const session = ref(null)
const loading = ref(true)
const error = ref(false)
const filters = reactive({
  category: 'all',
  status: 'all',
  keyword: '',
})
const statusLabels = {
  active: '进行中',
  maintained: '持续维护',
  planned: '计划中',
  archived: '已归档',
}
const categoryLabels = {
  web: 'Web',
  ai: 'AI',
  content: '内容',
  ops: '运维',
  learning: '学习',
  other: '其他',
}

const categoryOptions = computed(() => {
  const counts = Object.fromEntries(PROJECT_CATEGORIES.map((category) => [category, 0]))
  projects.value.forEach((project) => {
    counts[project.category] = (counts[project.category] || 0) + 1
  })
  return [
    { value: 'all', label: '全部', count: projects.value.length },
    ...PROJECT_CATEGORIES
      .filter((category) => counts[category] > 0)
      .map((category) => ({
        value: category,
        label: categoryLabels[category],
        count: counts[category],
      })),
  ]
})

const statusOptions = computed(() => {
  const counts = {}
  projects.value.forEach((project) => {
    counts[project.status] = (counts[project.status] || 0) + 1
  })
  return [
    { value: 'all', label: '全部状态', count: projects.value.length },
    ...Object.entries(statusLabels)
      .filter(([status]) => counts[status] > 0)
      .map(([status, label]) => ({ value: status, label, count: counts[status] })),
  ]
})

const filteredProjects = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return projects.value.filter((project) => {
    if (filters.category !== 'all' && project.category !== filters.category) return false
    if (filters.status !== 'all' && project.status !== filters.status) return false
    if (!keyword) return true
    return [
      project.name,
      project.summary,
      project.description,
      ...project.stack,
    ].join(' ').toLowerCase().includes(keyword)
  })
})

// Cycle through color vars for accent gradients
const accents = [
  ['var(--c4)', 'var(--c7)'],
  ['var(--c8)', 'var(--c6)'],
  ['var(--c3)', 'var(--c7)'],
  ['var(--c5)', 'var(--c4)'],
  ['var(--c2)', 'var(--c8)'],
  ['var(--c1)', 'var(--c6)'],
  ['var(--c7)', 'var(--c3)'],
  ['var(--c6)', 'var(--c5)'],
]

function accent(i) {
  const [a, b] = accents[i % accents.length]
  return `linear-gradient(135deg, ${a}, ${b})`
}

onMounted(async () => {
  useMeta({
    title: '项目 — 大橘',
    description: '我正在推进的开源项目和个人作品',
    url: window.location.href,
  })
  try {
    const [contentRes, sessionRes] = await Promise.all([
      fetch('/api/public/content'),
      fetch('/api/admin/session'),
    ])
    const [d, sessionData] = await Promise.all([
      contentRes.json(),
      sessionRes.json(),
    ])
    if (d.success && Array.isArray(d.data?.projects)) {
      projects.value = normalizeProjects(d.data.projects)
    }
    if (sessionData.success) {
      session.value = sessionData.data
    }
  } catch {
    error.value = true
  }
  loading.value = false
})

function isExternal(link) {
  return link && link.startsWith('http')
}

function resetFilters() {
  filters.category = 'all'
  filters.status = 'all'
  filters.keyword = ''
}

function editProject(project) {
  router.push({
    path: '/admin',
    query: {
      tab: 'content',
      project: project.slug,
    },
  })
}
</script>

<template>
  <div class="projects-page">
    <!-- Header -->
    <header class="projects-header">
      <span class="kicker-tag">Projects</span>
      <h1>我的项目</h1>
      <p class="projects-subtitle">正在推进或已完成的工作，持续更新。</p>
    </header>

    <section v-if="!loading && !error && projects.length" class="project-toolbar" aria-label="项目筛选">
      <div class="category-filters" role="group" aria-label="按分类筛选">
        <button
          v-for="option in categoryOptions"
          :key="option.value"
          type="button"
          class="category-filter"
          :class="{ active: filters.category === option.value }"
          :aria-pressed="filters.category === option.value"
          @click="filters.category = option.value"
        >
          {{ option.label }} <span>{{ option.count }}</span>
        </button>
      </div>
      <div class="filter-controls">
        <input
          v-model="filters.keyword"
          class="project-search"
          type="search"
          placeholder="搜索项目或技术栈"
          aria-label="搜索项目"
        />
        <select v-model="filters.status" class="status-filter" aria-label="按状态筛选">
          <option
            v-for="option in statusOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }} · {{ option.count }}
          </option>
        </select>
      </div>
    </section>

    <!-- Loading skeletons -->
    <div v-if="loading" class="projects-grid">
      <div v-for="i in 3" :key="i" class="proj-skeleton">
        <div class="skeleton" style="width:60%;height:22px;margin-bottom:10px" />
        <div class="skeleton" style="width:90%;height:14px;margin-bottom:6px" />
        <div class="skeleton" style="width:75%;height:14px;margin-bottom:18px" />
        <div style="display:flex;gap:6px">
          <div v-for="j in 3" :key="j" class="skeleton" style="width:52px;height:22px;border-radius:999px" />
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="empty-state">
      <p class="empty-icon">⚠️</p>
      <p class="empty-title">加载失败</p>
      <p class="empty-desc">无法获取项目数据，请稍后再试。</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!projects.length" class="empty-state">
      <p class="empty-icon">🚧</p>
      <p class="empty-title">项目准备中</p>
      <p class="empty-desc">这里还没有项目，稍后会陆续补充。</p>
    </div>

    <div v-else-if="!filteredProjects.length" class="empty-state">
      <p class="empty-title">没有符合条件的项目</p>
      <p class="empty-desc">换一个分类或状态，或者清除搜索关键词。</p>
      <button type="button" class="reset-filters" @click="resetFilters">清除筛选</button>
    </div>

    <!-- Project cards -->
    <div v-else class="projects-grid">
      <article
        v-for="(proj, i) in filteredProjects"
        :key="proj.slug || i"
        class="proj-card"
      >
        <div class="proj-accent" :style="{ background: accent(i) }" />
        <div class="proj-body">
          <div class="proj-heading">
            <h2 class="proj-title">{{ proj.name }}</h2>
            <div class="proj-badges">
              <span class="proj-category">{{ categoryLabels[proj.category] }}</span>
              <span class="proj-status" :class="`status-${proj.status}`">
                {{ statusLabels[proj.status] || proj.status }}
              </span>
            </div>
          </div>
          <p class="proj-desc" v-if="proj.summary">{{ proj.summary }}</p>

          <!-- Tech stack tags -->
          <div class="proj-tags" v-if="proj.stack.length">
            <span v-for="t in proj.stack" :key="t" class="proj-tag">{{ t }}</span>
          </div>

          <!-- Links -->
          <div class="proj-links" v-if="proj.demoUrl || proj.repoUrl || session">
            <button
              v-if="session"
              type="button"
              class="proj-link proj-edit-btn"
              @click="editProject(proj)"
            >编辑项目</button>
            <a
              v-if="proj.repoUrl"
              :href="proj.repoUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="proj-link proj-link-gh"
            >⎇ GitHub</a>
            <a
              v-if="proj.demoUrl && isExternal(proj.demoUrl)"
              :href="proj.demoUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="proj-link proj-link-demo"
            >↗ 查看项目</a>
            <a
              v-else-if="proj.demoUrl"
              :href="proj.demoUrl"
              class="proj-link proj-link-demo"
            >↗ 了解更多</a>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.projects-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 20px 80px;
}

/* Header */
.projects-header {
  padding: 52px 0 40px;
  display: grid;
  gap: 6px;
}
.kicker-tag {
  display: inline-block;
  font-size: .72rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--c8);
}
.projects-header h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--dark);
}
.projects-subtitle {
  font-size: .95rem;
  color: var(--soft);
}

.project-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 24px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}

.category-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.category-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--soft);
  font-size: .76rem;
  cursor: pointer;
  transition: border-color .18s, color .18s, background .18s;
}

.category-filter span {
  color: var(--text-muted, #aaa);
  font-size: .68rem;
}

.category-filter:hover,
.category-filter.active {
  border-color: var(--dark);
  color: var(--dark);
  background: rgba(127, 127, 127, .06);
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.project-search,
.status-filter {
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--panel);
  color: var(--dark);
  font-size: .78rem;
}

.project-search {
  width: 180px;
  padding: 0 11px;
}

.status-filter {
  padding: 0 9px;
}

.project-search:focus,
.status-filter:focus {
  outline: none;
  border-color: var(--c4);
}

/* Grid */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

/* Card */
.proj-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  overflow: hidden;
  backdrop-filter: blur(16px);
  box-shadow: 0 10px 30px rgba(0,0,0,.04);
  transition: .25s;
  display: flex;
  flex-direction: column;
}
.proj-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 48px rgba(0,0,0,.09);
}
.proj-accent {
  height: 5px;
  width: 100%;
  flex-shrink: 0;
}
.proj-body {
  padding: 22px 22px 20px;
  display: grid;
  gap: 10px;
  align-content: start;
  flex: 1;
}
.proj-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--dark);
  line-height: 1.3;
}
.proj-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.proj-badges {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}
.proj-category {
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--soft);
  font-size: .68rem;
}
.proj-status {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: .7rem;
  font-weight: 600;
  color: var(--soft);
  background: rgba(0, 0, 0, .04);
}
.status-active {
  color: var(--c3);
  background: rgba(16, 185, 129, .1);
}
.status-planned {
  color: var(--c8);
  background: rgba(245, 158, 11, .1);
}
.proj-desc {
  font-size: .88rem;
  color: var(--soft);
  line-height: 1.65;
}
.proj-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.proj-tag {
  font-size: .74rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(59,130,246,.07);
  color: var(--c4);
  border: 1px solid rgba(59,130,246,.15);
}
.proj-links {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.proj-link {
  font-size: .8rem;
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  transition: .2s;
  font-weight: 500;
}
.proj-link:hover { transform: translateY(-1px); }
.proj-link-gh {
  background: rgba(0,0,0,.03);
  color: var(--dark);
}
.proj-link-gh:hover { background: rgba(0,0,0,.08); }
.proj-link-demo {
  background: linear-gradient(135deg, var(--c8), var(--c6));
  color: #fff !important;
  border-color: transparent;
}
.proj-link-demo:hover { opacity: .88; }
.proj-edit-btn {
  border-color: var(--line);
  background: transparent;
  color: var(--dark);
  cursor: pointer;
}
.proj-edit-btn:hover {
  border-color: var(--c1);
  color: var(--c1);
}

/* Skeleton card */
.proj-skeleton {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  backdrop-filter: blur(14px);
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  display: grid;
  gap: 10px;
  justify-items: center;
}
.empty-icon  { font-size: 3rem; }
.empty-title { font-size: 1.1rem; font-weight: 700; color: var(--dark); }
.empty-desc  { font-size: .9rem; color: var(--soft); }
.reset-filters {
  margin-top: 4px;
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--dark);
  cursor: pointer;
}

@media (max-width: 600px) {
  .project-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .filter-controls {
    width: 100%;
  }
  .project-search {
    flex: 1;
    width: auto;
  }
  .projects-grid { grid-template-columns: 1fr; }
}
</style>
