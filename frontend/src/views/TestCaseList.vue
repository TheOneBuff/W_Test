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
        <el-button type="primary" @click="handleCreate" :icon="Plus">新建用例</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table :data="pagedData" v-loading="loading" style="width: 100%">
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

        <el-table-column prop="description" label="描述" show-overflow-tooltip min-width="150" />

        <el-table-column label="操作" width="200" fixed="right" align="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row.id)">编辑</el-button>
            <el-button type="success" link @click="handleFastRun(row)">运行</el-button>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEnvStore } from '@/stores/env'
import axios from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

const router = useRouter()
const envStore = useEnvStore()

const allData = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const filterProjectId = ref<number | null>(null)
const searchKeyword = ref('')

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
    allData.value = cRes.data
  } catch(e) { console.error(e) }
  finally { loading.value = false }
}

const handleFastRun = async (row: any) => {
  const envId = envStore.currentEnvId
  const confirmMsg = envId
    ? `即将使用【全局环境 (ID:${envId})】运行，确定吗？`
    : `当前未选择环境，将以默认配置运行，确定吗？`

  try {
    await ElMessageBox.confirm(confirmMsg, '快速运行', {
      confirmButtonText: '运行',
      cancelButtonText: '取消',
      type: 'info'
    })
    const params = envId ? { env_id: envId } : {}
    const res = await axios.post(`/testcases/${row.id}/run`, null, { params })
    ElMessage.success('任务已提交')
    router.push(`/report-view/${res.data.id}`)
  } catch (e) { /* Cancelled */ }
}

const handleCreate = () => router.push('/testcases/create')
const handleEdit = (id: number) => router.push(`/testcases/edit/${id}`)
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
</style>