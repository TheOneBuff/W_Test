<template>
  <div class="detail-container">
    <div class="status-header">
      <div class="left">
        <el-button link @click="router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <span class="divider">/</span>
        <span class="report-title">测试报告 #{{ report.id }}</span>

        <el-tag :type="statusTag" effect="dark" class="ml-3" size="default">
          <span v-if="report.status === 'running'">RUNNING</span>
          <span v-else-if="report.status === 'pending'">PENDING</span>
          <span v-else>{{ report.status ? report.status.toUpperCase() : 'UNKNOWN' }}</span>
        </el-tag>
      </div>

      <div class="right">
        <div class="meta-item" v-if="report.test_case_id">
          <span class="label">Case ID:</span>
          <span class="val">{{ report.test_case_id }}</span>
        </div>

        <div class="meta-item">
          <span class="label">开始时间:</span>
          <span class="val">{{ formatDate(report.start_time) }}</span>
        </div>
        <div class="meta-item">
          <span class="label">耗时:</span>
          <span class="val">{{ duration }}</span>
        </div>

        <el-button
          v-if="report.status !== 'running' && report.status !== 'pending'"
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

        <div v-if="report.status === 'running' || report.status === 'pending'" class="running-state">
          <div class="loading-spinner">
            <el-icon class="icon-spin" :size="24"><Loading /></el-icon>
          </div>
          <h3>AI 正在执行测试...</h3>
          <p v-if="report.status === 'pending'">任务排队中，等待执行器接单...</p>
          <p v-else>MidScene 正在分析页面并规划路径</p>
        </div>

        <div class="console-box">
          <div class="console-header">
            <span>TERMINAL OUTPUT</span>
            <span class="log-size">{{ report.logs ? report.logs.length : 0 }} chars</span>
          </div>
          <div class="console-body" ref="consoleBodyRef">
            <pre>{{ report.logs || '> Waiting for logs...' }}</pre>
          </div>
        </div>
      </div>

      <div v-else class="iframe-wrapper">
        <iframe v-if="reportUrl" :src="reportUrl" class="report-iframe" frameborder="0"></iframe>
        <div v-else class="empty-state">
          <p>报告生成成功，但文件路径丢失。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/request'
import { dispatchTask } from '@/api/android' // 复用之前定义的 API
import { Loading, RefreshRight, ArrowLeft } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const retrying = ref(false)

// 报告数据模型
const report = ref<any>({
  id: 0,
  test_case_id: 0,
  status: 'pending',
  logs: '',
  start_time: '',
  end_time: '',
  report_path: ''
})

const consoleBodyRef = ref<HTMLElement>()
let timer: any = null

// 状态颜色映射
const statusTag = computed(() => {
  const map: any = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return map[report.value.status] || 'info'
})

// 计算静态资源 URL (需匹配后端 StaticFiles 挂载路径)
const reportUrl = computed(() => {
  if (!report.value.report_path) return ''
  // 确保路径不重复拼接 /reports/
  const path = report.value.report_path.startsWith('/') ? report.value.report_path.slice(1) : report.value.report_path
  return `/reports/${path}`
})

// 计算耗时
const duration = computed(() => {
  if (!report.value.end_time || !report.value.start_time) return '-'
  return dayjs(report.value.end_time).diff(dayjs(report.value.start_time), 'second') + 's'
})

// 轮询获取状态
const fetchStatus = async () => {
  try {
    // 假设后端有通用的 GET /api/reports/{id} 接口
    const res = await request.get(`/api/reports/${route.params.id}`)
    report.value = res.data // 确保 res.data 包含 TestReportOut 的所有字段

    // 如果是 Pending 或 Running，继续轮询
    if (['pending', 'running'].includes(res.data.status)) {
      timer = setTimeout(fetchStatus, 2000)
    }
  } catch (e) {
    console.error(e)
    // 可以添加 404 处理
  }
}

// 自动滚动日志到底部
watch(() => report.value.logs, () => {
  nextTick(() => {
    if (consoleBodyRef.value) {
      consoleBodyRef.value.scrollTop = consoleBodyRef.value.scrollHeight
    }
  })
})

// 处理重跑：重新下发任务 -> 跳转到新报告
const handleRetry = async () => {
  if (!report.value.test_case_id) {
    ElMessage.error('无法获取关联用例 ID')
    return
  }

  retrying.value = true
  try {
    // 调用 Android 分发接口
    const res = await dispatchTask(report.value.test_case_id)

    // [修复] res 是 AxiosResponse 对象，实际数据在 res.data 中
    const newReport = res.data

    ElMessage.success(`重跑任务已创建 (ID: ${newReport.id})`)

    // 跳转到新报告页面
    router.push(`/report-view/${newReport.id}`)

    // 更新当前页面数据模型
    report.value = newReport

    // 立即刷新状态
    fetchStatus()

  } catch (e) {
    console.error(e)
    ElMessage.error('重跑请求失败')
  } finally {
    retrying.value = false
  }
}

const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm:ss') : '-'

// 监听路由变化 (解决在当前页面点重跑跳转后数据不刷新的问题)
watch(() => route.params.id, (newId) => {
  if (newId) {
    if (timer) clearTimeout(timer)
    fetchStatus()
  }
})

onMounted(fetchStatus)
onUnmounted(() => timer && clearTimeout(timer))
</script>

<style scoped>
/* [核心修复]
  1. 移除 margin: -24px，回归标准流，杜绝左侧被切。
  2. height: calc(100vh - 120px)。计算方式：Header(64) + PaddingTop(24) + PaddingBottom(24) + 余量(8) = 120px
*/
.detail-container {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

.status-header {
  height: 56px; padding: 0 20px; display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #e5e7eb; flex-shrink: 0; background: #fff;
}
.left { display: flex; align-items: center; font-size: 15px; font-weight: 600; color: #111827; }
.back-btn { font-size: 14px; color: #6b7280; font-weight: normal; }
.divider { margin: 0 10px; color: #d1d5db; }
.ml-3 { margin-left: 12px; }
.right { display: flex; align-items: center; gap: 20px; font-size: 13px; color: #6b7280; }
.meta-item .val { color: #111827; font-weight: 500; margin-left: 6px; font-family: monospace; }

.content-body { flex: 1; padding: 0; overflow: hidden; display: flex; flex-direction: column; position: relative; }
.log-wrapper { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.running-state {
  padding: 12px; text-align: center; border-bottom: 1px solid #333; background: #1e1e1e; color: #fff; flex-shrink: 0;
}
.running-state h3 { margin: 4px 0; font-size: 14px; font-weight: normal; }
.running-state p { color: #999; font-size: 12px; margin: 0; }
.icon-spin { animation: spin 2s linear infinite; color: #409eff; }

.console-box {
  flex: 1;
  background: #1e1e1e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.console-header {
  background: #252526; color: #9ca3af; font-size: 11px; padding: 4px 16px; font-weight: 600;
  display: flex; justify-content: space-between; border-bottom: 1px solid #333; flex-shrink: 0;
}
.console-body {
  flex: 1;
  overflow: auto;
  padding: 16px; /* 容器内边距 */
  min-width: 0;
}
.console-body pre {
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
  padding-left: 4px; /* [核心修复] 额外的文字左侧安全距离 */
}

.iframe-wrapper { flex: 1; background: #fff; overflow: hidden; }
.report-iframe { width: 100%; height: 100%; display: block; border: none; }
.empty-state { display: flex; justify-content: center; align-items: center; height: 100%; color: #999; }

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>