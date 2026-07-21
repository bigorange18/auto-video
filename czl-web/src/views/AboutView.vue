<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMeta } from '../composables/useMeta.js'

const content = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/public/content')
    const d = await res.json()
    if (d.success) content.value = d.data
  } catch { /* */ }
  loading.value = false
  useMeta({
    title: '关于我 — 大橘',
    description: content.value?.intro?.summary || '这里展示正在推进的项目、稳定积累的方法，以及我对前端、工程化和内容组织的长期兴趣。',
    url: window.location.href,
  })
})

const skillGroups = computed(() => {
  const all = content.value?.skills || []
  const front = ['HTML / CSS', 'JavaScript', 'TypeScript', 'Vue.js', 'React', 'UI / UX 设计']
  const back  = ['Node.js']
  const tools = ['Git', 'Webpack', 'Docker']
  const group = (labels) => all.filter(s => labels.includes(s))
  const rest  = all.filter(s => !front.includes(s) && !back.includes(s) && !tools.includes(s))
  return [
    { label: '前端', color: 'c4', skills: group(front) },
    { label: '后端', color: 'c3', skills: group(back) },
    { label: '工具', color: 'c5', skills: group(tools) },
    ...(rest.length ? [{ label: '其他', color: 'c8', skills: rest }] : []),
  ].filter(g => g.skills.length)
})

const timeline = [
  {
    range: '2023 — 现在',
    role: '全栈工程师',
    org: '独立开发者',
    desc: '专注个人项目开发与技术内容创作，构建个人品牌站点，探索 AI 驱动的工作流自动化。',
  },
  {
    range: '2021 — 2023',
    role: '前端工程师',
    org: '某互联网公司',
    desc: '负责核心产品前端架构，主导组件库建设与设计系统落地，推进工程化与性能优化。',
  },
  {
    range: '2019 — 2021',
    role: '前端开发',
    org: '某科技创业公司',
    desc: '参与多个 SaaS 产品从零到一，技术栈覆盖 Vue / React，完成 CI/CD 流程搭建。',
  },
  {
    range: '2015 — 2019',
    role: '计算机科学学士',
    org: '某高校',
    desc: '主修软件工程，辅修 UI 设计。期间参与多个校级开源项目，获校优秀毕业生。',
  },
]

const interests = [
  { icon: '🌱', title: '开源项目', desc: '相信开放协作的力量，积极参与开源社区，把能复用的工具都做成可分享的形态。' },
  { icon: '🎬', title: '内容创作', desc: '把技术积累转化为文章、视频或工具，让方法论可以沉淀和传播，而不是消耗在脑子里。' },
  { icon: '🤖', title: 'AI 探索', desc: '持续跟进 AI 工具链的演进，把 LLM 能力融入日常工作流，而不只是体验 Demo。' },
]
</script>

<template>
  <div class="about-page">

    <!-- Hero -->
    <section class="about-hero">
      <div class="hero-inner">
        <div class="hero-avatar">🍊</div>
        <div class="hero-text">
          <h1 class="hero-name">{{ content?.site?.title || '大橘' }}</h1>
          <p class="hero-title">{{ content?.site?.subtitleName || '全栈工程师 · 内容创作者' }}</p>
          <p class="hero-bio">
            {{ content?.intro?.summary || '这里展示正在推进的项目、稳定积累的方法，以及我对前端、工程化和内容组织的长期兴趣。' }}
          </p>
        </div>
      </div>
    </section>

    <div class="about-body">

      <!-- Timeline -->
      <section class="about-section">
        <div class="section-label">
          <span class="kicker-tag">Experience</span>
          <h2>我的经历</h2>
        </div>
        <div class="timeline">
          <div v-for="(item, i) in timeline" :key="i" class="tl-item">
            <div class="tl-dot" />
            <div class="tl-card">
              <span class="tl-range">{{ item.range }}</span>
              <h3 class="tl-role">{{ item.role }}</h3>
              <p class="tl-org">{{ item.org }}</p>
              <p class="tl-desc">{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Skills -->
      <section class="about-section" v-if="!loading">
        <div class="section-label">
          <span class="kicker-tag">Skills</span>
          <h2>技能栈</h2>
        </div>
        <div class="skill-groups">
          <div v-for="g in skillGroups" :key="g.label" class="skill-group">
            <p class="skill-group-label" :class="`color-${g.color}`">{{ g.label }}</p>
            <div class="skill-tags">
              <span
                v-for="s in g.skills" :key="s"
                class="skill-tag" :class="`tag-${g.color}`"
              >{{ s }}</span>
            </div>
          </div>
        </div>
      </section>
      <section class="about-section" v-else>
        <div class="skeleton" style="width:120px;height:20px;margin-bottom:20px" />
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <div v-for="i in 8" :key="i" class="skeleton" style="width:80px;height:30px;border-radius:999px" />
        </div>
      </section>

      <!-- Interests -->
      <section class="about-section">
        <div class="section-label">
          <span class="kicker-tag">Interests</span>
          <h2>我在意的事</h2>
        </div>
        <div class="interest-grid">
          <div v-for="item in interests" :key="item.title" class="interest-card">
            <div class="interest-icon">{{ item.icon }}</div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<style scoped>
.about-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px 80px;
}

