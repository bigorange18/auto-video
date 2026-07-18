<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

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

// 文章管理
const allArticles = ref([])
const editingArticle = ref(null) // null=新建, 有id=编辑
const articleForm = reactive({
  title: '',
  summary: '',
  content: '',
  type: 'blog',
  tags: '',
  coverImage: '',
  published: true,
})
const articleSaving = ref(false)
const articleNotice = ref('')
const articlePreview = ref('')
const activeTab = ref('content') // 'content' | 'articles' | 'tasks' | 'messages' | 'stats'

// 文章预览（防抖）
import { renderMarkdown } from '../markdown.js'
let previewTimer = null
function updatePreview() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    articlePreview.value = renderMarkdown(articleForm.content)
  }, 300)
}
// 用 watch 监听 content 变化
watch(() => articleForm.content, updatePreview)
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
  await loadArticles()
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

// 加载所有文章（含未发布）
async function loadArticles() {
  const res = await fetch('/api/admin/articles')
  const d = await res.json()
  if (d.success) allArticles.value = d.data
}

// 开始编辑文章
function editArticle(article) {
  editingArticle.value = article
  articleForm.title = article.title
  articleForm.summary = article.summary || ''
  articleForm.content = article.content || ''
  articleForm.type = article.type || 'blog'
  articleForm.tags = (article.tags || []).join(', ')
  articleForm.coverImage = article.coverImage || ''
  articleForm.published = article.published !== false
  articlePreview.value = renderMarkdown(article.content || '')
  articleNotice.value = ''
  activeTab.value = 'articles'
}

// 新建文章
function newArticle() {
  editingArticle.value = null
  articleForm.title = ''
  articleForm.summary = ''
  articleForm.content = ''
  articleForm.type = 'blog'
  articleForm.tags = ''
  articleForm.coverImage = ''
  articleForm.published = true
  articlePreview.value = ''
  articleNotice.value = ''
  activeTab.value = 'articles'
}

// 取消编辑
function cancelEdit() {
  editingArticle.value = null
  newArticle()
}

// 保存文章（创建或更新）
async function saveArticle(publish = true) {
  if (!articleForm.title.trim() || !articleForm.content.trim()) {
    articleNotice.value = '标题和内容不能为空'
    return
  }
  articleSaving.value = true
  articleNotice.value = ''

  const payload = {
    title: articleForm.title.trim(),
    summary: articleForm.summary.trim(),
    content: articleForm.content,
    type: articleForm.type,
    tags: articleForm.tags.split(',').map(t => t.trim()).filter(Boolean),
    coverImage: articleForm.coverImage.trim(),
    published: publish,
  }

  const url = editingArticle.value?.id
    ? `/api/admin/articles/${editingArticle.value.id}`
    : '/api/admin/articles'
  const method = editingArticle.value?.id ? 'PUT' : 'POST'

  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const d = await res.json()
  articleSaving.value = false

  if (d.success) {
    articleNotice.value = editingArticle.value?.id ? '文章已更新' : '文章已创建'
    if (d.data) {
      editingArticle.value = d.data
      articleForm.content = d.data.content
    }
    await loadArticles()
  } else {
    articleNotice.value = d.message || '保存失败'
  }
}

// 删除文章
async function removeArticle(id) {
  if (!confirm('确定要删除这篇文章吗？此操作不可恢复。')) return
  await fetch(`/api/admin/articles/${id}`, { method: 'DELETE' })
  if (editingArticle.value?.id === id) cancelEdit()
  await loadArticles()
}

