<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

// ── Data ─────────────────────────────────────────────────────────────────────
const tasks = ref([])
const loading = ref(true)
const filters = reactive({ keyword: '', status: 'all' })

// ── Modal state ───────────────────────────────────────────────────────────────
const modal = reactive({ open: false, editId: null })
const saving = ref(false)
const form = reactive({
  title: '',
  project: '',
  priority: 'medium',
  status: 'todo',
  dueDate: '',
  tags: '',
  notes: '',
})

// ── Inline delete confirm ─────────────────────────────────────────────────────
const pendingDelete = ref(null)

// ── Fetch ─────────────────────────────────────────────────────────────────────
async function fetchTasks() {
  loading.value = true
  try {
    const res = await fetch('/api/admin/tasks')
    const json = await res.json()
    if (json.success) tasks.value = json.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchTasks)

// ── Computed ──────────────────────────────────────────────────────────────────
const filteredTasks = computed(() => {
  const kw = filters.keyword.trim().toLowerCase()
  return tasks.value.filter((t) => {
    const statusOk = filters.status === 'all' || t.status === filters.status
    const kwOk = kw
      ? [t.title, t.project, ...(t.tags || [])].join(' ').toLowerCase().includes(kw)
      : true
    return statusOk && kwOk
  })
})

const counts = computed(() => ({
  todo: tasks.value.filter((t) => t.status === 'todo').length,
  in_progress: tasks.value.filter((t) => t.status === 'in_progress').length,
  done: tasks.value.filter((t) => t.status === 'done').length,
  total: tasks.value.length,
}))

const statusPills = [
  { value: 'all', label: '全部' },
  { value: 'todo', label: '待处理' },
  { value: 'in_progress', label: '进行中' },
  { value: 'done', label: '已完成' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────
function toStatusLabel(s) {
  return { todo: '待处理', in_progress: '进行中', done: '已完成' }[s] ?? s
}
function toPriorityLabel(p) {
  return { high: '高', medium: '中', low: '低' }[p] ?? p
}
function priorityColor(p) {
  return { high: '#ef4444', medium: '#f97316', low: '#22c55e' }[p] ?? '#94a3b8'
}
function isOverdue(task) {
  if (!task.dueDate || task.status === 'done') return false
  return new Date(task.dueDate) < new Date(new Date().toDateString())
}
function progressPct(n) {
  const total = counts.value.total
  return total ? Math.round((n / total) * 100) : 0
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openCreate() {
  Object.assign(form, {
    title: '', project: '', priority: 'medium',
    status: 'todo', dueDate: '', tags: '', notes: '',
  })
  modal.editId = null
  modal.open = true
}

function openEdit(task) {
  Object.assign(form, {
    title: task.title,
    project: task.project || '',
    priority: task.priority || 'medium',
    status: task.status || 'todo',
    dueDate: task.dueDate || '',
    tags: (task.tags || []).join(', '),
    notes: task.notes || '',
  })
  modal.editId = task.id
  modal.open = true
}

function closeModal() {
  modal.open = false
  modal.editId = null
}

async function saveTask() {
  if (!form.title.trim()) return
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      project: form.project.trim(),
      priority: form.priority,
      status: form.status,
      dueDate: form.dueDate || null,
      tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      notes: form.notes.trim(),
    }
    let res
    if (modal.editId) {
      res = await fetch(`/api/admin/tasks/${modal.editId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      res = await fetch('/api/admin/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }
    const json = await res.json()
    if (json.success) {
      await fetchTasks()
      closeModal()
    }
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────
function askDelete(id) {
  pendingDelete.value = id
}
function cancelDelete() {
  pendingDelete.value = null
}
async function confirmDelete(id) {
  await fetch(`/api/admin/tasks/${id}`, { method: 'DELETE' })
  pendingDelete.value = null
  await fetchTasks()
}
</script>

<template>
  <div class="at-root">
    <!-- Toolbar -->
    <div class="at-toolbar">
      <input
        v-model="filters.keyword"
        class="at-search"
        type="text"
        placeholder="搜索任务、项目或标签…"
      />
      <div class="at-pills">
        <button
          v-for="pill in statusPills"
          :key="pill.value"
          type="button"
          class="at-pill"
          :class="{ active: filters.status === pill.value }"
          @click="filters.status = pill.value"
        >{{ pill.label }}</button>
      </div>
      <button type="button" class="at-new-btn" @click="openCreate">＋ 新建任务</button>
    </div>

    <!-- Progress bar -->
    <div v-if="counts.total > 0" class="at-progress-wrap">
      <div class="at-progress-bar">
        <div
          class="at-seg at-seg--todo"
          :style="{ width: progressPct(counts.todo) + '%' }"
        ></div>
        <div
          class="at-seg at-seg--inprogress"
          :style="{ width: progressPct(counts.in_progress) + '%' }"
        ></div>
        <div
          class="at-seg at-seg--done"
          :style="{ width: progressPct(counts.done) + '%' }"
        ></div>
      </div>
      <div class="at-progress-legend">
        <span class="at-leg at-leg--todo">待处理 {{ counts.todo }}</span>
        <span class="at-leg at-leg--inprogress">进行中 {{ counts.in_progress }}</span>
        <span class="at-leg at-leg--done">已完成 {{ counts.done }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="at-empty">加载中…</div>

    <!-- Empty state -->
    <div v-else-if="filteredTasks.length === 0" class="at-empty">
      <div class="at-empty-icon">📋</div>
      <p>暂无任务</p>
    </div>

    <!-- Task cards -->
    <div v-else class="at-list">
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="at-card"
        :class="{ 'at-card--overdue': isOverdue(task) }"
        :style="{ '--border-color': priorityColor(task.priority) }"
      >
        <div class="at-card-body">
          <div class="at-card-top">
            <div class="at-card-title-row">
              <strong class="at-card-title">{{ task.title }}</strong>
              <span class="at-card-project">{{ task.project || '未分配项目' }}</span>
            </div>
            <div class="at-card-right">
              <span
                class="at-status-badge"
                :class="`at-status--${task.status}`"
              >{{ toStatusLabel(task.status) }}</span>
              <span
                v-if="task.dueDate"
                class="at-due"
                :class="{ 'at-due--overdue': isOverdue(task) }"
              >{{ task.dueDate }}</span>
            </div>
          </div>

          <p v-if="task.notes" class="at-notes">{{ task.notes }}</p>

          <div class="at-meta">
            <span class="at-priority-badge" :style="{ color: priorityColor(task.priority) }">
              {{ toPriorityLabel(task.priority) }}优先级
            </span>
            <span
              v-for="tag in (task.tags || [])"
              :key="tag"
              class="at-tag"
            >#{{ tag }}</span>
          </div>
        </div>

        <div class="at-actions">
          <button type="button" class="at-edit-btn" @click="openEdit(task)">编辑</button>

          <template v-if="pendingDelete === task.id">
            <span class="at-del-confirm-text">确认删除？</span>
            <button type="button" class="at-del-yes" @click="confirmDelete(task.id)">确认</button>
            <button type="button" class="at-del-no" @click="cancelDelete">取消</button>
          </template>
          <button
            v-else
            type="button"
            class="at-del-btn"
            @click="askDelete(task.id)"
          >删除</button>
        </div>
      </div>
    </div>

    <!-- Modal overlay -->
    <Teleport to="body">
      <div v-if="modal.open" class="at-overlay" @click.self="closeModal">
        <div class="at-modal">
          <h3 class="at-modal-title">{{ modal.editId ? '编辑任务' : '新建任务' }}</h3>

          <div class="at-modal-field">
            <label class="at-label">标题</label>
            <input v-model="form.title" type="text" class="at-input" placeholder="任务标题" />
          </div>

          <div class="at-modal-field">
            <label class="at-label">项目</label>
            <input v-model="form.project" type="text" class="at-input" placeholder="所属项目（可选）" />
          </div>

          <div class="at-modal-field">
            <label class="at-label">优先级</label>
            <div class="at-seg-group">
              <button
                v-for="opt in [{ v: 'high', l: '高' }, { v: 'medium', l: '中' }, { v: 'low', l: '低' }]"
                :key="opt.v"
                type="button"
                class="at-seg-btn"
                :class="{ active: form.priority === opt.v }"
                @click="form.priority = opt.v"
              >{{ opt.l }}</button>
            </div>
          </div>

          <div class="at-modal-field">
            <label class="at-label">状态</label>
            <div class="at-seg-group">
              <button
                v-for="opt in [{ v: 'todo', l: '待处理' }, { v: 'in_progress', l: '进行中' }, { v: 'done', l: '已完成' }]"
                :key="opt.v"
                type="button"
                class="at-seg-btn"
                :class="{ active: form.status === opt.v }"
                @click="form.status = opt.v"
              >{{ opt.l }}</button>
            </div>
          </div>

          <div class="at-modal-field">
            <label class="at-label">截止日期</label>
            <input v-model="form.dueDate" type="date" class="at-input" />
          </div>

          <div class="at-modal-field">
            <label class="at-label">标签（逗号分隔）</label>
            <input v-model="form.tags" type="text" class="at-input" placeholder="frontend, api" />
          </div>

          <div class="at-modal-field">
            <label class="at-label">备注</label>
            <textarea v-model="form.notes" class="at-textarea" rows="3" placeholder="备注信息…"></textarea>
          </div>

          <div class="at-modal-actions">
            <button type="button" class="at-save-btn" :disabled="saving" @click="saveTask">
              {{ saving ? '保存中…' : '保存' }}
            </button>
            <button type="button" class="at-cancel-btn" @click="closeModal">取消</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ── Root ── */
.at-root { display: flex; flex-direction: column; gap: 16px; }

/* ── Toolbar ── */
.at-toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.at-search {
  flex: 1; min-width: 180px; padding: 8px 16px;
  border: 1px solid var(--line); border-radius: 999px;
  background: var(--panel); font-size: .88rem; color: var(--dark);
  outline: none; transition: .2s;
}
.at-search:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }

.at-pills { display: flex; gap: 4px; flex-wrap: wrap; }
.at-pill {
  padding: 6px 16px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--panel);
  color: var(--soft); font-size: .84rem; cursor: pointer; transition: .2s;
}
.at-pill:hover { border-color: var(--c4); color: var(--c4); }
.at-pill.active {
  background: linear-gradient(135deg, var(--c4), var(--c7));
  color: #fff; border-color: transparent;
}

.at-new-btn {
  margin-left: auto; padding: 8px 20px; border-radius: 999px; border: none;
  background: linear-gradient(135deg, var(--c8), var(--c6));
  color: #fff; font-size: .88rem; font-weight: 600; cursor: pointer;
  transition: .2s; white-space: nowrap;
}
.at-new-btn:hover { opacity: .88; transform: translateY(-1px); }

/* ── Progress bar ── */
.at-progress-wrap { display: flex; flex-direction: column; gap: 6px; }
.at-progress-bar {
  height: 6px; border-radius: 999px; overflow: hidden;
  background: var(--bg2); display: flex;
}
.at-seg { height: 100%; transition: width .4s ease; }
.at-seg--todo { background: #94a3b8; }
.at-seg--inprogress { background: #f97316; }
.at-seg--done { background: #22c55e; }

.at-progress-legend { display: flex; gap: 16px; }
.at-leg {
  display: flex; align-items: center; gap: 5px;
  font-size: .78rem; color: var(--soft);
}
.at-leg::before {
  content: ''; display: inline-block;
  width: 8px; height: 8px; border-radius: 50%;
}
.at-leg--todo::before { background: #94a3b8; }
.at-leg--inprogress::before { background: #f97316; }
.at-leg--done::before { background: #22c55e; }

/* ── Empty ── */
.at-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 10px; padding: 48px 20px; color: var(--soft); text-align: center;
}
.at-empty-icon { font-size: 2.4rem; opacity: .7; }

/* ── Card list ── */
.at-list { display: flex; flex-direction: column; gap: 10px; }
.at-card {
  display: flex; align-items: flex-start; gap: 12px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
  border-left: 4px solid var(--border-color, #94a3b8);
  padding: 14px 16px; transition: .2s;
  box-shadow: 0 2px 8px rgba(0,0,0,.03);
}
.at-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.07); }
.at-card--overdue { background: rgba(239,68,68,.04); }

.at-card-body { flex: 1; display: flex; flex-direction: column; gap: 7px; min-width: 0; }
.at-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.at-card-title-row { display: flex; flex-direction: column; gap: 2px; }
.at-card-title { font-size: .95rem; color: var(--dark); line-height: 1.35; }
.at-card-project { font-size: .78rem; color: var(--soft); }
.at-card-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.at-status-badge {
  padding: 2px 10px; border-radius: 999px; font-size: .74rem; font-weight: 600;
}
.at-status--todo { background: rgba(148,163,184,.12); color: #64748b; }
.at-status--in_progress { background: rgba(249,115,22,.12); color: #ea580c; }
.at-status--done { background: rgba(34,197,94,.12); color: #16a34a; }

.at-due { font-size: .78rem; color: var(--soft); }
.at-due--overdue { color: #ef4444; font-weight: 600; }

.at-notes {
  font-size: .84rem; color: var(--soft); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.at-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.at-priority-badge { font-size: .76rem; font-weight: 600; }
.at-tag {
  padding: 2px 8px; border-radius: 999px; font-size: .74rem;
  background: rgba(139,92,246,.08); color: var(--c5);
}

/* ── Actions ── */
.at-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
.at-edit-btn {
  padding: 5px 14px; border-radius: 8px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .82rem;
  cursor: pointer; transition: .2s;
}
.at-edit-btn:hover { border-color: var(--c4); color: var(--c4); }

.at-del-btn {
  padding: 5px 14px; border-radius: 8px; border: 1px solid transparent;
  background: transparent; color: var(--soft); font-size: .82rem;
  cursor: pointer; transition: .2s;
}
.at-del-btn:hover { background: rgba(239,68,68,.08); color: #ef4444; border-color: rgba(239,68,68,.2); }

.at-del-confirm-text { font-size: .8rem; color: #ef4444; white-space: nowrap; }
.at-del-yes {
  padding: 5px 12px; border-radius: 8px; border: none;
  background: #ef4444; color: #fff; font-size: .82rem; cursor: pointer; transition: .2s;
}
.at-del-yes:hover { background: #dc2626; }
.at-del-no {
  padding: 5px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .82rem; cursor: pointer; transition: .2s;
}

/* ── Modal overlay ── */
.at-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,.38); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.at-modal {
  background: var(--panel); border: 1px solid var(--line); border-radius: 20px;
  padding: 28px; width: 100%; max-width: 480px;
  box-shadow: 0 32px 80px rgba(0,0,0,.18);
  display: flex; flex-direction: column; gap: 14px;
  max-height: 90vh; overflow-y: auto;
}
.at-modal-title { font-size: 1.05rem; font-weight: 700; color: var(--dark); }

.at-modal-field { display: flex; flex-direction: column; gap: 5px; }
.at-label { font-size: .82rem; color: var(--soft); font-weight: 500; }
.at-input {
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--bg1); font-size: .88rem; color: var(--dark);
  outline: none; transition: .2s;
}
.at-input:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }
.at-textarea {
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--bg1); font-size: .88rem; color: var(--dark);
  outline: none; resize: vertical; transition: .2s;
}
.at-textarea:focus { border-color: var(--c5); box-shadow: 0 0 0 3px rgba(139,92,246,.08); }

/* ── Segmented buttons ── */
.at-seg-group { display: flex; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.at-seg-btn {
  flex: 1; padding: 7px 10px; border: none; border-right: 1px solid var(--line);
  background: var(--bg1); color: var(--soft); font-size: .84rem;
  cursor: pointer; transition: .15s;
}
.at-seg-btn:last-child { border-right: none; }
.at-seg-btn:hover { background: var(--bg2); }
.at-seg-btn.active { background: var(--c5); color: #fff; font-weight: 600; }

/* ── Modal actions ── */
.at-modal-actions { display: flex; gap: 10px; padding-top: 4px; }
.at-save-btn {
  flex: 1; padding: 10px; border-radius: 10px; border: none;
  background: linear-gradient(135deg, var(--c8), var(--c6));
  color: #fff; font-size: .9rem; font-weight: 600; cursor: pointer; transition: .2s;
}
.at-save-btn:hover:not(:disabled) { opacity: .88; }
.at-save-btn:disabled { opacity: .5; cursor: not-allowed; }
.at-cancel-btn {
  padding: 10px 20px; border-radius: 10px; border: 1px solid var(--line);
  background: transparent; color: var(--soft); font-size: .9rem;
  cursor: pointer; transition: .2s;
}
.at-cancel-btn:hover { border-color: var(--soft); }
</style>
