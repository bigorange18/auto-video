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
const tasks = ref([])
const taskSummary = ref({
  total: 0,
  status: { todo: 0, in_progress: 0, done: 0 },
  priority: { high: 0, medium: 0, low: 0 },
  overdue: 0,
})
const taskFilters = reactive({ keyword: '', status: 'all' })
const taskForm = reactive({
  title: '',
  project: '',
  priority: 'medium',
  status: 'todo',
  dueDate: '',
  tags: '',
  notes: '',
})
const taskSaving = ref(false)
const taskNotice = ref('')
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

const filteredTasks = computed(() => {
  const keyword = taskFilters.keyword.trim().toLowerCase()
  return tasks.value.filter((task) => {
    const inStatus = taskFilters.status === 'all' ? true : task.status === taskFilters.status
    const inKeyword = keyword
      ? [task.title, task.project, ...(task.tags || [])].join(' ').toLowerCase().includes(keyword)
      : true
    return inStatus && inKeyword
  })
})

async function fetchSession() {
  const response = await fetch('/api/admin/session')
  const result = await response.json()
  session.value = result.data
}

async function loadDashboard() {
  const [contentRes, messagesRes, statsRes, tasksRes, taskSummaryRes] = await Promise.all([
    fetch('/api/admin/content'),
    fetch('/api/admin/messages'),
    fetch('/api/admin/stats'),
    fetch('/api/admin/tasks'),
    fetch('/api/admin/tasks/summary'),
  ])
  const [contentJson, messagesJson, statsJson, tasksJson, taskSummaryJson] = await Promise.all([
    contentRes.json(),
    messagesRes.json(),
    statsRes.json(),
    tasksRes.json(),
    taskSummaryRes.json(),
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
  if (tasksJson.success) {
    tasks.value = tasksJson.data
  }
  if (taskSummaryJson.success) {
    taskSummary.value = taskSummaryJson.data
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

function toStatusLabel(status) {
  const map = {
    todo: '待处理',
    in_progress: '进行中',
    done: '已完成',
  }
  return map[status] || '待处理'
}

function toPriorityLabel(priority) {
  const map = {
    high: '高',
    medium: '中',
    low: '低',
  }
  return map[priority] || '中'
}

async function createTask() {
  if (!taskForm.title.trim()) {
    taskNotice.value = '任务标题不能为空'
    return
  }
  taskSaving.value = true
  taskNotice.value = ''
  const response = await fetch('/api/admin/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: taskForm.title,
      project: taskForm.project,
      priority: taskForm.priority,
      status: taskForm.status,
      dueDate: taskForm.dueDate,
      tags: taskForm.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      notes: taskForm.notes,
    }),
  })
  const result = await response.json()
  taskSaving.value = false
  taskNotice.value = result.message || (result.success ? '任务已创建' : '创建失败')
  if (result.success) {
    taskForm.title = ''
    taskForm.project = ''
    taskForm.priority = 'medium'
    taskForm.status = 'todo'
    taskForm.dueDate = ''
    taskForm.tags = ''
    taskForm.notes = ''
    await loadDashboard()
  }
}

async function cycleTaskStatus(task) {
  const order = ['todo', 'in_progress', 'done']
  const currentIndex = order.indexOf(task.status)
  const nextStatus = order[(currentIndex + 1) % order.length]
  await fetch(`/api/admin/tasks/${task.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: nextStatus }),
  })
  await loadDashboard()
}

async function removeTask(id) {
  await fetch(`/api/admin/tasks/${id}`, { method: 'DELETE' })
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
        <article>
          <span>任务总数</span>
          <strong>{{ taskSummary.total }}</strong>
        </article>
        <article>
          <span>进行中任务</span>
          <strong>{{ taskSummary.status.in_progress }}</strong>
        </article>
        <article>
          <span>逾期任务</span>
          <strong>{{ taskSummary.overdue }}</strong>
        </article>
      </section>

      <section class="panel tasks-panel">
        <div class="section-head">
          <p class="kicker">Tasko</p>
          <h2>任务管理</h2>
        </div>

        <div class="task-toolbar">
          <label>
            <span>搜索</span>
            <input v-model="taskFilters.keyword" type="text" placeholder="按任务、项目或标签搜索" />
          </label>
          <label>
            <span>状态</span>
            <select v-model="taskFilters.status">
              <option value="all">全部</option>
              <option value="todo">待处理</option>
              <option value="in_progress">进行中</option>
              <option value="done">已完成</option>
            </select>
          </label>
        </div>

        <form class="task-form" @submit.prevent="createTask">
          <label>
            <span>任务标题</span>
            <input v-model="taskForm.title" type="text" required />
          </label>
          <label>
            <span>项目</span>
            <input v-model="taskForm.project" type="text" />
          </label>
          <label>
            <span>优先级</span>
            <select v-model="taskForm.priority">
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>
          <label>
            <span>状态</span>
            <select v-model="taskForm.status">
              <option value="todo">待处理</option>
              <option value="in_progress">进行中</option>
              <option value="done">已完成</option>
            </select>
          </label>
          <label>
            <span>截止日期</span>
            <input v-model="taskForm.dueDate" type="date" />
          </label>
          <label>
            <span>标签（逗号分隔）</span>
            <input v-model="taskForm.tags" type="text" placeholder="frontend, api" />
          </label>
          <label class="full">
            <span>备注</span>
            <textarea v-model="taskForm.notes" rows="3"></textarea>
          </label>
          <div class="task-form-actions full">
            <button type="submit" :disabled="taskSaving">{{ taskSaving ? '创建中...' : '新建任务' }}</button>
            <span class="helper-text">{{ taskNotice }}</span>
          </div>
        </form>

        <div class="task-list">
          <article v-for="item in filteredTasks" :key="item.id" class="task-item">
            <div class="task-item-head">
              <div>
                <strong>{{ item.title }}</strong>
                <span>{{ item.project || '未分配项目' }}</span>
              </div>
              <small>{{ item.dueDate || '无截止日期' }}</small>
            </div>
            <p v-if="item.notes">{{ item.notes }}</p>
            <div class="task-meta">
              <span class="task-badge">状态：{{ toStatusLabel(item.status) }}</span>
              <span class="task-badge">优先级：{{ toPriorityLabel(item.priority) }}</span>
              <span v-for="tag in item.tags" :key="`${item.id}-${tag}`" class="task-tag">#{{ tag }}</span>
            </div>
            <div class="task-actions">
              <button type="button" class="ghost-button" @click="cycleTaskStatus(item)">切换状态</button>
              <button type="button" class="ghost-button danger" @click="removeTask(item.id)">删除</button>
            </div>
          </article>
          <p v-if="!filteredTasks.length" class="helper-text">当前筛选下没有任务。</p>
        </div>
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
