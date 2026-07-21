<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  session: Object,      // { username }
  stats: Object,        // { recent[], messageCount, unreadCount }
  taskSummary: Object,  // { total, status: {todo, in_progress, done}, priority: {high,medium,low}, overdue }
  articles: Array,
  activeTab: String,
})

const emit = defineEmits(['logout', 'update:activeTab'])

const tabs = [
  { key: 'overview',  label: '概览' },
  { key: 'articles',  label: '文章' },
  { key: 'tasks',     label: '任务' },
  { key: 'messages',  label: '消息' },
  { key: 'traffic',   label: '流量' },
  { key: 'content',   label: '内容' },
]

// Last 7 rows of recent traffic
const recentSeven = computed(() => {
  const rows = props.stats?.recent ?? []
  return rows.slice(-7)
})

// Max PV for proportional bar widths
const maxPv = computed(() => {
  const vals = recentSeven.value.map(r => r.pv ?? r.count ?? 0)
  return Math.max(...vals, 1)
})

// Task status totals for progress bars
const taskTotal = computed(() => props.taskSummary?.total || 1)
const todoPct      = computed(() => Math.round(((props.taskSummary?.status?.todo        ?? 0) / taskTotal.value) * 100))
const inProgressPct = computed(() => Math.round(((props.taskSummary?.status?.in_progress ?? 0) / taskTotal.value) * 100))
const donePct      = computed(() => Math.round(((props.taskSummary?.status?.done         ?? 0) / taskTotal.value) * 100))

function setTab(key) {
  emit('update:activeTab', key)
}
</script>

