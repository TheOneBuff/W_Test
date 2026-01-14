<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">定时任务管理</div>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新建任务</el-button>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table :data="taskList" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" align="center" class-name="text-gray" />
        <el-table-column prop="name" label="任务名称" width="200" class-name="font-medium" />

        <el-table-column label="Cron 表达式" width="160">
          <template #default="{ row }">
            <el-tag effect="plain" type="info" class="font-mono">{{ row.cron_expr }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="执行范围" width="120">
          <template #default="{ row }">
            <el-tag :type="row.target_type === 'project' ? 'primary' : 'warning'" size="small">
              {{ row.target_type === 'project' ? '项目级' : '指定用例' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="关联对象" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.target_type === 'project'">
              <el-icon class="v-align"><Folder /></el-icon> {{ getProjectName(row.project_id) }}
            </span>
            <span v-else>
              <el-icon class="v-align"><Document /></el-icon> 包含 {{ row.case_ids ? row.case_ids.split(',').length : 0 }} 个用例
            </span>
          </template>
        </el-table-column>

        <el-table-column label="启用状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              size="small"
              @change="(val: any) => handleToggle(row, val)"
              :loading="row._switching"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="240" fixed="right" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleRunNow(row)" :loading="row._running">立即运行</el-button>
            <el-button link type="info" @click="openLogs(row)">日志</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑任务' : '新建定时任务'" width="600px" destroy-on-close>
      <el-form :model="form" label-width="100px" label-position="left">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="例如：每日核心回归" />
        </el-form-item>

        <el-form-item label="触发规则" required>
          <div class="cron-input-group">
            <el-input v-model="form.cron_expr" placeholder="* * * * *" style="width: 200px" />
            <el-select v-model="quickCron" placeholder="快速模板" style="flex: 1" @change="(v:any)=>form.cron_expr=v">
              <el-option label="每小时 (0 * * * *)" value="0 * * * *" />
              <el-option label="每天凌晨2点 (0 2 * * *)" value="0 2 * * *" />
              <el-option label="每周一 (0 8 * * 1)" value="0 8 * * 1" />
            </el-select>
          </div>
          <div class="form-tip">格式: 分 时 日 月 周</div>
        </el-form-item>

        <el-form-item label="运行环境">
          <el-select v-model="form.env_id" placeholder="默认环境" clearable style="width: 100%">
            <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">执行范围配置</el-divider>

        <el-form-item label="范围类型">
          <el-radio-group v-model="form.target_type">
            <el-radio-button label="project">整个项目</el-radio-button>
            <el-radio-button label="cases">指定用例</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选择项目" v-if="form.target_type === 'project'" required>
          <el-select v-model="form.project_id" placeholder="请选择项目" style="width: 100%">
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="选择用例" v-if="form.target_type === 'cases'">
          <el-transfer
            v-model="selectedCases"
            :data="allCases"
            :titles="['待选', '已选']"
            :props="{ key: 'id', label: 'name' }"
            filterable
            filter-placeholder="搜索..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" title="执行历史" width="750px">
      <el-table :data="logList" border stripe size="small" height="400">
        <el-table-column prop="trigger_time" label="执行时间" width="150">
          <template #default="{row}">{{ formatDate(row.trigger_time) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{row}">
             <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
               {{ row.status ? row.status.toUpperCase() : '-' }}
             </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果报告">
          <template #default="{row}">
            <div v-if="row.report_ids && row.report_ids !== '[]'" class="report-links">
              <el-tag
                v-for="rid in tryParse(row.report_ids)"
                :key="rid"
                size="small"
                class="cursor-pointer mr-1"
                @click="viewReport(rid)"
              >
                #{{ rid }}
              </el-tag>
            </div>
            <span v-else-if="row.status === 'failed'" class="error-text">{{ row.error_msg }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Folder, Document } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const taskList = ref<any[]>([])
const projectList = ref<any[]>([])
const envList = ref<any[]>([])
const allCases = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const logDialogVisible = ref(false)
const logList = ref<any[]>([])
const quickCron = ref('')
const selectedCases = ref<number[]>([])

const form = reactive({
  id: null, name: '', cron_expr: '', target_type: 'project',
  project_id: null, case_ids: '', env_id: null, is_enabled: true
})

const init = async () => {
  loading.value = true
  try {
    const [t, p, e, c] = await Promise.all([
      axios.get('/periodic/'), axios.get('/projects/'), axios.get('/envs/'), axios.get('/testcases/')
    ])
    taskList.value = t.data; projectList.value = p.data; envList.value = e.data; allCases.value = c.data
  } catch(e) { console.error(e) }
  finally { loading.value = false }
}

const getProjectName = (pid: number) => {
  const p = projectList.value.find(i => i.id === pid)
  return p ? p.name : pid
}

const openDialog = (row?: any) => {
  if (row) {
    Object.assign(form, row)
    selectedCases.value = row.case_ids ? row.case_ids.split(',').map(Number) : []
  } else {
    Object.assign(form, { id: null, name: '', cron_expr: '', target_type: 'project', project_id: null, case_ids: '', env_id: null, is_enabled: true })
    selectedCases.value = []
  }
  quickCron.value = ''
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.name || !form.cron_expr) return ElMessage.warning('请填写完整')
  if (form.target_type === 'cases') {
    if (selectedCases.value.length === 0) return ElMessage.warning('至少选择一个用例')
    form.case_ids = selectedCases.value.join(',')
    form.project_id = null
  } else {
    if (!form.project_id) return ElMessage.warning('请选择项目')
    form.case_ids = ''
  }

  submitting.value = true
  try {
    if (form.id) await axios.put(`/periodic/${form.id}`, form)
    else await axios.post('/periodic/', form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    init()
  } catch (e: any) { ElMessage.error('保存失败') }
  finally { submitting.value = false }
}

const handleDelete = async (id: number) => {
  try { await axios.delete(`/periodic/${id}`); ElMessage.success('已删除'); init() } catch(e) {}
}

const handleToggle = async (row: any, val: boolean) => {
  row._switching = true
  try {
    const payload = { ...row, is_enabled: val }
    await axios.put(`/periodic/${row.id}`, payload)
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (e) {
    row.is_enabled = !val
    ElMessage.error('操作失败')
  } finally { row._switching = false }
}

const handleRunNow = async (row: any) => {
  row._running = true
  try {
    await axios.post(`/periodic/${row.id}/run`)
    ElMessage.success('任务已触发')
  } catch(e) { ElMessage.error('触发失败') }
  finally { row._running = false }
}

const openLogs = async (row: any) => {
  logDialogVisible.value = true
  logList.value = []
  const res = await axios.get(`/periodic/${row.id}/logs`)
  logList.value = res.data
}

const viewReport = (id: number) => window.open(router.resolve(`/report-view/${id}`).href, '_blank')
const tryParse = (str: string) => { try { return JSON.parse(str) } catch { return [] } }
const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm') : '-'

onMounted(init)
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 8px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.title { font-size: 16px; font-weight: 600; color: #1f2937; }
.table-card { border: none; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); overflow: hidden; }
.font-medium { font-weight: 500; }
.font-mono { font-family: monospace; }
.text-gray { color: #9ca3af; }
.v-align { vertical-align: -2px; margin-right: 2px; }

.cron-input-group { display: flex; gap: 10px; }
.form-tip { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.error-text { color: #dc2626; font-size: 12px; }
.report-links { display: flex; flex-wrap: wrap; gap: 4px; }
</style>