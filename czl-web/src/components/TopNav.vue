<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useDarkMode } from '../composables/useDarkMode.js'

const scrolled = ref(false)
const showContact = ref(false)
const messageForm = reactive({ name: '', email: '', body: '' })
const sending = ref(false)
const notice = ref('')

const { isDark, toggle } = useDarkMode()

function onScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

function openContact() { showContact.value = true; notice.value = '' }
function closeContact() { showContact.value = false }

async function submitMessage() {
  sending.value = true
  notice.value = ''
  const res = await fetch('/api/public/messages', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(messageForm),
  })
  const d = await res.json()
  sending.value = false
  notice.value = d.message || (d.success ? '留言已提交，谢谢！' : '提交失败')
  if (d.success) { messageForm.name = ''; messageForm.email = ''; messageForm.body = '' }
}
</script>

<template>
  <nav class="topnav" :class="{ scrolled }">
    <div class="topnav-inner">
      <router-link to="/" class="topnav-brand">🍊 大橘</router-link>
      <div class="topnav-links">
        <router-link to="/" exact-active-class="active">首页</router-link>
        <router-link to="/about" active-class="active">关于</router-link>
        <router-link to="/projects" active-class="active">项目</router-link>
        <router-link to="/admin">管理</router-link>
        <button
          class="theme-toggle"
          :title="isDark ? '切换到亮色模式' : '切换到暗色模式'"
          @click="toggle"
          aria-label="Toggle dark mode"
        >{{ isDark ? '☀️' : '🌙' }}</button>
        <a href="#" class="contact-trigger" @click.prevent="openContact">联系方式</a>
      </div>
    </div>
  </nav>

  <!-- Contact Modal -->
  <Teleport to="body">
    <div class="modal-overlay" v-if="showContact" @click.self="closeContact">
      <div class="modal-panel">
        <div class="modal-head">
          <h2>💬 联系我</h2>
          <button class="modal-close" @click="closeContact">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="submitMessage">
          <label><span>名字</span><input v-model="messageForm.name" type="text" required placeholder="你的名字" /></label>
          <label><span>邮箱</span><input v-model="messageForm.email" type="email" required placeholder="your@email.com" /></label>
          <label><span>留言</span><textarea v-model="messageForm.body" rows="4" required placeholder="想说些什么…" /></label>
          <button type="submit" :disabled="sending">{{ sending ? '提交中…' : '发送留言' }}</button>
          <p class="modal-notice" v-if="notice" :class="{ success: notice.includes('谢谢') }">{{ notice }}</p>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid transparent;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
  transition: background .2s, border-color .2s, transform .15s;
}
.theme-toggle:hover {
  background: rgba(0, 0, 0, .06);
  border-color: var(--line);
  transform: rotate(20deg);
}
:global(html.dark) .theme-toggle:hover {
  background: rgba(255, 255, 255, .08);
}
</style>
