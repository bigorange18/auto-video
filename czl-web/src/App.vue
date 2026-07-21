<script setup>
import TopNav from './components/TopNav.vue'
import { useDarkMode } from './composables/useDarkMode.js'

// Initialize singleton — applies dark class before first render
useDarkMode()
</script>

<template>
  <TopNav />
  <router-view v-slot="{ Component }">
    <Transition name="page">
      <component :is="Component" :key="$route.fullPath" />
    </Transition>
  </router-view>
</template>
