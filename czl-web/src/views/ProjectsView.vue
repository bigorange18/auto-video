<script setup>
import { ref, onMounted } from 'vue'
import { useMeta } from '../composables/useMeta.js'

const projects = ref([])
const loading = ref(true)
const error = ref(false)

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
    const res = await fetch('/api/public/content')
    const d = await res.json()
    if (d.success && Array.isArray(d.data?.projects)) {
      projects.value = d.data.projects
    }
  } catch {
    error.value = true
  }
  loading.value = false
})

function isExternal(link) {
  return link && link.startsWith('http')
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
    <div v-else-if="projects.length === 0" class="empty-state">
      <p class="empty-icon">🚧</p>
      <p class="empty-title">项目准备中</p>
      <p class="empty-desc">这里还没有项目，稍后会陆续补充。</p>
    </div>

    <!-- Project cards -->
    <div v-else class="projects-grid">
      <article
        v-for="(proj, i) in projects"
        :key="i"
        class="proj-card"
      >
        <div class="proj-accent" :style="{ background: accent(i) }" />
        <div class="proj-body">
          <h2 class="proj-title">{{ proj.title }}</h2>
          <p class="proj-desc" v-if="proj.desc">{{ proj.desc }}</p>

          <!-- Tech stack tags -->
          <div class="proj-tags" v-if="proj.tech && proj.tech.length">
            <span v-for="t in proj.tech" :key="t" class="proj-tag">{{ t }}</span>
          </div>

          <!-- Links -->
          <div class="proj-links" v-if="proj.link || proj.github">
            <a
              v-if="proj.github"
              :href="proj.github"
              target="_blank"
              rel="noopener noreferrer"
              class="proj-link proj-link-gh"
            >⎇ GitHub</a>
            <a
              v-if="proj.link && isExternal(proj.link)"
              :href="proj.link"
              target="_blank"
              rel="noopener noreferrer"
              class="proj-link proj-link-demo"
            >↗ 查看项目</a>
            <a
              v-else-if="proj.link"
              :href="proj.link"
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

@media (max-width: 600px) {
  .projects-grid { grid-template-columns: 1fr; }
}
</style>
