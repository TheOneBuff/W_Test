<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="filter-group">
        <span class="label">状态筛选:</span>
        <el-radio-group v-model="filterStatus" @change="handleFilterChange" size="default">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="success">成功</el-radio-button>
          <el-radio-button label="failed">失败</el-radio-button>
          <el-radio-button label="running">运行中</el-radio-button>
        </el-radio-group>
      </div>
      <div class="action-group">
        <el-button type="primary" :icon="Refresh" @click="fetchList" :loading="loading">
          刷新列表
        </el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table
        :data="list"
        v-loading="loading"
        style="width: 100%"
        :header-cell-style="{ background: '#f9fafb', color: '#374151', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center">
          <template #default="{ row }">
            <span class="text-gray">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="测试用例" min-width="200">
          <template #default="{ row }">
            <div class="case-info">
              <span class="case-name" @click="$router.push(`/testcases/edit/${row.test_case_id}`)">
                {{ row.test_case_name || `Case #${row.test_case_id}` }}
              </span>
              <el-tag size="small" type="info" effect="plain" class="ml-2">UI</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="执行状态" width="140">
          <template #default="{ row }">
            <div class="status-badge" :class="row.status">
              <span class="dot"></span>
              {{ statusText[row.status] || row.status }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="执行时间" width="220">
          <template #default="{ row }">
            <div class="time-info">
              <div><el-icon><Clock /></el-icon> {{ formatDate(row.start_time) }}</div>
              <div class="duration" v-if="row.end_time">
                耗时: {{ formatDuration(row.start_time, row.end_time) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewReport(row.id)">
              查看详情
            </el-button>
            <el-divider direction="vertical" />
            <el-button
              type="warning"
              link
              size="small"
              @click="handleRetry(row)"
              :loading="row._loading"
            >
              重跑
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无测试报告" :image-size="100" />
        </template>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import axios from '@/utils/request'
import { useRouter } from 'vue-router'
import { Refresh, Clock } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const router = useRouter()
const list = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')

const statusText: any = {
  success: '执行成功',
  failed: '执行失败',
  running: '运行中',
  pending: '等待中'
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('/testcases/reports/', {
      params: {
        skip: (page.value - 1) * pageSize.value,
        limit: pageSize.value,
        status: filterStatus.value || undefined
      }
    })
    if (res.data && Array.isArray(res.data.items)) {
      list.value = res.data.items
      total.value = res.data.total
    } else {
      list.value = []
      total.value = 0
    }
  } catch(e) { console.error(e) }
  finally { loading.value = false }
}

const handleFilterChange = () => {
  page.value = 1
  fetchList()
}

const viewReport = (id: number) => router.push(`/report-view/${id}`)

const handleRetry = async (row: any) => {
  row._loading = true
  try {
    const res = await axios.post(`/testcases/reports/${row.id}/retry`)
    ElMessage.success('已触发重试')
    fetchList() // 刷新状态
  } catch (e) {
    ElMessage.error('重试失败')
  } finally {
    row._loading = false
  }
}

const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm:ss') : '-'
const formatDuration = (start: string, end: string) => {
  if (!start || !end) return '-'
  return `${dayjs(end).diff(dayjs(start), 'second')}s`
}

onMounted(fetchList)
</script>

<style scoped>
/* 容器 */
.page-container { max-width: 1200px; margin: 0 auto; }

/* 顶部工具栏 */
.toolbar-card {
  background: #fff;
  padding: 16px 24px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.filter-group .label { font-size: 14px; color: #6b7280; margin-right: 12px; font-weight: 500; }

/* 表格卡片 */
.table-card { border: none; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); }
.text-gray { color: #9ca3af; font-family: monospace; }

/* 用例信息 */
.case-info { display: flex; align-items: center; }
.case-name { font-weight: 600; color: #111827; cursor: pointer; transition: color 0.2s; }
.case-name:hover { color: #6366f1; text-decoration: underline; }
.ml-2 { margin-left: 8px; }

/* 状态徽章 (Dot Style) */
.status-badge { display: inline-flex; align-items: center; font-size: 13px; font-weight: 500; }
.status-badge .dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }

.status-badge.success { color: #059669; }
.status-badge.success .dot { background: #10b981; }

.status-badge.failed { color: #dc2626; }
.status-badge.failed .dot { background: #ef4444; }

.status-badge.running { color: #d97706; }
.status-badge.running .dot { background: #f59e0b; animation: pulse 2s infinite; }

.status-badge.pending { color: #6b7280; }
.status-badge.pending .dot { background: #9ca3af; }

/* 时间信息 */
.time-info { font-size: 13px; color: #4b5563; }
.duration { font-size: 12px; color: #9ca3af; margin-top: 2px; }

/* 分页 */
.pagination-bar { padding: 16px 24px; display: flex; justify-content: flex-end; border-top: 1px solid #f3f4f6; }

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>