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
        <el-table-column prop="test_case_id" label="用例ID" width="100">
           <template #default="{ row }">
             <el-link type="primary" @click="$router.push(`/testcases/edit/${row.test_case_id}`)">
               #{{ row.test_case_id }}
             </el-link>
           </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]">{{ row.status.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间">
          <template #default="{ row }">
            {{ formatDate(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="耗时">
          <template #default="{ row }">
            {{ formatDuration(row.start_time, row.end_time) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewReport(row.id)">查看详情</el-button>
            <el-button type="warning" link @click="handleRetry(row)" :loading="row._loading">重跑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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
    list.value = res.data
    // 假设后端没有返回 total，这里暂时 mock 或者需要后端支持 count 接口
    total.value = 100
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
    // 跳转到新报告
    router.push(`/report-view/${res.data.id}`)
  } catch (e) {
    ElMessage.error('重跑失败')
  } finally {
    row._loading = false
  }
}

const formatDate = (str: string) => dayjs(str).format('MM-DD HH:mm:ss')
const formatDuration = (start: string, end: string) => {
  if (!end) return '-'
  const diff = dayjs(end).diff(dayjs(start), 'second')
  return `${diff}s`
}

onMounted(fetchList)
</script>

<style scoped>
.report-list { padding: 20px; }
.header-actions { display: flex; justify-content: space-between; margin-bottom: 20px; align-items: center; }
.mt-4 { margin-top: 20px; text-align: right; }
</style>
