import { ref, watch } from 'vue'

// Singleton ref — shared across all components
const isDark = ref(false)

function applyDark(value) {
  if (value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  localStorage.setItem('czl-theme', value ? 'dark' : 'light')
}

// Initialize once at module load time
const stored = localStorage.getItem('czl-theme')
if (stored === 'dark') {
  isDark.value = true
} else if (stored === 'light') {
  isDark.value = false
} else {
  isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
}
applyDark(isDark.value)

// Sync DOM whenever isDark changes
watch(isDark, applyDark)

export function useDarkMode() {
  function toggle() {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
