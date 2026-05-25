<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

const session = ref(null)
const loginForm = reactive({ username: 'admin', password: '' })
const loginError = ref('')
const saving = ref(false)
const statusText = ref('')
const loading = ref(true)
const messages = ref([])
const stats = ref({ recent: [], messageCount: 0, unreadCount: 0 })
const contentForm = reactive({
  site: { titlePrefix: '', title: '', subtitlePrefix: '', subtitleName: '', pixelText: '' },
  intro: { headline: '', summary: '' },
  skills: [],
  projects: [],
  contact: { email: '', wechat: '', github: '' },
})

const skillsInput = computed({
  get: () => contentForm.skills.join('\n'),
  set: (value) => {
    contentForm.skills = value.split('\n').map((item) => item.trim()).filter(Boolean)
  },
})

const projectsInput = computed({
  get: () => JSON.stringify(contentForm.projects, null, 2),
  set: (value) => {
    try {
      const parsed = JSON.parse(value)
      contentForm.projects = Array.isArray(parsed) ? parsed : []
    } catch {
      // keep previous value until save
    }
  },
})

async function fetchSession() {
  const response = await fetch('/api/admin/session')
  const result = await response.json()
  session.value = result.data
}

async function loadDashboard() {
  const [contentRes, messagesRes, statsRes] = await Promise.all([
    fetch('/api/admin/content'),
    fetch('/api/admin/messages'),
    fetch('/api/admin/stats'),
  ])
  const [contentJson, messagesJson, statsJson] = await Promise.all([
    contentRes.json(),
    messagesRes.json(),
    statsRes.json(),
  ])
  if (contentJson.success) {
    Object.assign(contentForm, contentJson.data)
  }
  if (messagesJson.success) {
    messages.value = messagesJson.data
  }
  if (statsJson.success) {
    stats.value = statsJson.data
  }
}

async function bootstrap() {
  loading.value = true
  await fetchSession()
  if (session.value) {
    await loadDashboard()
  }
  loading.value = false
}

async function login() {
  loginError.value = ''
  const response = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginForm),
  })
  const result = await response.json()
  if (!result.success) {
    loginError.value = result.message || '登录失败'
    return
  }
  session.value = result.data
  await loadDashboard()
}

async function logout() {
  await fetch('/api/admin/logout', { method: 'POST' })
  session.value = null
}

async function saveContent() {
  saving.value = true
  statusText.value = ''
  const response = await fetch('/api/admin/content', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(contentForm),
  })
  const result = await response.json()
  saving.value = false
  statusText.value = result.message || (result.success ? '已保存' : '保存失败')
}

async function toggleRead(message) {
  await fetch(`/api/admin/messages/${message.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ read: !message.read }),
  })
  await loadDashboard()
}

async function removeMessage(id) {
  await fetch(`/api/admin/messages/${id}`, { method: 'DELETE' })
  await loadDashboard()
}

onMounted(bootstrap)
</script>

<template>
  <div class="admin-shell" v-if="!loading">
    <section class="admin-login panel" v-if="!session">
      <div class="section-head">
        <p class="kicker">Admin</p>
        <h1>管理后台</h1>
      </div>
      <form class="message-form" @submit.prevent="login">
        <label>
          <span>账号</span>
          <input v-model="loginForm.username" type="text" required />
        </label>
        <label>
          <span>密码</span>
          <input v-model="loginForm.password" type="password" required />
        </label>
        <button type="submit">登录</button>
        <p class="form-notice error" v-if="loginError">{{ loginError }}</p>
      </form>
    </section>

    <div v-else class="admin-dashboard">
      <header class="admin-topbar panel">
        <div>
          <p class="kicker">Dashboard</p>
          <h1>内容管理</h1>
        </div>
        <div class="topbar-actions">
          <router-link to="/">查看前台</router-link>
          <button class="ghost-button" type="button" @click="logout">退出</button>
        </div>
      </header>

      <section class="panel stats-row">
        <article>
          <span>留言总数</span>
          <strong>{{ stats.messageCount }}</strong>
        </article>
        <article>
          <span>未读留言</span>
          <strong>{{ stats.unreadCount }}</strong>
        </article>
        <article>
          <span>最近统计天数</span>
          <strong>{{ stats.recent.length }}</strong>
        </article>
      </section>

      <section class="panel admin-grid">
        <div class="editor-panel">
          <div class="section-head">
            <p class="kicker">Content</p>
            <h2>站点内容</h2>
          </div>
          <div class="editor-form">
            <label><span>标题前缀</span><input v-model="contentForm.site.titlePrefix" type="text" /></label>
            <label><span>标题</span><input v-model="contentForm.site.title" type="text" /></label>
            <label><span>副标题前缀</span><input v-model="contentForm.site.subtitlePrefix" type="text" /></label>
            <label><span>副标题名称</span><input v-model="contentForm.site.subtitleName" type="text" /></label>
            <label><span>像素文字</span><input v-model="contentForm.site.pixelText" type="text" /></label>
            <label><span>首页主标题</span><input v-model="contentForm.intro.headline" type="text" /></label>
            <label class="full"><span>简介</span><textarea v-model="contentForm.intro.summary" rows="5"></textarea></label>
            <label class="full"><span>技能列表，每行一项</span><textarea v-model="skillsInput" rows="7"></textarea></label>
            <label class="full"><span>项目 JSON</span><textarea v-model="projectsInput" rows="10"></textarea></label>
            <label><span>邮箱</span><input v-model="contentForm.contact.email" type="text" /></label>
            <label><span>微信</span><input v-model="contentForm.contact.wechat" type="text" /></label>
            <label><span>GitHub</span><input v-model="contentForm.contact.github" type="text" /></label>
          </div>
          <div class="editor-actions">
            <button type="button" @click="saveContent" :disabled="saving">{{ saving ? '保存中...' : '保存站点内容' }}</button>
            <span class="helper-text">{{ statusText }}</span>
          </div>
        </div>

        <div class="message-panel">
          <div class="section-head">
            <p class="kicker">Inbox</p>
            <h2>留言管理</h2>
          </div>
          <div class="message-admin-list">
            <article v-for="item in messages" :key="item.id" class="message-admin-item">
              <div class="message-admin-head">
                <div>
                  <strong>{{ item.name }}</strong>
                  <span>{{ item.email }}</span>
                </div>
                <small>{{ item.createdAt.slice(0, 16).replace('T', ' ') }}</small>
              </div>
              <p>{{ item.body }}</p>
              <div class="message-admin-actions">
                <button type="button" class="ghost-button" @click="toggleRead(item)">
                  {{ item.read ? '标记未读' : '标记已读' }}
                </button>
                <button type="button" class="ghost-button danger" @click="removeMessage(item.id)">删除</button>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <p class="kicker">Traffic</p>
          <h2>最近访问</h2>
        </div>
        <div class="traffic-list">
          <div v-for="item in stats.recent" :key="item.date" class="traffic-item">
            <strong>{{ item.date }}</strong>
            <span>PV {{ item.pv }}</span>
            <span>UV {{ item.uv }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