<template>
  <div class="shell-wrap">
    <!-- ── Top Bar ── -->
    <header class="topbar">
      <div class="topbar-left">
        <span class="topbar-icon">🏠</span>
        <span class="topbar-title">管理后台</span>
        <span class="user-badge">{{ session?.username }}</span>
      </div>
      <div class="topbar-right">
        <RouterLink to="/" class="topbar-action-btn">查看前台</RouterLink>
        <button class="topbar-action-btn danger" type="button" @click="emit('logout')">退出登录</button>
      </div>
    </header>

    <!-- ── Overview Stats Row ── -->
    <div class="overview-stats">
      <article class="stat-card" style="--accent: var(--c1)">
        <div class="stat-card-icon">📨</div>
        <div class="stat-card-body">
          <span class="stat-card-label">留言总数</span>
          <strong class="stat-card-value">{{ stats?.messageCount ?? 0 }}</strong>
        </div>
      </article>

      <article class="stat-card" style="--accent: var(--c3)" :class="{ 'stat-alert': (stats?.unreadCount ?? 0) > 0 }">
        <div class="stat-card-icon">🔴</div>
        <div class="stat-card-body">
          <span class="stat-card-label">未读留言</span>
          <strong class="stat-card-value" :class="{ 'val-red': (stats?.unreadCount ?? 0) > 0 }">
            {{ stats?.unreadCount ?? 0 }}
          </strong>
        </div>
      </article>

      <article class="stat-card" style="--accent: var(--c2)">
        <div class="stat-card-icon">📝</div>
        <div class="stat-card-body">
          <span class="stat-card-label">文章数</span>
          <strong class="stat-card-value">{{ articles?.length ?? 0 }}</strong>
        </div>
      </article>

      <article class="stat-card" style="--accent: var(--c4)">
        <div class="stat-card-icon">✅</div>
        <div class="stat-card-body">
          <span class="stat-card-label">任务总数</span>
          <strong class="stat-card-value">{{ taskSummary?.total ?? 0 }}</strong>
        </div>
      </article>

      <article class="stat-card" style="--accent: var(--c5)">
        <div class="stat-card-icon">⚡</div>
        <div class="stat-card-body">
          <span class="stat-card-label">进行中</span>
          <strong class="stat-card-value">{{ taskSummary?.status?.in_progress ?? 0 }}</strong>
        </div>
      </article>

      <article class="stat-card" style="--accent: var(--c6)" :class="{ 'stat-alert': (taskSummary?.overdue ?? 0) > 0 }">
        <div class="stat-card-icon">⚠️</div>
        <div class="stat-card-body">
          <span class="stat-card-label">逾期任务</span>
          <strong class="stat-card-value" :class="{ 'val-red': (taskSummary?.overdue ?? 0) > 0 }">
            {{ taskSummary?.overdue ?? 0 }}
          </strong>
        </div>
      </article>
    </div>

    <!-- ── Tab Navigation ── -->
    <nav class="tab-nav" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        :aria-selected="activeTab === tab.key"
        @click="setTab(tab.key)"
      >
        {{ tab.label }}
        <!-- unread badge on 消息 -->
        <span
          v-if="tab.key === 'messages' && (stats?.unreadCount ?? 0) > 0"
          class="tab-badge tab-badge--red"
        >{{ stats.unreadCount }}</span>
        <!-- overdue badge on 任务 -->
        <span
          v-if="tab.key === 'tasks' && (taskSummary?.overdue ?? 0) > 0"
          class="tab-badge tab-badge--orange"
        >{{ taskSummary.overdue }}</span>
      </button>
    </nav>

    <!-- ── Overview Tab Panel ── -->
    <section v-if="activeTab === 'overview'" class="overview-panel">
      <div class="overview-grid">

        <!-- Mini traffic chart -->
        <div class="ov-card">
          <h3 class="ov-card-title">最近 7 天访问</h3>
          <div v-if="recentSeven.length" class="mini-bars">
            <div
              v-for="row in recentSeven"
              :key="row.date ?? row.day"
              class="mini-bar-row"
            >
              <span class="mini-bar-label">{{ row.date ?? row.day }}</span>
              <div class="mini-bar-track">
                <div
                  class="mini-bar-fill"
                  :style="{ width: ((row.pv ?? row.count ?? 0) / maxPv * 100) + '%' }"
                ></div>
              </div>
              <span class="mini-bar-val">{{ row.pv ?? row.count ?? 0 }}</span>
            </div>
          </div>
          <p v-else class="ov-empty">暂无访问数据</p>
        </div>

        <!-- Task status -->
        <div class="ov-card">
          <h3 class="ov-card-title">任务状态</h3>
          <div class="task-progress-list">
            <div class="task-progress-row">
              <div class="task-progress-meta">
                <span class="task-progress-label">待处理</span>
                <span class="task-progress-count">{{ taskSummary?.status?.todo ?? 0 }}</span>
              </div>
              <div class="task-progress-track">
                <div class="task-progress-fill" style="--fill-color: var(--c2)" :style="{ width: todoPct + '%' }"></div>
              </div>
            </div>
            <div class="task-progress-row">
              <div class="task-progress-meta">
                <span class="task-progress-label">进行中</span>
                <span class="task-progress-count">{{ taskSummary?.status?.in_progress ?? 0 }}</span>
              </div>
              <div class="task-progress-track">
                <div class="task-progress-fill" style="--fill-color: var(--c5)" :style="{ width: inProgressPct + '%' }"></div>
              </div>
            </div>
            <div class="task-progress-row">
              <div class="task-progress-meta">
                <span class="task-progress-label">已完成</span>
                <span class="task-progress-count">{{ taskSummary?.status?.done ?? 0 }}</span>
              </div>
              <div class="task-progress-track">
                <div class="task-progress-fill" style="--fill-color: var(--c3)" :style="{ width: donePct + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Quick actions -->
      <div class="quick-actions">
        <span class="quick-actions-label">快捷操作</span>
        <button type="button" class="quick-btn" @click="setTab('articles')">
          ✏️ 新建文章
        </button>
        <button type="button" class="quick-btn" @click="setTab('tasks')">
          ➕ 新建任务
        </button>
      </div>
    </section>

    <!-- ── Slot for all other tab panels ── -->
    <slot name="tab-content" />
  </div>
</template>

<style scoped>
/* ── Shell wrapper ── */
.shell-wrap {
  max-width: 1120px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  display: grid;
  gap: 20px;
}

/* ── Top Bar ── */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 20px;
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-icon {
  font-size: 1.3rem;
  line-height: 1;
}

.topbar-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--dark);
}

