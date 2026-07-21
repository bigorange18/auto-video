<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import EntryCard from '../components/EntryCard.vue'

const route = useRoute()
const allArticles = ref([])
const loading = ref(true)

const tagName = computed(() => route.params.tagName || '')

const filtered = computed(() => {
  if (!tagName.value) return []
  return allArticles.value.filter(a => a.tags?.includes(tagName.value))
})

// Build tag cloud: { tag: count }
const tagCloud = computed(() => {
  const map = {}
  allArticles.value.forEach(a => {
    (a.tags || []).forEach(t => {
      map[t] = (map[t] || 0) + 1
    })
  })
  return Object.entries(map).sort((a, b) => b[1] - a[1])
})

// Cycle through css color vars for tag chips
const colorVars = ['--c1','--c2','--c3','--c4','--c5','--c6','--c7','--c8']
function tagColor(index) {
  return `var(${colorVars[index % colorVars.length]})`
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await fetch('/api/public/articles?pageSize=50')
    const d = await res.json()
    const list = d.data?.articles || d.data || []
    allArticles.value = Array.isArray(list) ? list : []
  } catch {}
  loading.value = false
})
</script>

<template>
  <div class="tag-shell">
    <nav class="tag-back">
      <router-link to="/">&larr; 返回首页</router-link>
    </nav>

    <!-- Loading skeleton -->
    <div v-if="loading" class="tag-container">
      <div class="skeleton" style="width:220px;height:36px;border-radius:10px;margin-bottom:10px" />
      <div class="skeleton" style="width:100px;height:16px;border-radius:6px;margin-bottom:32px" />
      <div class="blog-list">
        <div v-for="i in 3" :key="i" class="skeleton-card">
          <div class="skeleton" style="width:200px;height:130px;border-radius:12px;flex-shrink:0" />
          <div style="display:grid;gap:8px;padding:16px 0">
            <div class="skeleton" style="width:60px;height:12px" />
            <div class="skeleton" style="width:70%;height:20px" />
            <div class="skeleton" style="width:100%;height:13px" />
          </div>
        </div>
      </div>
    </div>

    <!-- Tag cloud (no tagName param) -->
    <div v-else-if="!tagName" class="tag-container">
      <div class="tag-page-header">
        <h1 class="tag-page-title">标签云</h1>
        <p class="tag-page-subtitle">共 {{ tagCloud.length }} 个标签</p>
      </div>
      <div class="tag-cloud">
        <router-link
          v-for="([tag, count], i) in tagCloud"
          :key="tag"
          :to="'/tag/' + tag"
          class="tag-cloud-item"
          :style="{ '--chip-color': tagColor(i) }"
        >
          #{{ tag }}<span class="tag-count">{{ count }}</span>
        </router-link>
      </div>
    </div>

    <!-- Specific tag articles -->
    <div v-else class="tag-container">
      <div class="tag-page-header">
        <h1 class="tag-page-title">
          <span class="tag-hash-chip">#{{ tagName }}</span>
        </h1>
        <p class="tag-page-subtitle">共 {{ filtered.length }} 篇文章</p>
      </div>

      <!-- Articles grid -->
      <div v-if="filtered.length" class="blog-list">
        <EntryCard v-for="a in filtered" :key="a.id" :entry="a" />
      </div>

      <!-- Empty state -->
      <div v-else class="tag-empty">
        <span class="empty-emoji">🏷️</span>
        <p>没有找到标签 <strong>#{{ tagName }}</strong> 的文章</p>
        <router-link to="/tags" class="tag-browse-link">浏览所有标签</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-shell {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 20px 60px;
}

.tag-back {
  margin-bottom: 24px;
  font-size: 0.88rem;
}
.tag-back a {
  color: var(--soft);
  transition: color 0.18s;
}
.tag-back a:hover {
  color: var(--c8);
}

.tag-container {
  /* intentionally unstyled wrapper */
}

.tag-page-header {
  margin-bottom: 28px;
}

.tag-page-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--dark);
  display: flex;
  align-items: center;
  gap: 10px;
  line-height: 1.3;
}

.tag-hash-chip {
  display: inline-block;
  padding: 4px 18px;
  border-radius: 999px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--c8) 14%, transparent), color-mix(in srgb, var(--c6) 12%, transparent));
  border: 1px solid color-mix(in srgb, var(--c8) 28%, transparent);
  color: var(--c8);
  font-size: 1.6rem;
}

.tag-page-subtitle {
  margin-top: 6px;
  font-size: 0.88rem;
  color: var(--soft);
}

/* Tag cloud */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 24px 28px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}

.tag-cloud-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--chip-color, var(--c1));
  background: color-mix(in srgb, var(--chip-color, var(--c1)) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--chip-color, var(--c1)) 28%, transparent);
  text-decoration: none;
  transition: transform 0.15s, box-shadow 0.15s;
}
.tag-cloud-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--chip-color, var(--c1)) 28%, transparent);
}

.tag-count {
  font-size: 0.74rem;
  font-weight: 400;
  opacity: 0.75;
  background: color-mix(in srgb, var(--chip-color, var(--c1)) 18%, transparent);
  border-radius: 999px;
  padding: 1px 7px;
}

/* Empty state */
.tag-empty {
  text-align: center;
  padding: 60px 20px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  backdrop-filter: blur(16px);
}
.tag-empty .empty-emoji {
  display: block;
  font-size: 2.5rem;
  margin-bottom: 12px;
}
.tag-empty p {
  color: var(--soft);
  font-size: 0.95rem;
  margin-bottom: 16px;
}
.tag-browse-link {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 999px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--c8) 14%, transparent), color-mix(in srgb, var(--c6) 12%, transparent));
  border: 1px solid color-mix(in srgb, var(--c8) 28%, transparent);
  color: var(--c8);
  font-size: 0.86rem;
  font-weight: 600;
  transition: transform 0.15s;
}
.tag-browse-link:hover {
  transform: translateY(-2px);
}
</style>
