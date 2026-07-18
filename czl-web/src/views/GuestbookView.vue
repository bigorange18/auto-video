<script setup>
import { ref, reactive, onMounted } from 'vue'

const messages = ref([])
const loading = ref(true)
const error = ref('')
const formLoading = ref(false)

const form = reactive({ name: '', email: '', body: '' })
const notice = ref('')
const noticeOk = ref(false)

async function fetchMessages() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/public/guestbook')
    const d = await res.json()
    if (d.success) {
      messages.value = d.data || []
    } else {
      error.value = d.message || '加载留言失败'
    }
  } catch {
    error.value = '网络错误，无法加载留言'
  }
  loading.value = false
}

async function submitMessage() {
  if (!form.name || !form.email || !form.body) {
    notice.value = '请完整填写所有字段'
    noticeOk.value = false
    return
  }
  if (form.body.trim().length < 5) {
    notice.value = '留言内容至少 5 个字'
    noticeOk.value = false
    return
  }
  formLoading.value = true
  notice.value = ''
  try {
    const res = await fetch('/api/public/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    const d = await res.json()
    notice.value = d.message || (d.success ? '留言已提交，谢谢！' : '提交失败')
    noticeOk.value = d.success
    if (d.success) {
      form.name = ''
      form.email = ''
      form.body = ''
      await fetchMessages()
    }
  } catch {
    notice.value = '网络错误，提交失败'
    noticeOk.value = false
  }
  formLoading.value = false
}

function formatDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10) + ' ' + iso.slice(11, 16)
}

onMounted(fetchMessages)
</script>

<template>
  <div class="guestbook-shell">
    <section style="text-align:center;margin-bottom:24px">
      <h1 style="font-size:clamp(1.4rem,3.5vw,1.8rem);color:var(--dark);margin-bottom:8px">💬 留言板</h1>
      <p style="color:var(--soft);font-size:.92rem;line-height:1.65">
        欢迎留下你的足迹。任何想说的话、建议或问候，都可以写在这里。
      </p>
    </section>

    <!-- Message Form -->
    <div class="panel guestbook-form">
      <h3 style="font-size:1rem;color:var(--dark);margin-bottom:14px">写留言</h3>
      <form @submit.prevent="submitMessage" style="display:grid;gap:14px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <label style="display:grid;gap:4px">
            <span style="font-size:.84rem;color:var(--soft)">名字</span>
            <input
              v-model="form.name"
              type="text"
              required
              placeholder="你的名字"
              style="width:100%;padding:10px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.9);font-size:.88rem;outline:none"
            />
          </label>
          <label style="display:grid;gap:4px">
            <span style="font-size:.84rem;color:var(--soft)">邮箱</span>
            <input
              v-model="form.email"
              type="email"
              required
              placeholder="your@email.com"
              style="width:100%;padding:10px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.9);font-size:.88rem;outline:none"
            />
          </label>
        </div>
        <label style="display:grid;gap:4px">
          <span style="font-size:.84rem;color:var(--soft)">留言内容</span>
          <textarea
            v-model="form.body"
            rows="4"
            required
            placeholder="想说些什么…"
            style="width:100%;min-height:100px;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.9);font-size:.9rem;outline:none;resize:vertical"
          ></textarea>
        </label>
        <div style="display:flex;align-items:center;gap:14px">
          <button
            type="submit"
            :disabled="formLoading"
            style="padding:10px 24px;border:none;border-radius:999px;background:linear-gradient(135deg,var(--c4),var(--c7));color:#fff;cursor:pointer;font-size:.9rem;transition:.2s"
          >{{ formLoading ? '提交中…' : '发送留言' }}</button>
          <p v-if="notice" :style="{ fontSize: '.86rem', color: noticeOk ? 'var(--c3)' : 'var(--c1)' }">{{ notice }}</p>
        </div>
      </form>
    </div>

    <!-- Messages List -->
    <div v-if="loading" style="margin-top:20px">
      <div v-for="i in 3" :key="i" class="skeleton" style="height:80px;margin-bottom:12px;border-radius:16px" />
    </div>

    <div v-else-if="error" class="empty-state" style="margin-top:20px">
      <p>{{ error }}</p>
    </div>

    <div v-else-if="!messages.length" class="empty-state" style="margin-top:20px">
      <p>还没有留言，来做第一个留言的人吧！</p>
    </div>

    <div v-else class="guestbook-list">
      <div v-for="m in messages" :key="m.id" class="guestbook-item">
        <div class="guestbook-item-head">
          <strong>{{ m.name }}</strong>
          <time>{{ formatDate(m.createdAt) }}</time>
        </div>
        <div class="guestbook-item-body">{{ m.body }}</div>
      </div>
    </div>
  </div>
</template>
