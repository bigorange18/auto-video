<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  unreadCount: {
    type: Number,
    default: 0,
  },
})

const messages = ref([])
const filter = ref('all') // 'all' | 'unread'
const pendingDelete = ref(new Set())
const loading = ref(true)

const filtered = computed(() => {
  if (filter.value === 'unread') return messages.value.filter((m) => !m.read)
  return messages.value
})

const localUnread = computed(() => messages.value.filter((m) => !m.read).length)

async function fetchMessages() {
  loading.value = true
  try {
    const res = await fetch('/api/admin/messages')
    const json = await res.json()
    if (json.success) messages.value = json.data
  } finally {
    loading.value = false
  }
}

async function toggleRead(msg) {
  await fetch(`/api/admin/messages/${msg.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ read: !msg.read }),
  })
  msg.read = !msg.read
}

function confirmDelete(id) {
  const next = new Set(pendingDelete.value)
  next.add(id)
  pendingDelete.value = next
}

function cancelDelete(id) {
  const next = new Set(pendingDelete.value)
  next.delete(id)
  pendingDelete.value = next
}

async function removeMessage(id) {
  await fetch(`/api/admin/messages/${id}`, { method: 'DELETE' })
  cancelDelete(id)
  messages.value = messages.value.filter((m) => m.id !== id)
}

function avatarLetter(name) {
  return (name || '?').trim().charAt(0).toUpperCase()
}

function fmtTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffDays < 1) {
    const diffHours = Math.floor(diffMs / 3600000)
    if (diffHours < 1) return '刚刚'
    return `${diffHours}小时前`
  }
  if (diffDays <= 7) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(fetchMessages)
</script>

<template>
  <div class="messages-wrap">
    <div class="messages-header">
      <div>
        <p class="kicker">Inbox</p>
        <h2>
          留言管理
          <span class="unread-badge" v-if="localUnread > 0">{{ localUnread }}</span>
        </h2>
      </div>
      <div class="filter-pills">
        <button
          class="pill"
          :class="{ active: filter === 'all' }"
          type="button"
          @click="filter = 'all'"
        >全部</button>
        <button
          class="pill"
          :class="{ active: filter === 'unread' }"
          type="button"
          @click="filter = 'unread'"
        >
          未读
          <span class="pill-badge" v-if="localUnread > 0">{{ localUnread }}</span>
        </button>
      </div>
    </div>

    <div class="loading-state" v-if="loading">加载中...</div>

    <div class="empty-state" v-else-if="!filtered.length">
      <span v-if="filter === 'unread'">没有未读留言</span>
      <span v-else>暂无留言</span>
    </div>

    <div class="message-list" v-else>
      <article
        v-for="msg in filtered"
        :key="msg.id"
        class="message-card"
        :class="{ unread: !msg.read }"
      >
        <div class="msg-avatar">{{ avatarLetter(msg.name) }}</div>

        <div class="msg-body">
          <div class="msg-meta">
            <strong class="msg-name">{{ msg.name }}</strong>
            <a :href="`mailto:${msg.email}`" class="msg-email">{{ msg.email }}</a>
            <span class="msg-time">{{ fmtTime(msg.createdAt) }}</span>
          </div>

          <p class="msg-text">{{ msg.message }}</p>

          <div class="msg-actions" v-if="!pendingDelete.has(msg.id)">
            <button type="button" class="action-btn" @click="toggleRead(msg)">
              {{ msg.read ? '标记未读' : '标记已读' }}
            </button>
            <button type="button" class="action-btn danger" @click="confirmDelete(msg.id)">
              删除
            </button>
          </div>

          <div class="msg-confirm" v-else>
            <span class="confirm-text">确认删除这条留言？</span>
            <button type="button" class="action-btn danger" @click="removeMessage(msg.id)">确认删除</button>
            <button type="button" class="action-btn" @click="cancelDelete(msg.id)">取消</button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.messages-wrap {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.messages-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.messages-header h2 {
  font-size: 1.1rem;
  color: var(--dark);
  display: flex;
  align-items: center;
  gap: 8px;
}

.unread-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--c4);
  color: #fff;
  font-size: .7rem;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  padding: 0 5px;
}

.filter-pills {
  display: flex;
  gap: 6px;
}

.pill {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--bg1);
  color: var(--soft);
  font-size: .82rem;
  cursor: pointer;
  transition: .15s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.pill:hover { border-color: var(--c4); color: var(--c4); }

.pill.active {
  background: var(--c4);
  border-color: var(--c4);
  color: #fff;
}

.pill-badge {
  background: rgba(255,255,255,.3);
  border-radius: 999px;
  font-size: .7rem;
  font-weight: 700;
  padding: 0 5px;
  min-width: 16px;
  text-align: center;
}

.pill.active .pill-badge { background: rgba(255,255,255,.35); }

/* States */
.loading-state,
.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--soft);
  font-size: .9rem;
  background: var(--bg1);
  border-radius: 12px;
  border: 1px dashed var(--line);
}

/* Message list */
.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-card {
  display: flex;
  gap: 14px;
  padding: 16px;
  background: var(--bg1);
  border: 1px solid var(--line);
  border-left: 3px solid transparent;
  border-radius: 12px;
  transition: border-color .15s;
}

.message-card.unread {
  border-left-color: var(--c4);
  background: color-mix(in srgb, var(--c4) 4%, var(--bg1));
}

/* Avatar */
.msg-avatar {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c4), var(--c5));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .95rem;
  font-weight: 700;
}

.msg-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.msg-meta {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.msg-name {
  font-size: .9rem;
  color: var(--dark);
}

.msg-email {
  font-size: .8rem;
  color: var(--c4);
  text-decoration: none;
}

.msg-email:hover { text-decoration: underline; }

.msg-time {
  font-size: .76rem;
  color: var(--soft);
  margin-left: auto;
}

.msg-text {
  font-size: .875rem;
  color: var(--dark);
  line-height: 1.65;
  word-break: break-word;
}

/* Actions */
.msg-actions,
.msg-confirm {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.confirm-text {
  font-size: .8rem;
  color: var(--soft);
}

.action-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--soft);
  font-size: .78rem;
  cursor: pointer;
  transition: .15s;
}

.action-btn:hover {
  border-color: var(--c4);
  color: var(--c4);
}

.action-btn.danger:hover {
  border-color: var(--c1);
  color: var(--c1);
}

@media (max-width: 600px) {
  .message-card { flex-direction: column; }
  .msg-time { margin-left: 0; }
}
</style>
