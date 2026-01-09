<template>
  <div class="dashboard-container">
    <!-- 顶部数据卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="12">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>📚 总用例数</span>
              <el-tag type="primary">Total Cases</el-tag>
            </div>
          </template>
          <div class="card-num">{{ totalCases }}</div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" class="data-card">
          <template #header>
            <div class="card-header">
              <span>🌍 总环境数</span>
              <el-tag type="success">Total Envs</el-tag>
            </div>
          </template>
          <div class="card-num">{{ totalEnvs }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-card shadow="never">
      <template #header>
        <div class="chart-header">
          <span>📈 每日新增用例趋势 (按项目/环境)</span>
          <el-radio-group v-model="chartDays" size="small" @change="fetchChartData">
            <el-radio-button label="7">近7天</el-radio-button>
            <el-radio-button label="30">近30天</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="chartRef" style="width: 100%; height: 400px;"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/utils/request'
import * as echarts from 'echarts'

const totalCases = ref(0)
const totalEnvs = ref(0)
const chartDays = ref('7')
const chartRef = ref<HTMLElement>()
let myChart: echarts.ECharts | null = null

// 初始化数据
const initData = async () => {
  try {
    // 1. 获取统计数字 (需要在后端增加接口，或者前端计算)
    // 这里为了演示，假设直接调用列表接口取长度
    const [caseRes, envRes] = await Promise.all([
      axios.get('/testcases/'),
      axios.get('/envs/')
    ])
    totalCases.value = caseRes.data.length
    totalEnvs.value = envRes.data.length

    // 2. 加载图表
    await fetchChartData()
  } catch (e) {
    console.error(e)
  }
}

// 获取图表数据并渲染
const fetchChartData = async () => {
  if (!myChart && chartRef.value) {
    myChart = echarts.init(chartRef.value)
  }

  myChart?.showLoading()

  try {
    // 调用后端聚合接口 (需要新增)
    // 假设接口返回格式: { dates: ['01-01', '01-02'], series: [{name: 'Project A', data: [1, 5]}] }
    const res = await axios.get('/dashboard/trend', { params: { days: chartDays.value } })

    const option = {
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { top: '10%', left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: res.data.dates },
      yAxis: { type: 'value' },
      series: res.data.series.map((item: any) => ({
        name: item.name,
        type: 'line',
        smooth: true,
        data: item.data
      }))
    }

    myChart?.setOption(option)
  } catch (e) {
    console.error("Chart Error", e)
  } finally {
    myChart?.hideLoading()
  }
}

// 窗口大小变化自适应
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
.dashboard-container { padding: 20px; }
.mb-4 { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-num { font-size: 36px; font-weight: bold; text-align: center; margin-top: 10px; color: #303133; }
.chart-header { display: flex; justify-content: space-between; align-items: center; }
</style>
