<script setup>
import { computed } from 'vue'

const props = defineProps({ entry: { type: Object, required: true } })

const labels = { blog: '博客', life: '生活', photo: '摄影' }
const image = computed(() => props.entry.coverImage || props.entry.images?.[0] || '')
const d = computed(() => (props.entry.date || props.entry.createdAt || '').slice(0, 10))

// Reading time estimate based on summary + title length
const readingTime = computed(() => {
  const text = (props.entry.title || '') + ' ' + (props.entry.summary || '') + ' ' + (props.entry.content || '')
  const words = text.replace(/[\u4e00-\u9fa5]/g, 'x x').split(/\s+/).filter(Boolean).length
  return Math.max(1, Math.round(words / 300))
})

// Gradient placeholder colors cycling through --c1 to --c8
const gradientIndex = computed(() => {
  const id = props.entry.id || ''
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) & 0xffff
  return (hash % 8) + 1
})
</script>

<template>
  <router-link :to="`/article/${entry.id}`" class="blog-card">
    <div
      class="blog-card-img"
      :class="!image ? `blog-card-img--gradient grad-${gradientIndex}` : ''"
      :style="image ? { backgroundImage: `url(${image})` } : {}"
    >
      <span v-if="!image" class="blog-card-img-label">{{ labels[entry.type] || '博客' }}</span>
    </div>
    <div class="blog-card-body">
      <div class="blog-card-meta">
        <span class="blog-badge" :class="`badge-${entry.type || 'blog'}`">{{ labels[entry.type] || '博客' }}</span>
        <span class="blog-date">{{ d }}</span>
        <span class="blog-read-time">约 {{ readingTime }} 分钟</span>
      </div>
      <h3>{{ entry.title }}</h3>
      <p class="blog-summary">{{ entry.summary }}</p>
      <div class="blog-tags" v-if="entry.tags?.length">
        <router-link
          v-for="t in entry.tags"
          :key="t"
          :to="'/tag/' + t"
          class="blog-tag"
          @click.prevent.stop="$router.push('/tag/' + t)"
        >{{ t }}</router-link>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.blog-card {
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.blog-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 36px rgba(0,0,0,0.13);
}
.blog-card-img--gradient {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.05em;
  text-shadow: 0 1px 4px rgba(0,0,0,0.18);
}
.grad-1 { background: linear-gradient(135deg, var(--c1), var(--c2)); }
.grad-2 { background: linear-gradient(135deg, var(--c2), var(--c3)); }
.grad-3 { background: linear-gradient(135deg, var(--c3), var(--c4)); }
.grad-4 { background: linear-gradient(135deg, var(--c4), var(--c5)); }
.grad-5 { background: linear-gradient(135deg, var(--c5), var(--c6)); }
.grad-6 { background: linear-gradient(135deg, var(--c6), var(--c7)); }
.grad-7 { background: linear-gradient(135deg, var(--c7), var(--c8)); }
.grad-8 { background: linear-gradient(135deg, var(--c8), var(--c1)); }

.badge-blog { background: var(--c1) !important; }
.badge-life { background: var(--c4) !important; }
.badge-photo { background: var(--c6) !important; }

.blog-read-time {
  font-size: 0.72rem;
  color: #aaa;
  margin-left: 6px;
}
</style>
