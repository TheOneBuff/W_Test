<template>
  <div class="detail-container" v-loading="loading">
    <div class="header-card">
      <div class="left-section">
        <el-button link @click="router.back()">← 返回列表</el-button>
        <span class="detail-title">生成结果详情 #{{ record.id }}</span>
        <el-tag v-if="record.status" :type="record.status==='success'?'success':'danger'" class="ml-2">
          {{ record.status }}
        </el-tag>
      </div>
      <div class="right-section">
        <el-button type="success" :disabled="selectedRows.length === 0" @click="handleBatchExport">
          批量导出 Excel ({{ selectedRows.length }})
        </el-button>
        <el-button type="primary" @click="handleExportAll">
          导出全部
        </el-button>
      </div>
    </div>

    <el-collapse v-model="activeNames" class="mb-3">
      <el-collapse-item title="查看原始需求" name="1">
        <div class="req-box">
          <div class="req-text">{{ record.requirement }}</div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-card shadow="never" class="table-card">
      <el-table
        :data="testCases"
        border
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />

        <el-table-column prop="module" label="模块" width="120" show-overflow-tooltip />
        <el-table-column prop="title" label="用例标题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="precondition" label="前置条件" width="150" show-overflow-tooltip />

        <el-table-column label="测试步骤" min-width="250">
          <template #default="{ row }">
            <div class="pre-wrap">
              <template v-if="Array.isArray(row.steps)">
                <div v-for="(s, i) in row.steps" :key="i">{{ s }}</div>
              </template>
              <template v-else>{{ row.steps }}</template>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="预期结果" min-width="250">
          <template #default="{ row }">
            <div class="pre-wrap">
              <template v-if="Array.isArray(row.expected)">
                <div v-for="(e, i) in row.expected" :key="i">{{ e }}</div>
              </template>
              <template v-else>{{ row.expected }}</template>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="priority" label="优先级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.priority==='P0'?'danger':'warning'">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleSingleExport(row)">导出</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const activeNames = ref(['1'])
const record = ref<any>({})
const testCases = ref<any[]>([])
const selectedRows = ref([])

// 1. 加载详情
const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/knowledge/records/${route.params.id}`)
    record.value = res.data
    testCases.value = res.data.result_json || []
  } catch (e) {
    ElMessage.error('获取记录详情失败')
  } finally {
    loading.value = false
  }
}

// 2. 导出逻辑
const handleSelectionChange = (val: any) => selectedRows.value = val

const exportData = async (dataList: any[]) => {
  try {
    const res = await axios.post('/knowledge/export', dataList, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Result_${record.value.id}_${Date.now()}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const handleExportAll = () => exportData(testCases.value)
const handleBatchExport = () => exportData(selectedRows.value)
const handleSingleExport = (row: any) => exportData([row])

onMounted(fetchDetail)
</script>

<style scoped>
.detail-container { padding: 20px; max-width: 1200px; margin: 0 auto; min-height: 100vh; background: #f5f7fa; }
.header-card {
  background: #fff; padding: 15px 20px; border-radius: 8px; margin-bottom: 15px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.detail-title { font-size: 18px; font-weight: bold; margin-left: 10px; color: #333; }
.ml-2 { margin-left: 8px; }
.req-box { padding: 15px; background: #fff; border-radius: 4px; color: #555; line-height: 1.6; white-space: pre-wrap; }
.table-card { border: none; border-radius: 8px; }
.pre-wrap { white-space: pre-wrap; font-family: monospace; }
</style>