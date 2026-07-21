<script setup>
// No logic needed — purely presentational
</script>

<template>
  <div class="nf-wrap">
    <div class="nf-glass">
      <div class="nf-code">404</div>
      <h1 class="nf-title">页面不存在</h1>
      <p class="nf-sub">你要找的页面已经飞走了</p>
      <router-link to="/" class="nf-btn">返回首页</router-link>
    </div>
  </div>
</template>

<style scoped>
.nf-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fff7ed 0%, #fce7f3 50%, #ede9fe 100%);
  padding: 24px;
}

.nf-glass {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: 24px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.10);
  padding: 56px 64px;
  text-align: center;
  max-width: 440px;
  width: 100%;
}

.nf-code {
  font-size: 6rem;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 16px;
  background: linear-gradient(135deg, var(--c1, #f97316), var(--c5, #8b5cf6));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
}

.nf-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.nf-sub {
  font-size: 0.95rem;
  color: #888;
  margin: 0 0 32px;
}

.nf-btn {
  display: inline-block;
  padding: 11px 32px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--c1, #f97316), var(--c5, #8b5cf6));
  color: #fff;
  font-size: 0.92rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.18s, transform 0.18s;
}

.nf-btn:hover {
  opacity: 0.88;
  transform: translateY(-2px);
}
</style>
