<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AdminShell from '../components/admin/AdminShell.vue'
import AdminArticles from '../components/admin/AdminArticles.vue'
import AdminTasks from '../components/admin/AdminTasks.vue'
import AdminMessages from '../components/admin/AdminMessages.vue'
import AdminTraffic from '../components/admin/AdminTraffic.vue'
import AdminContent from '../components/admin/AdminContent.vue'

const session = ref(null)
const loading = ref(true)
const route = useRoute()
const loginForm = reactive({ username: 'admin', password: '' })
const loginError = ref('')
const requestedTab = String(route.query.tab || '')
const activeTab = ref(
  ['overview', 'articles', 'tasks', 'messages', 'traffic', 'content'].includes(requestedTab)
    ? requestedTab
    : 'overview',
)

const stats = ref({ recent: [], messageCount: 0, unreadCount: 0 })
const taskSummary = ref({
  total: 0,
  status: { todo: 0, in_progress: 0, done: 0 },
  priority: { high: 0, medium: 0, low: 0 },
  overdue: 0,
})
const articles = ref([])

async function fetchSession() {
  const res = await fetch('/api/admin/session')
  const json = await res.json()
  session.value = json.data
}

async function fetchSharedData() {
  const [statsRes, taskSummaryRes, articlesRes] = await Promise.all([
    fetch('/api/admin/stats'),
    fetch('/api/admin/tasks/summary'),
    fetch('/api/admin/articles'),
  ])
  const [statsJson, taskSummaryJson, articlesJson] = await Promise.all([
    statsRes.json(),
    taskSummaryRes.json(),
    articlesRes.json(),
  ])
  if (statsJson.success) stats.value = statsJson.data
  if (taskSummaryJson.success) taskSummary.value = taskSummaryJson.data
  if (articlesJson.success) articles.value = articlesJson.data
}

async function bootstrap() {
  loading.value = true
  await fetchSession()
  if (session.value) {
    await fetchSharedData()
  }
  loading.value = false
}

async function login() {
  loginError.value = ''
  const res = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginForm),
  })
  const json = await res.json()
  if (!json.success) {
    loginError.value = json.message || '登录失败'
    return
  }
  session.value = json.data
  await fetchSharedData()
}

async function logout() {
  await fetch('/api/admin/logout', { method: 'POST' })
  session.value = null
}

onMounted(bootstrap)
</script>

<template>
  <div v-if="loading" class="admin-loading">加载中...</div>

  <template v-else-if="!session">
    <div class="login-page">
      <div class="login-card">
        <div class="login-logo">🍊</div>
        <h1 class="login-title">管理后台</h1>
        <p class="login-subtitle">大橘 · Dashboard</p>
        <form @submit.prevent="login" class="login-form">
          <div class="login-field">
            <span class="login-field-icon">👤</span>
            <input
              v-model="loginForm.username"
              type="text"
              placeholder="账号"
              required
              autocomplete="username"
            />
          </div>
          <div class="login-field">
            <span class="login-field-icon">🔒</span>
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              required
              autocomplete="current-password"
            />
          </div>
          <Transition name="err-fade">
            <p v-if="loginError" class="login-error">{{ loginError }}</p>
          </Transition>
          <button type="submit" class="login-btn">登录</button>
        </form>
        <p class="login-footer">仅限授权用户访问</p>
      </div>
    </div>
  </template>

  <template v-else>
    <AdminShell
      :session="session"
      :stats="stats"
      :task-summary="taskSummary"
      :articles="articles"
      :active-tab="activeTab"
      @logout="logout"
      @update:activeTab="activeTab = $event"
    >
      <template #tab-content>
        <AdminArticles v-if="activeTab === 'articles'" />
        <AdminTasks v-else-if="activeTab === 'tasks'" />
        <AdminMessages v-else-if="activeTab === 'messages'" />
        <AdminTraffic v-else-if="activeTab === 'traffic'" :stats="stats" />
        <AdminContent v-else-if="activeTab === 'content'" />
      </template>
    </AdminShell>
  </template>
</template>

<style scoped>
.admin-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  font-size: 1rem;
  color: var(--soft);
}

/* ── Login page ── */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 24px;
  padding: 40px 36px 32px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.10);
  text-align: center;
}

:global(html.dark) .login-card {
  background: rgba(22, 24, 34, 0.90);
  border-color: rgba(255, 255, 255, 0.08);
}

.login-logo {
  font-size: 3rem;
  margin-bottom: 12px;
  line-height: 1;
}

.login-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 4px;
  color: var(--text, #1a1a1a);
}

.login-subtitle {
  font-size: 0.82rem;
  color: var(--text-muted, #999);
  margin: 0 0 28px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.login-field {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  padding: 0 14px;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.login-field:focus-within {
  border-color: var(--c1, #f97316);
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
  background: rgba(255, 255, 255, 0.8);
}

:global(html.dark) .login-field {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

:global(html.dark) .login-field:focus-within {
  background: rgba(255, 255, 255, 0.1);
}

.login-field-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.login-field input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  padding: 13px 0;
  font-size: 0.92rem;
  color: var(--text, #1a1a1a);
}

:global(html.dark) .login-field input {
  color: #e8eaf0;
}

.login-field input::placeholder {
  color: var(--text-muted, #aaa);
}

.login-error {
  font-size: 0.82rem;
  color: #ef4444;
  margin: 0;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.08);
  border-radius: 8px;
  text-align: left;
}

.err-fade-enter-active, .err-fade-leave-active { transition: opacity 0.2s; }
.err-fade-enter-from, .err-fade-leave-to { opacity: 0; }

.login-btn {
  margin-top: 4px;
  padding: 13px;
  border: none;
  border-radius: 12px;
  background: var(--c1, #f97316);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.18s, transform 0.15s;
  letter-spacing: 0.03em;
}

.login-btn:hover { opacity: 0.88; transform: translateY(-1px); }
.login-btn:active { transform: translateY(0); }

.login-footer {
  margin: 20px 0 0;
  font-size: 0.75rem;
  color: var(--text-muted, #bbb);
}
</style>