// 切换发布状态
async function togglePublish(article) {
  await fetch(`/api/admin/articles/${article.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ published: article.published === false }),
  })
  await loadArticles()
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

      <div class="admin-tabs" style="display:flex;gap:4px;margin-top:16px">
        <button class="ghost-button" :class="{ active: activeTab === 'content' }" @click="activeTab='content'">站点内容</button>
        <button class="ghost-button" :class="{ active: activeTab === 'articles' }" @click="activeTab='articles'">文章管理</button>
        <button class="ghost-button" :class="{ active: activeTab === 'tasks' }" @click="activeTab='tasks'">任务管理</button>
        <button class="ghost-button" :class="{ active: activeTab === 'messages' }" @click="activeTab='messages'">留言管理</button>
        <button class="ghost-button" :class="{ active: activeTab === 'stats' }" @click="activeTab='stats'">访问统计</button>
      </div>

      <section class="panel stats-row" v-if="activeTab === 'stats' || activeTab === 'content'">
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

      <section class="panel tasks-panel" v-if="activeTab === 'tasks'">
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

      <section class="panel admin-grid" v-if="activeTab === 'content' || activeTab === 'messages'">
        <div class="editor-panel" v-if="activeTab === 'content'">
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

        <div class="message-panel" v-if="activeTab === 'messages'">
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

      <section class="panel" v-if="activeTab === 'stats'">
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

      <!-- 文章管理 -->
      <section class="panel article-editor" v-if="activeTab === 'articles'">
        <div class="section-head">
          <p class="kicker">Editor</p>
          <h2>{{ editingArticle ? '编辑文章' : '新建文章' }}</h2>
        </div>

        <div class="article-editor-layout">
          <form class="article-editor-form" @submit.prevent="saveArticle(true)">
            <label><span>标题 *</span><input v-model="articleForm.title" type="text" required /></label>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
              <label><span>类型</span>
                <select v-model="articleForm.type">
                  <option value="blog">博客</option>
                  <option value="life">生活</option>
                  <option value="photo">摄影</option>
                </select>
              </label>
              <label><span>标签（逗号分隔）</span><input v-model="articleForm.tags" type="text" /></label>
            </div>
            <label><span>摘要</span><input v-model="articleForm.summary" type="text" /></label>
            <label><span>封面图片 URL</span><input v-model="articleForm.coverImage" type="text" /></label>
            <label><span>内容（Markdown）*</span>
              <textarea id="article-content-editor" v-model="articleForm.content" required></textarea>
            </label>
            <div class="article-editor-actions">
              <button type="submit" :disabled="articleSaving">{{ articleSaving ? '保存中...' : '发布文章' }}</button>
              <button type="button" class="outline" @click="saveArticle(false)" :disabled="articleSaving">存为草稿</button>
              <button type="button" class="outline" @click="cancelEdit" v-if="editingArticle">取消编辑</button>
              <button type="button" class="danger-outline" @click="removeArticle(editingArticle.id)" v-if="editingArticle">删除文章</button>
              <span class="helper-text">{{ articleNotice }}</span>
            </div>
          </form>

          <!-- 预览区 -->
          <div class="article-editor-preview">
            <p v-if="!articlePreview" style="color:var(--soft);text-align:center;margin-top:120px">预览区域</p>
            <div v-else v-html="articlePreview"></div>
          </div>
        </div>

        <!-- 文章列表 -->
        <div class="section-head" style="margin-top:32px">
          <p class="kicker">Articles</p>
          <h3>所有文章 ({{ allArticles.length }})</h3>
        </div>
        <div class="admin-article-list">
          <div v-for="a in allArticles" :key="a.id" class="admin-article-item">
            <div class="admin-article-item-left">
              <strong>{{ a.title }}</strong>
              <div class="meta-row">
                <span :class="['publish-badge', a.published !== false ? 'published' : 'draft']">{{ a.published !== false ? '已发布' : '草稿' }}</span>
                <span>{{ a.type === 'blog' ? '博客' : a.type === 'life' ? '生活' : '摄影' }}</span>
                <span>{{ (a.createdAt || '').slice(0, 10) }}</span>
              </div>
            </div>
            <div class="admin-article-item-actions">
              <button class="ghost-button" @click="editArticle(a)">编辑</button>
              <button class="ghost-button" @click="togglePublish(a)">{{ a.published !== false ? '下架' : '发布' }}</button>
              <button class="ghost-button danger" @click="removeArticle(a.id)">删除</button>
            </div>
          </div>
          <p v-if="!allArticles.length" class="helper-text">还没有文章，点击上方新建。</p>
        </div>
      </section>
    </div>
  </div>
</template>
