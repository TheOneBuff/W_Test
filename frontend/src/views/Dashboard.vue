<template>
  <div class="dashboard-container">
    <el-row :gutter="24" class="mb-6">
      <el-col :span="6">
        <div class="stat-card blue">
          <div class="icon-wrapper"><el-icon><Document /></el-icon></div>
          <div class="content">
            <div class="value">{{ stats.total_cases }}</div>
            <div class="label">总用例数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="icon-wrapper"><el-icon><Monitor /></el-icon></div>
          <div class="content">
            <div class="value">{{ stats.total_envs }}</div>
            <div class="label">环境配置</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card purple">
          <div class="icon-wrapper"><el-icon><PieChart /></el-icon></div>
          <div class="content">
            <div class="value">{{ stats.pass_rate }}</div>
            <div class="label">近期通过率</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card red">
          <div class="icon-wrapper"><el-icon><Warning /></el-icon></div>
          <div class="content">
            <div class="value">{{ stats.failed_count }}</div>
            <div class="label">最近失败</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-card shadow="never" class="chart-card">
      <template #header>
        <div class="card-header">
          <div class="title">
            <el-icon class="mr-2"><TrendCharts /></el-icon>
            每日新增用例趋势
          </div>
          <el-radio-group v-model="chartDays" size="small" @change="fetchChartData">
            <el-radio-button label="7">近7天</el-radio-button>
            <el-radio-button label="30">近30天</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="chartRef" style="width: 100%; height: 350px;"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from '@/utils/request'
import * as echarts from 'echarts'
import { Document, Monitor, PieChart, Warning, TrendCharts } from '@element-plus/icons-vue'

const stats = reactive({
  total_cases: 0,
  total_envs: 0,
  pass_rate: '0%',
  failed_count: 0
})

const chartDays = ref('7')
const chartRef = ref<HTMLElement>()
let myChart: echarts.ECharts | null = null

// 初始化数据
const initData = async () => {
  // [修复] 分开请求，避免一个 404 导致所有数据丢失
  // 1. 获取用例总数
  try {
    const res = await axios.get('/testcases/')
    stats.total_cases = res.data.length
  } catch (e) { console.error('Failed to fetch cases', e) }

  // 2. 获取环境总数 [修复接口地址 /environments/ -> /envs/]
  try {
    const res = await axios.get('/envs/')
    stats.total_envs = res.data.length
  } catch (e) { console.error('Failed to fetch envs', e) }

  // 3. 获取近期报告计算通过率
  try {
    const res = await axios.get('/testcases/reports/', { params: { limit: 50 } })
    // 注意：接口返回结构可能是 { items: [], total: ... }
    const reports = Array.isArray(res.data) ? res.data : (res.data.items || [])

    if (reports.length > 0) {
      const passed = reports.filter((r: any) => r.status === 'success').length
      stats.pass_rate = Math.round((passed / reports.length) * 100) + '%'
      stats.failed_count = reports.filter((r: any) => r.status === 'failed').length
    }
  } catch (e) { console.error('Failed to fetch reports', e) }

  // 4. 加载图表
  await fetchChartData()
}

const fetchChartData = async () => {
  if (!myChart && chartRef.value) {
    myChart = echarts.init(chartRef.value)
  }
  myChart?.showLoading()

  try {
    const res = await axios.get('/dashboard/trend', { params: { days: chartDays.value } })

    const option = {
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, icon: 'circle' },
      grid: { top: '15%', left: '2%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: res.data.dates,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { color: '#6b7280' }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
      },
      series: res.data.series.map((item: any) => ({
        name: item.name,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3 },
        data: item.data
      }))
    }
    myChart?.setOption(option)
  } catch (e) {
    console.error('Chart Error', e)
  } finally {
    myChart?.hideLoading()
  }
}

const handleResize = () => myChart?.resize()

onMounted(() => {
  initData()
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  myChart?.dispose()
})
</script>

<style scoped>
.dashboard-container { padding: 0; }
.mb-6 { margin-bottom: 24px; }

/* 统计卡片样式 */
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  border: 1px solid #f3f4f6;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }

.icon-wrapper {
  width: 56px; height: 56px;
  border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  margin-right: 16px;
}

.content { flex: 1; }
.value { font-size: 28px; font-weight: 700; color: #111827; line-height: 1.2; }
.label { font-size: 14px; color: #6b7280; margin-top: 4px; }

/* 颜色主题 */
.blue .icon-wrapper { background: #eff6ff; color: #3b82f6; }
.green .icon-wrapper { background: #ecfdf5; color: #10b981; }
.purple .icon-wrapper { background: #f5f3ff; color: #8b5cf6; }
.red .icon-wrapper { background: #fef2f2; color: #ef4444; }

.chart-card { border-radius: 12px; border: none; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-size: 16px; font-weight: 600; color: #374151; display: flex; align-items: center; }
.mr-2 { margin-right: 8px; }
</style>