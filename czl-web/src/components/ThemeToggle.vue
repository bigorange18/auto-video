<script setup>
import { ref, onMounted } from 'vue'

const isDark = ref(false)

function apply() {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

function toggle() {
  isDark.value = !isDark.value
  apply()
}

onMounted(() => {
  // 默认白色，仅当用户手动切过暗色时才恢复
  const stored = localStorage.getItem('theme')
  if (stored === 'dark') isDark.value = true
  apply()
})
</script>

<template>
  <button class="theme-toggle" @click="toggle" :title="isDark ? '切换到浅色模式' : '切换到暗色模式'">
    {{ isDark ? '☀️' : '🌙' }}
  </button>
</template>
