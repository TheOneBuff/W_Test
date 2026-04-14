<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="filter-group">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用例名称..."
          prefix-icon="Search"
          clearable
          style="width: 240px"
        />
        <el-select
          v-model="filterProjectId"
          placeholder="所属项目"
          clearable
          style="width: 180px"
        >
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id"/>
        </el-select>
      </div>

      <div class="action-group">
        <el-button @click="init" :icon="Refresh" circle />
        <el-button type="primary" :disabled="selectedRows.length === 0" @click="handleBatchRun">
          批量运行 ({{ selectedRows.length }})
        </el-button>
        <el-button type="primary" @click="handleCreate" :icon="Plus">新建用例</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table :data="pagedData" v-loading="loading" style="width: 100%" @selection-change="handleSelectionChange" row-key="id">
        <el-table-column type="selection" width="55" reserve-selection />
        <el-table-column prop="id" label="ID" width="80" align="center" class-name="text-gray" />

        <el-table-column prop="name" label="用例名称" min-width="200">
          <template #default="{ row }">
            <span class="font-medium text-primary">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="script_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.script_type === 'yaml' ? 'warning' : 'success'" effect="light" size="small">
              {{ row.script_type ? row.script_type.toUpperCase() : 'YAML' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="最近一次执行状态" width="140">
          <template #default="{ row }">
            <div v-if="row.lastExecutionStatus" class="status-badge" :class="row.lastExecutionStatus">
              <span class="dot"></span>
              {{ statusText[row.lastExecutionStatus] || row.lastExecutionStatus }}
            </div>
            <div v-else class="status-badge pending">
              <span class="dot"></span>
              未执行
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" show-overflow-tooltip min-width="150" />

        <el-table-column label="操作" width="280" fixed="right" align="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row.id)">编辑</el-button>

            <el-button type="info" link @click="handleFastRun(row)">运行</el-button>

<!--            <el-button-->
<!--              type="success"
-->
<!--              link-->
<!--              :loading="row.androidLoading"
-->
<!--              @click="handleAndroidRun(row)"
-->
<!--            >
-->
<!--              <el-icon class="el-icon&#45;&#45;left"><Cellphone /></el-icon>
-->
<!--              Android
-->
<!--            </el-button>-->

            <el-divider direction="vertical" />

            <el-popconfirm title="确定删除该用例?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredData.length"
          :page-sizes="[10, 20, 50]"
          layout="total, prev, pager, next, sizes"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useEnvStore } from '@/stores/env'
import axios from '@/utils/request'
import { dispatchTask } from '@/api/android' // 导入 Android API
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Cellphone } from '@element-plus/icons-vue'

const router = useRouter()
const envStore = useEnvStore()

const allData = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const filterProjectId = ref<number | null>(null)
const searchKeyword = ref('')
const selectedRows = ref<any[]>([])

const handleSelectionChange = (val: any[]) => {
  selectedRows.value = val
}

// 状态文本映射
const statusText: any = {
  success: '执行成功',
  failed: '执行失败',
  running: '运行中',
  pending: '等待中'
}

// 分页状态
const currentPage = ref(1)
const pageSize = ref(10)

// 1. 过滤逻辑
const filteredData = computed(() => {
  let res = allData.value
  if (filterProjectId.value) {
    res = res.filter(item => item.project_id === filterProjectId.value)
  }
  if (searchKeyword.value) {
    const k = searchKeyword.value.toLowerCase()
    res = res.filter(item => item.name.toLowerCase().includes(k))
  }
  return res
})

// 2. 分页逻辑
const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

