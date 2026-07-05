<script setup>
import { computed } from 'vue'

const props = defineProps({
  entry: { type: Object, required: true },
})

const typeLabel = { blog: '博客', life: '生活', photo: '摄影' }

const cardImage = computed(() => {
  return props.entry.coverImage || props.entry.images?.[0] || ''
})

const displayDate = computed(() => {
  const d = props.entry.date || props.entry.createdAt
  return d ? d.slice(0, 10) : ''
})
</script>

<template>
  <router-link :to="`/article/${entry.id}`" class="blog-card">
    <div class="blog-card-img" v-if="cardImage" :style="{ backgroundImage: `url(${cardImage})` }"></div>
    <div class="blog-card-body">
      <div class="blog-card-meta">
        <span class="blog-type-badge">{{ typeLabel[entry.type] || '博客' }}</span>
        <span class="blog-date">{{ displayDate }}</span>
      </div>
      <h3>{{ entry.title }}</h3>
      <p class="blog-summary">{{ entry.summary }}</p>
      <div class="blog-tags" v-if="entry.tags?.length">
        <span v-for="tag in entry.tags" :key="tag" class="blog-tag">{{ tag }}</span>
      </div>
    </div>
  </router-link>
</template>
