<script setup>
import { onMounted, reactive, ref } from 'vue'
import EntryCard from '../components/EntryCard.vue'

const content = reactive({
  site: {},
  intro: {},
  skills: [],
  projects: [],
  contact: {},
})

const messageForm = reactive({ name: '', email: '', body: '' })
const loading = ref(true)
const sending = ref(false)
const notice = ref('')

/* ---- blog ---- */
const articles = ref([])
const articlesLoading = ref(true)

async function loadContent() {
  loading.value = true
  const response = await fetch('/api/public/content')
  const result = await response.json()
  if (result.success) {
    Object.assign(content, result.data)
  }
  loading.value = false
}

async function loadArticles() {
  articlesLoading.value = true
  try {
    const res = await fetch('/api/public/articles')
    const data = await res.json()
    if (data.success) {
      articles.value = data.data.map((a) => ({
        ...a,
        date: a.createdAt ? a.createdAt.slice(0, 10) : '',
      }))
    }
  } catch { /* silent */ }
  articlesLoading.value = false
}

async function submitMessage() {
  sending.value = true
  notice.value = ''
  const response = await fetch('/api/public/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(messageForm),
  })
  const result = await response.json()
  sending.value = false
  notice.value = result.message || (result.success ? '已提交' : '提交失败')
  if (result.success) {
    messageForm.name = ''
    messageForm.email = ''
    messageForm.body = ''
  }
}

onMounted(() => {
  loadContent()
  loadArticles()
})
</script>

<template>
  <div class="site-shell" v-if="!loading">
    <!-- ===== Hero ===== -->
    <header class="hero-panel">
      <div class="hero-copy">
        <p class="kicker">{{ content.site.titlePrefix }}</p>
        <h1>{{ content.site.title }}</h1>
        <p class="subtitle">
          {{ content.site.subtitlePrefix }}
          <strong>{{ content.site.subtitleName }}</strong>
        </p>
        <p class="summary">{{ content.intro.headline }}</p>
        <p class="description">{{ content.intro.summary }}</p>
        <div class="hero-actions">
          <a href="#blog">博客</a>
          <a href="#projects">查看项目</a>
          <a href="#contact" class="ghost">联系我</a>
        </div>
      </div>
      <div class="hero-card">
        <span class="pixel-label">{{ content.site.pixelText }}</span>
        <div class="hero-stat">
          <strong>Vue + Node</strong>
          <span>新站采用单一工程，前后端职责清晰。</span>
        </div>
        <div class="hero-stat">
          <strong>工作前台</strong>
          <span>展示真实内容、沉淀方法，并保留交流入口。</span>
        </div>
      </div>
    </header>

    <main class="content-stack">
      <!-- ===== Blog ===== -->
      <section class="panel" id="blog">
        <div class="section-head">
          <p class="kicker">Blog</p>
          <h2>最新文章</h2>
        </div>
        <div v-if="articlesLoading" class="helper-text">加载中…</div>
        <div v-else-if="articles.length === 0" class="helper-text">还没有文章。</div>
        <div v-else class="blog-grid">
          <EntryCard v-for="a in articles" :key="a.id" :entry="a" />
        </div>
      </section>

      <!-- ===== Skills ===== -->
      <section class="panel section-grid" id="skills">
        <div class="section-head">
          <p class="kicker">Skills</p>
          <h2>当前能力面</h2>
        </div>
        <div class="chip-list">
          <span v-for="skill in content.skills" :key="skill" class="chip">{{ skill }}</span>
        </div>
      </section>

      <!-- ===== Projects ===== -->
      <section class="panel" id="projects">
        <div class="section-head">
          <p class="kicker">Projects</p>
          <h2>正在推进的项目</h2>
        </div>
        <div class="project-grid">
          <article v-for="project in content.projects" :key="project.title" class="project-card">
            <h3>{{ project.title }}</h3>
            <p>{{ project.desc }}</p>
            <a :href="project.link || '#contact'" target="_blank" rel="noreferrer">打开</a>
          </article>
        </div>
      </section>

      <!-- ===== Contact ===== -->
      <section class="panel contact-panel" id="contact">
        <div class="contact-copy">
          <div class="section-head">
            <p class="kicker">Contact</p>
            <h2>联系方式</h2>
          </div>
          <ul class="contact-list">
            <li>
              <span>邮箱</span>
              <strong>{{ content.contact.email }}</strong>
            </li>
            <li>
              <span>微信</span>
              <strong>{{ content.contact.wechat }}</strong>
            </li>
            <li>
              <span>GitHub</span>
              <strong>{{ content.contact.github }}</strong>
            </li>
          </ul>
        </div>

        <form class="message-form" @submit.prevent="submitMessage">
          <label>
            <span>你的名字</span>
            <input v-model="messageForm.name" type="text" required />
          </label>
          <label>
            <span>邮箱</span>
            <input v-model="messageForm.email" type="email" required />
          </label>
          <label>
            <span>留言内容</span>
            <textarea v-model="messageForm.body" rows="5" required></textarea>
          </label>
          <button type="submit" :disabled="sending">
            {{ sending ? '提交中...' : '发送留言' }}
          </button>
          <p class="form-notice" v-if="notice">{{ notice }}</p>
        </form>
      </section>
    </main>
  </div>
</template>