.user-badge {
  padding: 3px 12px;
  border-radius: 999px;
  font-size: .8rem;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(59,130,246,.12), rgba(139,92,246,.12));
  color: var(--c4);
  border: 1px solid rgba(59,130,246,.2);
}

.topbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.topbar-action-btn {
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.88);
  color: var(--dark);
  font-size: .86rem;
  cursor: pointer;
  transition: .2s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.topbar-action-btn:hover {
  border-color: var(--c4);
  color: var(--c4);
}
.topbar-action-btn.danger {
  color: var(--c1);
}
.topbar-action-btn.danger:hover {
  border-color: var(--c1);
  background: rgba(255,107,107,.04);
}

/* ── Overview Stats Row ── */
.overview-stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 900px) {
  .overview-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .overview-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.stat-card {
  padding: 16px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--accent);
  border-radius: 16px;
  background: var(--panel);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: box-shadow .2s, transform .2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,.07);
}
.stat-card.stat-alert {
  background: rgba(255,107,107,.04);
  border-top-color: var(--c1);
}

.stat-card-icon {
  font-size: 1.2rem;
  line-height: 1;
  margin-top: 2px;
}

.stat-card-body {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.stat-card-label {
  font-size: .78rem;
  color: var(--soft);
  white-space: nowrap;
}

.stat-card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--dark);
  line-height: 1.2;
}
.stat-card-value.val-red {
  color: var(--c1);
}

/* ── Tab Navigation ── */
.tab-nav {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 10px 14px;
  backdrop-filter: blur(12px);
}

.tab-btn {
  position: relative;
  padding: 7px 18px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.88);
  color: var(--soft);
  font-size: .86rem;
  cursor: pointer;
  transition: .2s;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.tab-btn:hover {
  border-color: var(--c4);
  color: var(--c4);
}
.tab-btn.active {
  background: linear-gradient(135deg, var(--c4), var(--c7));
  border-color: transparent;
  color: #fff;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  font-size: .7rem;
  font-weight: 700;
  line-height: 1;
  color: #fff;
}
.tab-badge--red    { background: var(--c1); }
.tab-badge--orange { background: var(--c8); }

/* ── Overview Panel ── */
.overview-panel {
  display: grid;
  gap: 16px;
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 700px) {
  .overview-grid { grid-template-columns: 1fr; }
}

.ov-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}

.ov-card-title {
  font-size: .9rem;
  font-weight: 700;
  color: var(--dark);
  margin-bottom: 14px;
}

.ov-empty {
  font-size: .86rem;
  color: var(--soft);
  text-align: center;
  padding: 12px 0;
}

/* Mini bar chart */
.mini-bars {
  display: grid;
  gap: 7px;
}

.mini-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-bar-label {
  font-size: .72rem;
  color: var(--soft);
  width: 72px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mini-bar-track {
  flex: 1;
  height: 7px;
  background: rgba(0,0,0,.06);
  border-radius: 999px;
  overflow: hidden;
}

.mini-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--c4), var(--c7));
  transition: width .4s ease;
  min-width: 2px;
}

.mini-bar-val {
  font-size: .72rem;
  color: var(--soft);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}

/* Task progress */
.task-progress-list {
  display: grid;
  gap: 12px;
}

.task-progress-row {
  display: grid;
  gap: 5px;
}

.task-progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-progress-label {
  font-size: .82rem;
  color: var(--soft);
}

.task-progress-count {
  font-size: .82rem;
  font-weight: 600;
  color: var(--dark);
}

.task-progress-track {
  height: 6px;
  background: rgba(0,0,0,.06);
  border-radius: 999px;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--fill-color, var(--c4));
  transition: width .4s ease;
  min-width: 0;
}

/* Quick actions */
.quick-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px 18px;
  backdrop-filter: blur(12px);
}

.quick-actions-label {
  font-size: .82rem;
  color: var(--soft);
  margin-right: 4px;
}

.quick-btn {
  padding: 8px 18px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--c4), var(--c7));
  color: #fff;
  font-size: .86rem;
  cursor: pointer;
  transition: opacity .2s, transform .2s;
}
.quick-btn:hover {
  opacity: .88;
  transform: translateY(-1px);
}
</style>