const init = async () => {
  loading.value = true
  try {
    const [pRes, cRes] = await Promise.all([
      axios.get('/projects/'),
      axios.get('/testcases/')
    ])
    projects.value = pRes.data
    
    // 为每个数据项添加 loading 状态字段
    const testCases = cRes.data.map((item: any) => ({ ...item, androidLoading: false }))
    
    // 获取每个测试用例的最新执行状态
    for (const testCase of testCases) {
      try {
        const reportRes = await axios.get(`/testcases/reports/`, {
          params: {
            case_id: testCase.id,
            limit: 1
          }
        })
        
        if (reportRes.data && reportRes.data.items && reportRes.data.items.length > 0) {
          testCase.lastExecutionStatus = reportRes.data.items[0].status
        }
      } catch (e) {
        console.error(`获取测试用例 ${testCase.id} 的执行状态失败:`, e)
      }
    }
    
    allData.value = testCases
  } catch(e) { console.error(e) }
  finally { loading.value = false }
}

// 原有的快速运行 (假设是 HTTP 接口测试)
const handleFastRun = async (row: any) => {
  const envId = envStore.currentEnvId
  const confirmMsg = envId
    ? `即将使用【全局环境 (ID:${envId})】运行测试，确定吗？`
    : `当前未选择环境，将以默认配置运行测试，确定吗？`

  try {
    await ElMessageBox.confirm(confirmMsg, '快速运行', {
      confirmButtonText: '运行',
      cancelButtonText: '取消',
      type: 'info'
    })
    const params = envId ? { env_id: envId } : {}
    const res = await axios.post(`/testcases/${row.id}/run`, null, { params })
    ElMessage.success('任务已提交')
    // 这里假设普通运行也跳转到通用的 report 页面
    // router.push(`/report-view/${res.data.id}`)
  } catch (e) { /* Cancelled */ }
}

// 新增：Android 自动化运行
const handleAndroidRun = async (row: any) => {
  // 可以增加确认框
  try {
    await ElMessageBox.confirm('确定要将此用例下发到 Android 执行器吗？请确保本地执行器已启动并连接手机。', 'Android 执行', {
      confirmButtonText: '下发',
      cancelButtonText: '取消',
      type: 'warning'
    })

    row.androidLoading = true
    try {
      // 调用我们在 api/android.ts 中定义的接口
      const res = await dispatchTask(row.id)

      // [修复] 从 res.data 获取数据，因为 axios 拦截器返回的是完整 Response 对象
      const taskData = res.data

      ElMessage.success(`任务已下发 (Task ID: ${taskData.id})`)

      // 询问是否跳转去查看报告状态
      ElMessageBox.confirm('任务已进入队列，是否前往查看报告状态？', '下发成功', {
        confirmButtonText: '去查看',
        cancelButtonText: '留在本页',
        type: 'success'
      }).then(() => {
        // 跳转到之前设计的 ReportDetail 页面
        router.push(`/report-view/${taskData.id}`)
      }).catch(() => {})

    } catch (error) {
      console.error(error)
      ElMessage.error('任务下发失败')
    } finally {
      row.androidLoading = false
    }
  } catch {
    // Cancelled
  }
}

const handleCreate = () => router.push('/testcases/create')
const handleEdit = (id: number) => router.push(`/testcases/edit/${id}`)
const handleBatchRun = async () => {
  const envId = envStore.currentEnvId
  const caseIds = selectedRows.value.map(row => row.id)
  
  try {
    await ElMessageBox.confirm(
      `确定要批量运行 ${caseIds.length} 个测试用例吗？`, 
      '批量运行', 
      {
        confirmButtonText: '运行',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    const params = envId ? { env_id: envId } : {}
    const res = await axios.post('/testcases/batch-run', { case_ids: caseIds }, { params })

    
    ElMessage.success(`任务已提交，共 ${caseIds.length} 个用例`)
  } catch (e) { /* Cancelled */ }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/testcases/${id}`)
    ElMessage.success('已删除')
    init()
  } catch(e) { ElMessage.error('删除失败') }
}

onMounted(init)
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }

.toolbar-card {
  background: #fff; padding: 16px 20px; border-radius: 8px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.filter-group { display: flex; gap: 12px; }
.action-group { display: flex; gap: 12px; }

.table-card { border: none; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); overflow: hidden; }
.pagination-bar { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid #f9fafb; }

.font-medium { font-weight: 500; }
.text-primary { color: #111827; }
.text-gray { color: #9ca3af; font-family: monospace; }

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

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>