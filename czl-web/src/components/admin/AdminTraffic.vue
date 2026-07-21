<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({ recent: [], messageCount: 0, unreadCount: 0 }),
  },
})

const hoveredIndex = ref(null)

const recent = computed(() => {
  const data = props.stats?.recent ?? []
  return data.slice(-14)
})

const maxVal = computed(() => {
  if (!recent.value.length) return 1
  return Math.max(1, ...recent.value.flatMap((d) => [d.pv ?? 0, d.uv ?? 0]))
})

const totalPV = computed(() => recent.value.reduce((s, d) => s + (d.pv ?? 0), 0))
const totalUV = computed(() => recent.value.reduce((s, d) => s + (d.uv ?? 0), 0))
const avgPV = computed(() =>
  recent.value.length ? Math.round(totalPV.value / recent.value.length) : 0,
)
const peakPV = computed(() => Math.max(0, ...recent.value.map((d) => d.pv ?? 0)))

function barHeight(val) {
  return Math.round((val / maxVal.value) * 100)
}

function fmtDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}
</script>

<template>
  <div class="traffic-wrap">
    <div class="chart-header">
      <div class="chart-title">
        <p class="kicker">Analytics</p>
        <h2>流量趋势</h2>
      </div>
      <div class="legend">
        <span class="legend-item pv-legend">PV 页面访问</span>
        <span class="legend-item uv-legend">UV 独立访客</span>
      </div>
    </div>

    <div class="chart-area" v-if="recent.length">
      <div class="y-axis">
        <span class="y-top">{{ maxVal }}</span>
        <span class="y-mid">{{ Math.round(maxVal / 2) }}</span>
        <span class="y-bot">0</span>
      </div>
      <div class="chart-body">
        <div class="grid-lines">
          <div class="grid-line" />
          <div class="grid-line" />
          <div class="grid-line" />
        </div>
        <div class="bars-row">
          <div
            v-for="(day, i) in recent"
            :key="day.date"
            class="bar-group"
            @mouseenter="hoveredIndex = i"
            @mouseleave="hoveredIndex = null"
          >
            <div class="bars">
              <div class="bar pv-bar" :style="{ height: barHeight(day.pv ?? 0) + '%' }" />
              <div class="bar uv-bar" :style="{ height: barHeight(day.uv ?? 0) + '%' }" />
            </div>
            <span class="x-label">{{ fmtDate(day.date) }}</span>
            <div class="tooltip" :class="{ visible: hoveredIndex === i }">
              <strong>{{ fmtDate(day.date) }}</strong>
              <span class="tt-pv">PV: {{ day.pv ?? 0 }}</span>
              <span class="tt-uv">UV: {{ day.uv ?? 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-chart" v-else>暂无流量数据</div>

    <div class="summary-row">
      <div class="summary-item">
        <span class="summary-label">总 PV</span>
        <strong class="summary-val">{{ totalPV.toLocaleString() }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">总 UV</span>
        <strong class="summary-val">{{ totalUV.toLocaleString() }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">日均 PV</span>
        <strong class="summary-val">{{ avgPV.toLocaleString() }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">峰值 PV</span>
        <strong class="summary-val peak">{{ peakPV.toLocaleString() }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.traffic-wrap {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.chart-title h2 {
  font-size: 1.1rem;
  color: var(--dark);
}

.legend {
  display: flex;
  gap: 14px;
  align-items: center;
}

.legend-item {
  font-size: .8rem;
  color: var(--soft);
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-item::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.pv-legend::before { background: var(--c1); }
.uv-legend::before { background: var(--c2); }

/* Chart layout */
.chart-area {
  display: flex;
  gap: 8px;
  height: 180px;
}

.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 22px;
  min-width: 36px;
  flex-shrink: 0;
}

.y-axis span {
  font-size: .72rem;
  color: var(--soft);
  line-height: 1;
}

.chart-body {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.grid-lines {
  position: absolute;
  inset: 0;
  bottom: 22px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}

.grid-line {
  width: 100%;
  height: 1px;
  background: var(--line);
}

.bars-row {
  position: absolute;
  inset: 0;
  bottom: 0;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  padding-bottom: 22px;
}

.bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  position: relative;
  cursor: default;
}

.bars {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 1px;
}

.bar {
  flex: 1;
  border-radius: 3px 3px 0 0;
  min-height: 2px;
  transition: opacity .15s;
}

.pv-bar { background: var(--c1); }
.uv-bar { background: var(--c2); }

.bar-group:hover .bar { opacity: .75; }

.x-label {
  font-size: .62rem;
  color: var(--soft);
  text-align: center;
  margin-top: 4px;
  height: 18px;
  line-height: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

/* Tooltip */
.tooltip {
  position: absolute;
  bottom: calc(100% - 18px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--dark);
  color: #fff;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: .76rem;
  display: flex;
  flex-direction: column;
  gap: 3px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: opacity .15s;
  z-index: 10;
}

.tooltip.visible { opacity: 1; }

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--dark);
}

.tooltip strong {
  font-size: .78rem;
  margin-bottom: 2px;
}

.tt-pv { color: var(--c1); }
.tt-uv { color: var(--c2); }

/* Summary */
.summary-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.summary-item {
  background: var(--bg1);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: .76rem;
  color: var(--soft);
}

.summary-val {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--dark);
}

.summary-val.peak { color: var(--c1); }

.empty-chart {
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--soft);
  font-size: .9rem;
  background: var(--bg1);
  border-radius: 12px;
  border: 1px dashed var(--line);
}

@media (max-width: 600px) {
  .summary-row { grid-template-columns: repeat(2, 1fr); }
  .chart-area { height: 140px; }
  .x-label { font-size: .55rem; }
}
</style>
