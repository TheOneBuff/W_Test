<template>
  <div class="report-list">
    <div class="header-actions">
      <el-tag type="info">提示: 报告文件保留 7 天</el-tag>
      <el-button @click="fetchList">
        <el-icon class="mr-1"><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="test_case_id" label="用例" min-width="150">
           <template #default="{ row }">
             <div>
               <el-link type="primary" @click="$router.push(`/testcases/edit/${row.test_case_id}`)">
                 #{{ row.test_case_id }}
               </el-link>
               <span v-if="row.test_case_name" class="ml-2 text-gray-500 text-sm">
                 {{ row.test_case_name }}
               </span>
             </div>
           </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]">{{ row.status ? row.status.toUpperCase() : 'UNKNOWN' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.start_time, row.end_time) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewReport(row.id)">查看</el-button>
            <el-button type="warning" link @click="handleRetry(row)" :loading="row._loading">重跑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-4"
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        @current-change="handlePageChange"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from '@/utils/request'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const router = useRouter()
const list = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const statusMap: any = {
  pending: 'info',
  running: 'warning',
  success: 'success',
  failed: 'danger'
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('/testcases/reports/', {
      params: { skip: (page.value - 1) * pageSize, limit: pageSize }
    })

    // [修复] 适配后端新的返回结构 { total: ..., items: [...] }
    if (res.data && Array.isArray(res.data.items)) {
      list.value = res.data.items
      total.value = res.data.total
    } else {
      // 兼容旧格式（以防万一）
      list.value = Array.isArray(res.data) ? res.data : []
      total.value = list.value.length
    }

  } catch (error) {
    console.error(error)
    ElMessage.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (val: number) => {
  page.value = val
  fetchList()
}

const viewReport = (id: number) => {
  router.push(`/report-view/${id}`)
}

const handleRetry = async (row: any) => {
  row._loading = true
  try {
    const res = await axios.post(`/testcases/reports/${row.id}/retry`)
    ElMessage.success('任务已提交')
    // 可选：直接跳转
    // router.push(`/report-view/${res.data.id}`)
    // 或者刷新列表
    fetchList()
  } catch (e) {
    ElMessage.error('重跑失败')
  } finally {
    row._loading = false
  }
}

const formatDate = (str: string) => {
  if (!str) return '-'
  return dayjs(str).format('MM-DD HH:mm:ss')
}
const formatDuration = (start: string, end: string) => {
  if (!end || !start) return '-'
  const diff = dayjs(end).diff(dayjs(start), 'second')
  return `${diff}s`
}

onMounted(fetchList)
</script>

<style scoped>
.report-list { padding: 20px; }
.header-actions { display: flex; justify-content: space-between; margin-bottom: 20px; align-items: center; }
.mt-4 { margin-top: 20px; text-align: right; }
.ml-2 { margin-left: 8px; }
.text-gray-500 { color: #6b7280; }
.text-sm { font-size: 0.875rem; }
</style>