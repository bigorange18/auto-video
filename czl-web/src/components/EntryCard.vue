<script setup>
import { computed } from 'vue'
const props = defineProps({
  entry: {
    type: Object,
    required: true,
  },
})
const typeLabel = {
  blog: '博客',
  life: '生活',
  photo: '摄影',
}
const cardImage = computed(() => {
  return props.entry.images?.[0] || ''
})
</script>

<template>
  <article class="entry-card">
    <div class="entry-card-main">
      <div class="entry-card-text">
        <div class="entry-card-meta">
          <span class="entry-type">{{ typeLabel[entry.type] }}</span>
          <span class="entry-date">{{ entry.date }}</span>
        </div>
        <h3>{{ entry.title }}</h3>
        <p class="entry-summary">{{ entry.summary }}</p>
        <div class="entry-footer">
          <div class="tag-list">
            <span v-for="tag in entry.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <button type="button">查看详情</button>
        </div>
      </div>
      <div v-if="cardImage" class="entry-thumbnail" :style="{ backgroundImage: `url(${cardImage})` }"></div>
    </div>
  </article>
</template>
