<template>
  <div class="dashboard-wrapper">
    <div class="stats-grid">
      <div class="stat-card" v-for="(item, index) in statItems" :key="index">
        <div class="stat-icon-bg" :class="item.colorClass">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">{{ item.label }}</div>
          <div class="stat-value">{{ item.value }}</div>
        </div>
        <div class="stat-decoration">
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M0 100 C 20 0 50 0 100 100 Z" fill="currentColor" opacity="0.1"/>
          </svg>
        </div>
      </div>
    </div>

    <div class="charts-section">
      <div class="chart-container">
        <div class="chart-header">
          <div class="header-title">
            <div class="title-icon"><el-icon><TrendCharts /></el-icon></div>
            <span>用例执行趋势</span>
          </div>
          <el-radio-group v-model="chartDays" size="small" @change="fetchChartData">
            <el-radio-button label="7">近7天</el-radio-button>
            <el-radio-button label="30">近30天</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="chartRef" class="echarts-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import axios from '@/utils/request'
import * as echarts from 'echarts'
import { Document, Monitor, PieChart, Warning, TrendCharts } from '@element-plus/icons-vue'

const stats = reactive({
  total_cases: 0,
  total_envs: 0,
  pass_rate: '0%',
  failed_count: 0
})

const statItems = computed(() => [
  { label: '总用例数', value: stats.total_cases, icon: 'Document', colorClass: 'blue' },
  { label: '环境节点', value: stats.total_envs, icon: 'Monitor', colorClass: 'green' },
  { label: '通过率', value: stats.pass_rate, icon: 'PieChart', colorClass: 'purple' },
  { label: '最近失败', value: stats.failed_count, icon: 'Warning', colorClass: 'red' },
])

const chartDays = ref('7')
const chartRef = ref<HTMLElement>()
let myChart: echarts.ECharts | null = null

const initData = async () => {
  // 并行请求，防止阻塞
  Promise.allSettled([
    axios.get('/testcases/').then(res => stats.total_cases = res.data.length),
    axios.get('/envs/').then(res => stats.total_envs = res.data.length),
    axios.get('/testcases/reports/', { params: { limit: 50 } }).then(res => {
      const reports = Array.isArray(res.data) ? res.data : (res.data.items || [])
      if (reports.length > 0) {
        const passed = reports.filter((r: any) => r.status === 'success').length
        stats.pass_rate = Math.round((passed / reports.length) * 100) + '%'
        stats.failed_count = reports.filter((r: any) => r.status === 'failed').length
      }
    })
  ]).finally(() => fetchChartData())
}

const fetchChartData = async () => {
  if (!myChart && chartRef.value) myChart = echarts.init(chartRef.value)
  myChart?.showLoading({ color: '#4f46e5', maskColor: 'rgba(255,255,255,0.8)' })

  try {
    const res = await axios.get('/dashboard/trend', { params: { days: chartDays.value } })
    const option = {
      tooltip: { 
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderColor: '#e5e7eb',
        textStyle: { color: '#374151' },
        padding: 12
      },
      grid: { top: 30, right: 30, bottom: 20, left: 20, containLabel: true },
      xAxis: {
        type: 'category',
        data: res.data.dates,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#9ca3af', margin: 12 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } },
        axisLabel: { color: '#9ca3af' }
      },
      series: res.data.series.map((item: any, idx: number) => ({
        name: item.name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: idx === 0 ? '#4f46e5' : '#10b981' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: idx === 0 ? 'rgba(79, 70, 229, 0.15)' : 'rgba(16, 185, 129, 0.15)' },
            { offset: 1, color: 'rgba(255,255,255,0)' }
          ])
        },
        data: item.data
      }))
    }
    myChart?.setOption(option)
  } catch (e) { console.error(e) } 
  finally { myChart?.hideLoading() }
}

const handleResize = () => myChart?.resize()
onMounted(() => { initData(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { window.removeEventListener('resize', handleResize); myChart?.dispose() })
</script>

<style scoped>
.dashboard-wrapper { max-width: 1600px; margin: 0 auto; }

/* 卡片 Grid 布局 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  border: 1px solid #f3f4f6;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.stat-icon-bg {
  width: 56px; height: 56px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px;
  margin-right: 20px;
  z-index: 2;
}
.stat-icon-bg.blue { background: #e0e7ff; color: #4f46e5; }
.stat-icon-bg.green { background: #d1fae5; color: #10b981; }
.stat-icon-bg.purple { background: #f3e8ff; color: #9333ea; }
.stat-icon-bg.red { background: #fee2e2; color: #ef4444; }

.stat-content { z-index: 2; }
.stat-label { font-size: 14px; color: #6b7280; margin-bottom: 4px; }
.stat-value { font-size: 32px; font-weight: 700; color: #111827; letter-spacing: -0.5px; }

/* 装饰背景 */
.stat-decoration {
  position: absolute; right: -20px; bottom: -20px;
  width: 120px; height: 120px;
  color: #f3f4f6;
  z-index: 1;
}

/* 图表区域 */
.chart-container {
  background: #fff;
  padding: 24px 32px;
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid #f3f4f6;
}

.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 32px;
}
.header-title { 
  font-size: 18px; font-weight: 600; color: #1f2937; 
  display: flex; align-items: center; gap: 10px; 
}
.title-icon {
  background: #f3f4f6; padding: 6px; border-radius: 8px;
  display: flex; color: #4b5563;
}

.echarts-box { width: 100%; height: 400px; }

@media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stats-grid { grid-template-columns: 1fr; } }
</style>