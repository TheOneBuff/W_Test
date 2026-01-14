<template>
  <div class="detail-container">
    <div class="status-header">
      <div class="left">
        <el-button link @click="router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <span class="divider">/</span>
        <span class="report-title">报告 #{{ report.id }}</span>
        <el-tag :type="statusTag" effect="dark" class="ml-3" size="default">
          {{ report.status ? report.status.toUpperCase() : 'UNKNOWN' }}
        </el-tag>
      </div>

      <div class="right">
        <div class="meta-item">
          <span class="label">开始时间:</span>
          <span class="val">{{ formatDate(report.start_time) }}</span>
        </div>
        <div class="meta-item">
          <span class="label">耗时:</span>
          <span class="val">{{ duration }}</span>
        </div>
        <el-button
          v-if="report.status !== 'running'"
          type="primary"
          plain
          size="small"
          :icon="RefreshRight"
          :loading="retrying"
          @click="handleRetry"
        >
          重跑
        </el-button>
      </div>
    </div>

    <div class="content-body">
      <div v-if="report.status !== 'success'" class="log-wrapper">
        <div v-if="report.status === 'running'" class="running-state">
          <div class="loading-spinner">
            <div class="spinner-ring"></div>
            <el-icon class="icon-spin" :size="32"><Loading /></el-icon>
          </div>
          <h3>AI 正在执行测试...</h3>
          <p>MidScene 正在分析页面并规划路径，实时日志如下：</p>
        </div>

        <div class="console-box">
          <div class="console-header">
            <span>TERMINAL OUTPUT</span>
            <span class="log-size">{{ report.logs ? report.logs.length : 0 }} chars</span>
          </div>
          <div class="console-body">
            <pre>{{ report.logs || '> Waiting for logs...' }}</pre>
          </div>
        </div>
      </div>

      <div v-else class="iframe-wrapper">
        <iframe :src="reportUrl" class="report-iframe" frameborder="0"></iframe>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { Loading, RefreshRight, ArrowLeft } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const retrying = ref(false)
const report = ref<any>({ id: 0, status: 'pending', logs: '', start_time: '', end_time: '' })
let timer: any = null

const statusTag = computed(() => {
  const map: any = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[report.value.status] || 'info'
})

const reportUrl = computed(() => report.value.report_path ? `/reports/${report.value.report_path}` : '')

const duration = computed(() => {
  if (!report.value.end_time || !report.value.start_time) return '-'
  return dayjs(report.value.end_time).diff(dayjs(report.value.start_time), 'second') + 's'
})

const fetchStatus = async () => {
  try {
    const res = await axios.get(`/testcases/reports/${route.params.id}`)
    report.value = res.data
    if (['pending', 'running'].includes(res.data.status)) {
      timer = setTimeout(fetchStatus, 3000)
    }
  } catch (e) { console.error(e) }
}

const handleRetry = async () => {
  retrying.value = true
  try {
    const res = await axios.post(`/testcases/reports/${report.value.id}/retry`)
    ElMessage.success('已触发重跑')
    router.push(`/reports/${res.data.id}`)
    report.value = res.data
    fetchStatus()
  } catch (e) { ElMessage.error('重跑失败') }
  finally { retrying.value = false }
}

const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm:ss') : '-'

onMounted(fetchStatus)
onUnmounted(() => timer && clearTimeout(timer))
</script>

<style scoped>
/* 优化点：
  1. height: 改为 calc(100vh - 88px) -> 100vh - Header(64px) - PaddingTop(24px)
  2. margin: 改为 0 -24px -24px -> 顶部保留父级Padding，左右下抵消Padding
*/
.detail-container {
  height: calc(100vh - 88px);
  display: flex;
  flex-direction: column;
  margin: 0 -24px -24px;
}

/* 顶部状态栏 */
.status-header {
  background: #fff; height: 60px; padding: 0 24px; display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
  border-top-left-radius: 8px; /* 增加圆角，因为上面有间距了 */
  border-top-right-radius: 8px;
}
.left { display: flex; align-items: center; font-size: 16px; font-weight: 600; color: #111827; }
.back-btn { font-size: 14px; color: #6b7280; font-weight: normal; }
.back-btn:hover { color: #111827; }
.divider { margin: 0 12px; color: #d1d5db; font-weight: normal; }
.ml-3 { margin-left: 12px; }

.right { display: flex; align-items: center; gap: 24px; font-size: 13px; color: #6b7280; }
.meta-item .val { color: #111827; font-weight: 500; margin-left: 6px; font-family: monospace; }

/* 内容区 */
.content-body { flex: 1; padding: 0; overflow: hidden; display: flex; flex-direction: column; background: #fff; }

/* 日志区 */
.log-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.running-state {
  padding: 30px; text-align: center; border-bottom: 1px solid #f3f4f6; background: #fff;
}
.running-state h3 { margin: 10px 0 5px; color: #1f2937; }
.running-state p { color: #6b7280; font-size: 13px; margin: 0; }
.icon-spin { animation: spin 2s linear infinite; color: #6366f1; }

.console-box { flex: 1; background: #1e1e1e; display: flex; flex-direction: column; overflow: hidden; }
.console-header {
  background: #2d2d2d; color: #9ca3af; font-size: 11px; padding: 6px 16px; font-weight: 600;
  display: flex; justify-content: space-between; border-bottom: 1px solid #333;
}
.console-body { flex: 1; overflow: auto; padding: 16px; }
.console-body pre {
  margin: 0; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px;
  line-height: 1.6; color: #d4d4d4; white-space: pre-wrap;
}

/* iframe */
.iframe-wrapper { flex: 1; background: #fff; overflow: hidden; }
.report-iframe { width: 100%; height: 100%; display: block; }

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>