---
title: "Vue 3 Composition API 实践笔记"
summary: "记录从 Options API 迁移到 Composition API 的实际经验和最佳实践。"
type: blog
tags:
  - Vue
  - 前端
  - JavaScript
coverImage: "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80"
published: false
createdAt: "2026-07-03T12:00:00.000Z"
updatedAt: "2026-07-03T12:00:00.000Z"
---

# Vue 3 Composition API 实践笔记

Vue 3 的 Composition API 带来了全新的代码组织方式。本文记录我在实际项目中的使用心得。

## 为什么选择 Composition API

1. **更好的逻辑复用** — 通过 composables 替代 mixins
2. **更清晰的代码组织** — 相关逻辑可以放在一起
3. **更好的 TypeScript 支持**

## 基础示例

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'

const count = ref(0)
const double = computed(() => count.value * 2)

function increment() {
  count.value++
}

onMounted(() => {
  console.log('组件已挂载')
})
</script>
```

## 封装 Composable

```javascript
// useCounter.js
import { ref, computed } from 'vue'

export function useCounter(initial = 0) {
  const count = ref(initial)
  const double = computed(() => count.value * 2)
  
  function increment() {
    count.value++
  }
  
  function decrement() {
    count.value--
  }
  
  return { count, double, increment, decrement }
}
```

## 使用 Composable

```vue
<script setup>
import { useCounter } from './useCounter'

const { count, double, increment, decrement } = useCounter(10)
</script>
```

## 小结

Composition API 让 Vue 应用的代码组织更加灵活，特别是对于中大型项目来说优势明显。推荐在新项目中优先使用 `<script setup>` 语法。
