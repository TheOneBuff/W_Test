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

        <el-table-column label="用例类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.case_type === 'pc' ? 'primary' : 'success'" effect="light" size="small">
              {{ row.case_type === 'pc' ? 'PC' : 'WEB' }}
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

            <el-button
              :type="row.case_type === 'pc' ? 'warning' : 'info'"
              link
              @click="handleRun(row)"
            >
              <el-icon v-if="row.case_type === 'pc'" class="el-icon--left"><Monitor /></el-icon>
              运行
            </el-button>

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

    <el-dialog v-model="executorVisible" title="选择执行器" width="500px" align-center>
      <div class="executor-selector">
        <el-empty v-if="pcExecutors.length === 0 && !executorLoading" description="暂无可用的执行器">
          <template #image>
            <el-icon :size="60" color="#dcdfe6"><Monitor /></el-icon>
          </template>
        </el-empty>
        
        <div v-else v-loading="executorLoading">
          <div class="case-info-box">
            <span class="label">用例:</span>
            <span class="value">{{ currentPcCase?.name }}</span>
          </div>
          
          <el-select
            v-model="selectedExecutorId"
            placeholder="请选择执行器"
            style="width: 100%; margin-top: 16px"
            clearable
          >
            <el-option
              v-for="ex in pcExecutors"
              :key="ex.id"
              :label="`${ex.name} (${ex.ip_address || '无IP'})`"
              :value="ex.id"
            >
              <div class="executor-option">
                <span class="ex-name">{{ ex.name }}</span>
                <span class="ex-ip">{{ ex.ip_address || '无IP' }}</span>
                <el-tag size="small" :type="ex.status === 'online' ? 'success' : 'info'" class="ml-2">
                  {{ ex.status === 'online' ? '在线' : ex.status }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="executorVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExecutorRun" :disabled="!selectedExecutorId">
          确认下发
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useEnvStore } from '@/stores/env'
import axios from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Monitor } from '@element-plus/icons-vue'
import { getExecutorList, dispatchTask } from '@/api/pc'

const router = useRouter()
const envStore = useEnvStore()

const allData = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const filterProjectId = ref<number | null>(null)
const searchKeyword = ref('')
const selectedRows = ref<any[]>([])

const executorVisible = ref(false)
const currentPcCase = ref<any>(null)
const pcExecutors = ref<any[]>([])
const selectedExecutorId = ref<number | null>(null)
const executorLoading = ref(false)

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
const handleRun = async (row: any) => {
  if (row.case_type === 'pc') {
    await showExecutorSelector(row)
  } else {
    await handleFastRun(row)
  }
}

const showExecutorSelector = async (row: any) => {
  currentPcCase.value = row
  executorVisible.value = true
  selectedExecutorId.value = null
  
  executorLoading.value = true
  try {
    const res = await getExecutorList({ status: 'online', limit: 50 })
    pcExecutors.value = (res.data || []).filter((e: any) => e.is_active)
  } catch (e) {
    console.error(e)
    pcExecutors.value = []
  } finally {
    executorLoading.value = false
  }
}

const confirmExecutorRun = async () => {
  if (!selectedExecutorId.value) {
    ElMessage.warning('请选择执行器')
    return
  }
  
  executorVisible.value = false
  
  try {
    const res = await dispatchTask(currentPcCase.value.id, selectedExecutorId.value)
    ElMessage.success(`任务已下发 (Task ID: ${res.data.id})`)
    
    ElMessageBox.confirm('任务已进入队列，是否前往查看报告状态？', '下发成功', {
      confirmButtonText: '去查看',
      cancelButtonText: '留在本页',
      type: 'success'
    }).then(() => {
      router.push(`/report-view/${res.data.id}`)
    }).catch(() => {})
  } catch (e) {
    ElMessage.error('任务下发失败')
  }
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

.executor-selector { padding: 8px 0; }

.case-info-box {
  background: #f9fafb;
  padding: 12px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.case-info-box .label { color: #6b7280; font-size: 13px; }
.case-info-box .value { color: #111827; font-weight: 500; }

.executor-option { display: flex; align-items: center; gap: 8px; }
.ex-name { font-weight: 500; }
.ex-ip { color: #9ca3af; font-size: 12px; }
.ml-2 { margin-left: 8px; }
</style>