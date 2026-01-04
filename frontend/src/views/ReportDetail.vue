<template>
  <div class="report-detail">
    <el-page-header @back="router.back()" title="返回" style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
      <template #content>
        <span class="mr-3 text-large font-600">报告详情 #{{ report.id }}</span>
      </template>
      <template #extra>
        <el-button type="primary" @click="handleRetry" :loading="retrying" v-if="report.status !== 'running'">
          <el-icon class="mr-1"><RefreshRight /></el-icon> 重新运行
        </el-button>
        <el-tag :type="statusTag" size="large" effect="dark" class="ml-2">
          {{ report.status.toUpperCase() }}
        </el-tag>
      </template>
    </el-page-header>

    <!-- 状态栏 -->
    <div class="status-bar mb-3">
      <el-descriptions :column="4" border>
        <el-descriptions-item label="开始时间">{{ formatDate(report.start_time) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ formatDate(report.end_time) }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ duration }}</el-descriptions-item>
        <el-descriptions-item label="日志大小">{{ report.logs ? report.logs.length + ' chars' : '0' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 主体内容 -->
    <div class="main-body">
      <!-- 运行中/失败/Pending 显示日志 -->
      <div v-if="report.status !== 'success'" class="log-container">
        <div v-if="report.status === 'running'" class="loading-state">
          <el-icon class="is-loading" :size="40"><Loading /></el-icon>
          <h3 class="mt-2">AI 正在执行测试...</h3>
          <p class="sub-text">Midscene 正在分析页面并规划路径，这通常需要 30秒 到 2分钟。</p>
        </div>

        <div class="console-log">
          <div class="log-header">Console Output</div>
          <pre>{{ report.logs || 'Waiting for logs...' }}</pre>
        </div>
      </div>

      <!-- 成功显示 iframe -->
      <div v-else class="iframe-wrapper">
        <iframe :src="reportUrl" width="100%" height="100%" frameborder="0"></iframe>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { Loading, RefreshRight } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const retrying = ref(false)

interface Report {
  id: number
  status: string
  logs: string
  report_path: string
  start_time: string
  end_time: string
}

const report = ref<Report>({
  id: 0,
  status: 'pending',
  logs: '',
  report_path: '',
  start_time: '',
  end_time: ''
})

let timer: any = null

const statusTag = computed(() => {
  const map: any = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[report.value.status] || 'info'
})

const reportUrl = computed(() => {
  if (!report.value.report_path) return ''
  return `/reports/${report.value.report_path}`
})

const duration = computed(() => {
  if (!report.value.end_time) return '-'
  return dayjs(report.value.end_time).diff(dayjs(report.value.start_time), 'second') + 's'
})

const fetchStatus = async () => {
  try {
    const res = await axios.get(`/testcases/reports/${route.params.id}`)
    report.value = res.data

    if (['pending', 'running'].includes(res.data.status)) {
      timer = setTimeout(fetchStatus, 3000)
    }
  } catch (e) {
    console.error(e)
  }
}

const handleRetry = async () => {
  retrying.value = true
  try {
    const res = await axios.post(`/testcases/reports/${report.value.id}/retry`)
    ElMessage.success('已触发重跑')
    // 跳转到新 ID
    router.push(`/reports/${res.data.id}`)
    // 重置状态以便新页面加载
    report.value = res.data
    fetchStatus()
  } catch (e) {
    ElMessage.error('重跑失败')
  } finally {
    retrying.value = false
  }
}

const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm:ss') : '-'

onMounted(() => {
  fetchStatus()
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.report-detail { height: 100vh; display: flex; flex-direction: column; padding: 20px; background-color: #f5f7fa; box-sizing: border-box; }
.status-bar { background: #fff; padding: 10px; border-radius: 4px; }
.main-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; margin-top: 10px; background: #fff; border-radius: 4px; }

.log-container { flex: 1; display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.loading-state { padding: 40px; text-align: center; background: #fff; border-bottom: 1px solid #eee; }
.sub-text { color: #909399; font-size: 13px; margin-top: 5px; }

.console-log { flex: 1; background: #1e1e1e; color: #a9b7c6; overflow: auto; padding: 0; display: flex; flex-direction: column; }
.log-header { background: #2b2b2b; padding: 5px 10px; font-size: 12px; font-weight: bold; color: #fff; border-bottom: 1px solid #3c3f41; }
.console-log pre { margin: 0; padding: 15px; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 13px; line-height: 1.5; white-space: pre-wrap; }

.iframe-wrapper { flex: 1; overflow: hidden; }
.mb-3 { margin-bottom: 15px; }
.ml-2 { margin-left: 10px; }
.mt-2 { margin-top: 10px; }
</style>