/* Hero */
.about-hero {
  padding: 52px 0 40px;
}
.hero-inner {
  display: flex;
  gap: 32px;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 36px 40px;
  backdrop-filter: blur(18px);
  box-shadow: var(--shadow);
}
.hero-avatar {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c8), var(--c6), var(--c5));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.4rem;
  flex-shrink: 0;
}
.hero-text { display: grid; gap: 6px; }
.hero-name  { font-size: 1.8rem; font-weight: 800; color: var(--dark); }
.hero-title { font-size: .95rem; color: var(--c8); font-weight: 500; }
.hero-bio   { font-size: .92rem; color: var(--soft); line-height: 1.75; margin-top: 4px; }

/* Body */
.about-body { display: grid; gap: 40px; }

.about-section {}

.section-label { margin-bottom: 20px; }
.kicker-tag {
  display: inline-block;
  font-size: .72rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--c8);
  margin-bottom: 4px;
}
.section-label h2 { font-size: 1.25rem; color: var(--dark); }

/* Timeline */
.timeline {
  position: relative;
  padding-left: 28px;
  border-left: 2px solid var(--line);
  display: grid;
  gap: 8px;
}
.tl-item {
  position: relative;
  padding-bottom: 8px;
}
.tl-dot {
  position: absolute;
  left: -35px;
  top: 14px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c8), var(--c6));
  border: 2px solid var(--bg1);
  box-shadow: 0 0 0 3px rgba(249,115,22,.15);
}
.tl-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px 20px;
  backdrop-filter: blur(14px);
  box-shadow: 0 8px 24px rgba(0,0,0,.04);
  display: grid;
  gap: 4px;
  transition: .2s;
}
.tl-card:hover {
  transform: translateX(3px);
  box-shadow: 0 12px 32px rgba(0,0,0,.08);
}
.tl-range { font-size: .76rem; color: var(--c8); font-weight: 600; letter-spacing: .04em; }
.tl-role  { font-size: 1rem; font-weight: 700; color: var(--dark); }
.tl-org   { font-size: .84rem; color: var(--c4); }
.tl-desc  { font-size: .86rem; color: var(--soft); line-height: 1.65; margin-top: 4px; }

/* Skills */
.skill-groups { display: grid; gap: 20px; }
.skill-group { display: grid; gap: 10px; }
.skill-group-label {
  font-size: .8rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.color-c3 { color: var(--c3); }
.color-c4 { color: var(--c4); }
.color-c5 { color: var(--c5); }
.color-c8 { color: var(--c8); }

.skill-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.skill-tag {
  padding: 5px 14px;
  border-radius: 999px;
  font-size: .82rem;
  font-weight: 500;
  border: 1px solid transparent;
  transition: .2s;
}
.skill-tag:hover { transform: translateY(-1px); }
.tag-c4 { background: rgba(59,130,246,.08);  color: var(--c4); border-color: rgba(59,130,246,.18); }
.tag-c3 { background: rgba(16,185,129,.08);  color: var(--c3); border-color: rgba(16,185,129,.18); }
.tag-c5 { background: rgba(139,92,246,.08);  color: var(--c5); border-color: rgba(139,92,246,.18); }
.tag-c8 { background: rgba(249,115,22,.08);  color: var(--c8); border-color: rgba(249,115,22,.18); }

/* Interests */
.interest-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.interest-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 22px 20px;
  backdrop-filter: blur(14px);
  box-shadow: 0 8px 24px rgba(0,0,0,.04);
  display: grid;
  gap: 8px;
  transition: .25s;
}
.interest-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 40px rgba(0,0,0,.09);
}
.interest-icon { font-size: 1.8rem; }
.interest-card h3 { font-size: .98rem; font-weight: 700; color: var(--dark); }
.interest-card p  { font-size: .84rem; color: var(--soft); line-height: 1.65; }

@media (max-width: 700px) {
  .hero-inner { flex-direction: column; text-align: center; padding: 28px 22px; }
  .interest-grid { grid-template-columns: 1fr; }
}
@media (max-width: 500px) {
  .interest-grid { grid-template-columns: 1fr; }
}
</style>
