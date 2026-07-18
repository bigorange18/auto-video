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
      <div class="sidebar-card profile-card">
        <div class="avatar-circle" style="margin:0 0 12px">🍊</div>
        <div class="sidebar-name">{{ content.site.title || '大橘' }}</div>
        <div class="sidebar-subtitle">{{ content.site.subtitleName || '文字と生活' }}</div>
        <div class="sidebar-divider" />
        <p class="sidebar-intro" v-if="content.intro.summary">{{ content.intro.summary }}</p>
        <p class="sidebar-intro" v-else>个人博客与记录空间。分享技术笔记、项目心得与生活随想。</p>
        <div class="profile-socials" v-if="content.contact">
          <a v-if="content.contact.github" :href="'https://github.com/' + content.contact.github" target="_blank" class="social-link" title="GitHub">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.605-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/></svg>
          </a>
          <a v-if="content.contact.email" :href="'mailto:' + content.contact.email" class="social-link" title="Email">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13 2 4"/></svg>
          </a>
        </div>
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

      <div class="sidebar-card" v-if="content.projects?.length">
        <div class="section-head"><p class="kicker">Projects</p><h3>项目</h3></div>
        <div class="projects-grid-sidebar" style="display:grid;gap:10px;margin-top:10px">
          <div v-for="p in content.projects" :key="p.title" style="padding:10px 0;border-bottom:1px solid var(--line)">
            <div style="font-size:.88rem;font-weight:600;color:var(--dark)">{{ p.title }}</div>
            <div style="font-size:.78rem;color:var(--soft);margin-top:2px" v-if="p.desc">{{ p.desc }}</div>
            <a v-if="p.link" :href="p.link" target="_blank" style="font-size:.74rem;color:var(--c4)">{{ p.link }}</a>
          </div>
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

      <div v-if="filtered.length" class="guestbook-teaser" style="margin-top:20px;text-align:center;padding:24px;border:1px dashed var(--line);border-radius:16px;background:var(--panel)">
        <p style="font-size:.92rem;color:var(--soft);margin-bottom:8px">💬 有什么想说的？</p>
        <router-link to="/guestbook" style="color:var(--c4);font-weight:600">去留言板看看 →</router-link>
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
