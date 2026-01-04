<template>
  <div class="test-case-list">
    <!-- 头部操作区 -->
    <div class="header-actions">
      <!-- 筛选区 -->
      <div class="filter-box">
        <el-select
          v-model="filterProjectId"
          placeholder="按项目筛选"
          clearable
          @change="handleFilterChange"
          style="width: 200px;"
        >
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id"/>
        </el-select>

        <el-button @click="init" icon="Refresh">刷新</el-button>
      </div>

      <!-- 新建按钮 -->
      <el-button type="primary" @click="handleCreate">
        <el-icon class="mr-1"><Plus /></el-icon> 新建测试用例
      </el-button>
    </div>

    <!-- 表格区域 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="用例名称" width="200" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />

        <!-- 类型标签 -->
        <el-table-column prop="script_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.script_type === 'yaml' ? 'warning' : 'success'">
              {{ row.script_type.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 操作栏 -->
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row.id)">编辑</el-button>
            <!-- 修改这里：绑定新的快速运行方法 -->
            <el-button type="success" link @click="handleFastRun(row)">运行</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEnvStore } from '@/stores/env' // 1. 引入 Store
import axios from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const envStore = useEnvStore() // 2. 初始化

const tableData = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const filterProjectId = ref(null)

const init = async () => {
  loading.value = true
  try {
    const [pRes, cRes] = await Promise.all([
      axios.get('/projects/'),
      axios.get('/testcases/')
    ])
    projects.value = pRes.data
    tableData.value = cRes.data
  } catch(e) { console.error(e) }
  finally { loading.value = false }
}

const handleFilterChange = async () => {
  loading.value = true
  try {
    const params = filterProjectId.value ? { project_id: filterProjectId.value } : {}
    const res = await axios.get('/testcases/', { params })
    tableData.value = res.data
  } finally { loading.value = false }
}

// === 核心修改：快速运行 (使用全局环境) ===
const handleFastRun = async (row: any) => {
  const envId = envStore.currentEnvId

  // 提示用户当前使用的环境
  const confirmMsg = envId
    ? `即将使用【全局环境 (ID:${envId})】运行该用例，确定吗？`
    : `当前未选择环境，将以【默认配置】运行，确定吗？`

  try {
    // 简单确认，避免误点
    await ElMessageBox.confirm(confirmMsg, '运行确认', {
      confirmButtonText: '运行',
      cancelButtonText: '取消',
      type: 'info'
    })

    const params = envId ? { env_id: envId } : {}
    const res = await axios.post(`/testcases/${row.id}/run`, null, { params })

    ElMessage.success('任务已提交')
    // 跳转到新的报告路由
    router.push(`/report-view/${res.data.id}`)
  } catch (e) {
    // 用户取消或报错
  }
}

const handleCreate = () => router.push('/testcases/create')
const handleEdit = (id: number) => router.push(`/testcases/edit/${id}`)
const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/testcases/${id}`)
    ElMessage.success('已删除')
    init()
  } catch(e) {
    ElMessage.error('删除失败')
  }
}

onMounted(init)
</script>

<style scoped>
.test-case-list { padding: 20px; }
.header-actions { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;}
.filter-box { display: flex; gap: 10px; }
.mr-1 { margin-right: 5px; }
</style>
