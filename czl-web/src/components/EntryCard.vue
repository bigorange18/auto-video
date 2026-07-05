<script setup>
import { computed } from 'vue'

const props = defineProps({ entry: { type: Object, required: true } })

const labels = { blog: '博客', life: '生活', photo: '摄影' }
const image = computed(() => props.entry.coverImage || props.entry.images?.[0] || '')
const d = computed(() => (props.entry.date || props.entry.createdAt || '').slice(0, 10))
</script>

<template>
  <router-link :to="`/article/${entry.id}`" class="blog-card">
    <div class="blog-card-img" v-if="image" :style="{ backgroundImage: `url(${image})` }"></div>
    <div class="blog-card-body">
      <div class="blog-card-meta">
        <span class="blog-badge">{{ labels[entry.type] || '博客' }}</span>
        <span class="blog-date">{{ d }}</span>
      </div>
      <h3>{{ entry.title }}</h3>
      <p class="blog-summary">{{ entry.summary }}</p>
      <div class="blog-tags" v-if="entry.tags?.length">
        <span v-for="t in entry.tags" :key="t" class="blog-tag">{{ t }}</span>
      </div>
    </div>
  </router-link>
</template>
