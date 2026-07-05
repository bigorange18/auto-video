<script setup>
import TopNav from './components/TopNav.vue'
</script>

<template>
  <TopNav />
  <router-view v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <component :is="Component" />
    </Transition>
  </router-view>
</template>
