<template>
  <div class="scheduled-tasks">
    <div class="header-actions">
      <el-button type="primary" @click="openDialog()">
        <el-icon class="mr-1"><Plus /></el-icon> 新建定时任务
      </el-button>
    </div>

    <!-- 任务列表 -->
    <el-card shadow="never">
      <el-table :data="taskList" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="任务名称" width="200" />
        <el-table-column prop="cron_expr" label="Cron 表达式" width="150">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.cron_expr }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="执行范围" width="120">
          <template #default="{ row }">
            <el-tag :type="row.target_type === 'project' ? 'success' : 'warning'">
              {{ row.target_type === 'project' ? '按项目' : '指定用例' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联对象" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.target_type === 'project'">
              {{ getProjectName(row.project_id) }}
            </span>
            <span v-else>
              包含 {{ row.case_ids ? row.case_ids.split(',').length : 0 }} 个用例
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="上次执行时间">
          <template #default="{ row }">
            {{ formatDate(row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              @change="(val: any) => handleToggle(row, val)"
              :loading="row._switching"
            />
          </template>
        </el-table-column>
        </el-table-column>

        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" @click="openLogs(row)">日志</el-button>
            <el-button type="success" link @click="handleRunNow(row)" :loading="row._running">立即运行</el-button>

            <el-popconfirm title="确定删除该任务吗?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑/新建弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑任务' : '新建定时任务'" width="650px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="例如：每日回归测试" />
        </el-form-item>

        <el-form-item label="Cron 表达式" required>
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="14">
              <el-input v-model="form.cron_expr" placeholder="分 时 日 月 周 (空格分隔)" />
            </el-col>
            <el-col :span="10">
              <el-select v-model="quickCron" placeholder="快捷模板" @change="handleCronChange">
                <el-option label="每小时 (0 * * * *)" value="0 * * * *" />
                <el-option label="每天凌晨2点 (0 2 * * *)" value="0 2 * * *" />
                <el-option label="每周一早8点 (0 8 * * 1)" value="0 8 * * 1" />
                <el-option label="每5分钟 (*/5 * * * *)" value="*/5 * * * *" />
              </el-select>
            </el-col>
          </el-row>
          <div class="tip">格式：Minute Hour Day Month Week</div>
        </el-form-item>

        <el-form-item label="运行环境">
          <el-select v-model="form.env_id" placeholder="选择环境" clearable style="width: 100%">
            <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">执行范围</el-divider>

        <el-form-item label="选择方式">
          <el-radio-group v-model="form.target_type">
            <el-radio-button label="project">按项目 (所有用例)</el-radio-button>
            <el-radio-button label="cases">手动选择用例</el-radio-button>
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
            :titles="['可选', '已选']"
            :props="{ key: 'id', label: 'name' }"
            filterable
            filter-placeholder="搜索用例"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 日志弹窗 -->
    <el-dialog v-model="logDialogVisible" title="执行历史日志" width="700px">
      <el-table :data="logList" border stripe max-height="400">
        <el-table-column prop="trigger_time" label="触发时间" width="160">
          <template #default="{row}">{{ formatDate(row.trigger_time) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="row.status === 'success' ? 'success' : (row.status === 'running' ? 'warning' : 'danger')">
              {{ row.status.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成报告">
          <template #default="{row}">
            <div v-if="row.report_ids && row.report_ids !== '[]'">
              <el-link
                v-for="rid in tryParse(row.report_ids)"
                :key="rid"
                type="primary"
                class="mr-2"
                @click="viewReport(rid)"
              >
                #{{ rid }}
              </el-link>
            </div>
            <span v-else-if="row.status === 'failed'" style="color: red; font-size: 12px;">
              {{ row.error_msg }}
            </span>
            <span v-else>-</span>
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
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const taskList = ref<any[]>([])
const projectList = ref<any[]>([])
const envList = ref<any[]>([])
const allCases = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)

// 日志相关
const logDialogVisible = ref(false)
const logList = ref<any[]>([])

const form = reactive({
  id: null,
  name: '',
  cron_expr: '',
  target_type: 'project',
  project_id: null as number | null,
  case_ids: '',
  env_id: null as number | null,
  is_enabled: true
})

const quickCron = ref('')
const selectedCases = ref<number[]>([])

const init = async () => {
  loading.value = true
  try {
    const [taskRes, projRes, envRes, caseRes] = await Promise.all([
      axios.get('/periodic/'),
      axios.get('/projects/'),
      axios.get('/envs/'),
      axios.get('/testcases/')
    ])
    taskList.value = taskRes.data
    projectList.value = projRes.data
    envList.value = envRes.data
    allCases.value = caseRes.data
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const getProjectName = (pid: number) => {
  const p = projectList.value.find(i => i.id === pid)
  return p ? p.name : `Project #${pid}`
}

const formatDate = (str: string) => str ? dayjs(str).format('YYYY-MM-DD HH:mm:ss') : '-'

// 修改 openDialog 接收参数
const openDialog = (row?: any) => {
  if (row) {
    // 编辑模式：回显数据
    form.id = row.id
    form.name = row.name
    form.cron_expr = row.cron_expr
    form.target_type = row.target_type
    form.project_id = row.project_id
    form.env_id = row.env_id
    form.is_enabled = row.is_enabled

    // 回显用例列表
    if (row.case_ids) {
      selectedCases.value = row.case_ids.split(',').map((id: string) => Number(id))
    } else {
      selectedCases.value = []
    }
  } else {
    // 新建模式：重置
    form.id = null
    form.name = ''
    form.cron_expr = ''
    form.target_type = 'project'
    form.project_id = null
    form.env_id = null
    form.is_enabled = true
    selectedCases.value = []
  }

  quickCron.value = ''
  dialogVisible.value = true
}


const handleCronChange = (val: string) => {
  form.cron_expr = val
}

const handleSubmit = async () => {
  if (!form.name || !form.cron_expr) return ElMessage.warning('请填写完整')

  if (form.target_type === 'cases') {
    if (selectedCases.value.length === 0) return ElMessage.warning('请至少选择一个用例')
    form.case_ids = selectedCases.value.join(',')
    form.project_id = null
  } else {
    if (!form.project_id) return ElMessage.warning('请选择项目')
    form.case_ids = ''
  }

  submitting.value = true
  try {
    if (form.id) {
      // 编辑：PUT
      await axios.put(`/periodic/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      // 新建：POST
      await axios.post('/periodic/', form)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    init()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/periodic/${id}`)
    ElMessage.success('已删除')
    init()
  } catch(e) { ElMessage.error('删除失败') }
}

const handleToggle = async (row: any, val: boolean) => {
  row._switching = true
  try {
    // 复用 PUT 接口，只更新 is_enabled 字段
    // 注意：PUT 要求全量字段，所以最好把 row 的其他字段也带上，或者后端支持 PATCH
    // 为了简单且安全，我们构造一个完整的 payload
    const payload = {
      name: row.name,
      cron_expr: row.cron_expr,
      target_type: row.target_type,
      project_id: row.project_id,
      case_ids: row.case_ids,
      env_id: row.env_id,
      is_enabled: val // 只有这个变了
    }

    await axios.put(`/periodic/${row.id}`, payload)
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (e: any) {
    row.is_enabled = !val // 失败回滚开关状态
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    row._switching = false
  }
}


const handleRunNow = async (row: any) => {
  row._running = true
  try {
    await axios.post(`/periodic/${row.id}/run`)
    ElMessage.success('已触发，请查看日志')
  } catch(e) {
    ElMessage.error('触发失败')
  } finally {
    row._running = false
  }
}

// --- 日志逻辑 ---
const openLogs = async (row: any) => {
  logDialogVisible.value = true
  logList.value = [] // clear
  try {
    const res = await axios.get(`/periodic/${row.id}/logs`)
    logList.value = res.data
  } catch(e) {
    console.error(e)
  }
}

const viewReport = (id: number) => {
  const { href } = router.resolve({ path: `/report-view/${id}` })
  window.open(href, '_blank')
}

const tryParse = (str: string) => {
  try { return JSON.parse(str) } catch { return [] }
}

onMounted(init)
</script>

<style scoped>
.scheduled-tasks { padding: 20px; }
.header-actions { margin-bottom: 20px; }
.tip { font-size: 12px; color: #999; margin-top: 5px; }
.mr-1 { margin-right: 5px; }
.mr-2 { margin-right: 10px; }
</style>
