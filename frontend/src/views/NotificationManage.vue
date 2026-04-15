<template>
  <div class="notification-container">
    <div class="config-section modern-card">
      <div class="table-header">
        <h3>通知渠道配置</h3>
        <el-button type="primary" :icon="Plus" @click="openDialog()">添加通知渠道</el-button>
      </div>

      <el-table :data="notificationList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="配置名称" width="160" show-overflow-tooltip />
        
        <el-table-column prop="channel" label="渠道类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getChannelType(row.channel)" effect="plain">{{ getChannelLabel(row.channel) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_enabled" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_default" label="默认" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="warning" size="small">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="events" label="触发事件" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="evt in (row.events || [])" :key="evt" size="small" type="info" style="margin-right: 4px;">
              {{ evt }}
            </el-tag>
            <span v-if="!row.events?.length" class="text-gray">未配置</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleTest(row)">测试</el-button>
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑通知渠道' : '添加通知渠道'" width="600px" align-center>
      <el-form :model="form" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="配置名称" required>
              <el-input v-model="form.name" placeholder="例如: 飞书测试群" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通知渠道" required>
              <el-select v-model="form.channel" style="width:100%" @change="handleChannelChange">
                <el-option label="飞书群机器人" value="feishu" />
                <el-option label="企业微信机器人" value="weixin" />
                <el-option label="邮件" value="email" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="渠道配置">
          <div v-if="form.channel === 'feishu' || form.channel === 'weixin'">
            <el-input v-model="form.configJson.webhook_url" placeholder="Webhook 地址" />
            <div class="form-tip">在飞书/企业微信创建机器人获取 Webhook 地址</div>
          </div>
          <div v-else-if="form.channel === 'email'">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-input v-model="form.configJson.smtp_host" placeholder="SMTP 服务器" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="form.configJson.smtp_port" placeholder="端口" type="number" />
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 12px;">
              <el-col :span="12">
                <el-input v-model="form.configJson.username" placeholder="用户名" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="form.configJson.password" placeholder="密码" type="password" show-password />
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 12px;">
              <el-col :span="12">
                <el-input v-model="form.configJson.from_addr" placeholder="发件人地址" />
              </el-col>
              <el-col :span="12">
                <el-input v-model="form.configJson.to_addrs" placeholder="收件人地址(逗号分隔)" />
              </el-col>
            </el-row>
          </div>
          <div v-else class="form-tip">请选择通知渠道</div>
        </el-form-item>

        <el-form-item label="触发事件">
          <el-checkbox-group v-model="form.events">
            <el-checkbox label="task_success">任务成功</el-checkbox>
            <el-checkbox label="task_failed">任务失败</el-checkbox>
            <el-checkbox label="task_created">任务创建</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="其他设置">
          <el-checkbox v-model="form.is_enabled">启用此渠道</el-checkbox>
          <el-checkbox v-model="form.is_default" style="margin-left: 20px;">设为默认渠道</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

interface NotificationConfig {
  id: number
  name: string
  channel: string
  is_enabled: boolean
  is_default: boolean
  config_json: any
  events: string[]
}

interface ConfigJson {
  webhook_url: string
  smtp_host: string
  smtp_port: number
  username: string
  password: string
  from_addr: string
  to_addrs: string | string[]
}

const notificationList = ref<NotificationConfig[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)

const form = reactive({
  id: null as number | null,
  name: '',
  channel: 'feishu',
  is_enabled: true,
  is_default: false,
  events: [] as string[],
  configJson: {
    webhook_url: '',
    smtp_host: 'smtp.qq.com',
    smtp_port: 587,
    username: '',
    password: '',
    from_addr: '',
    to_addrs: ''
  }
})

const getChannelLabel = (channel: string) => {
  const map: Record<string, string> = {
    feishu: '飞书',
    weixin: '企业微信',
    email: '邮件'
  }
  return map[channel] || channel
}

const getChannelType = (channel: string) => {
  const map: Record<string, string> = {
    feishu: 'warning',
    weixin: 'success',
    email: 'primary'
  }
  return map[channel] || 'info'
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('/notification/')
    notificationList.value = res.data
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleChannelChange = () => {
  form.configJson = {
    webhook_url: '',
    smtp_host: 'smtp.qq.com',
    smtp_port: 587,
    username: '',
    password: '',
    from_addr: '',
    to_addrs: ''
  }
}

const openDialog = (row?: NotificationConfig) => {
  if (row) {
    form.id = row.id
    form.name = row.name
    form.channel = row.channel
    form.is_enabled = row.is_enabled
    form.is_default = row.is_default
    form.events = row.events || []
    form.configJson = row.config_json || {
      webhook_url: '',
      smtp_host: 'smtp.qq.com',
      smtp_port: 587,
      username: '',
      password: '',
      from_addr: '',
      to_addrs: ''
    }
  } else {
    form.id = null
    form.name = ''
    form.channel = 'feishu'
    form.is_enabled = true
    form.is_default = false
    form.events = []
    form.configJson = {
      webhook_url: '',
      smtp_host: 'smtp.qq.com',
      smtp_port: 587,
      username: '',
      password: '',
      from_addr: '',
      to_addrs: ''
    }
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.name) return ElMessage.warning('请填写配置名称')

  const configJson: ConfigJson = { ...form.configJson }
  if (form.channel === 'email' && typeof configJson.to_addrs === 'string') {
    configJson.to_addrs = configJson.to_addrs.split(',').map((s: string) => s.trim()).filter((s: string) => s !== '')
  }

  const data = {
    name: form.name,
    channel: form.channel,
    is_enabled: form.is_enabled,
    is_default: form.is_default,
    events: form.events,
    config_json: configJson
  }

  submitting.value = true
  try {
    if (form.id) {
      await axios.put(`/notification/${form.id}`, data)
    } else {
      await axios.post('/notification/', data)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
  } catch(e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row: NotificationConfig) => {
  ElMessageBox.confirm('确定删除该通知配置吗？', '警告', { type: 'warning' }).then(async () => {
    await axios.delete(`/notification/${row.id}`)
    ElMessage.success('删除成功')
    fetchList()
  })
}

const handleTest = async (row: NotificationConfig) => {
  try {
    const res = await axios.post('/notification/test', {
      config_id: row.id,
      test_message: '这是一条测试通知消息'
    })
    if (res.data.success) {
      ElMessage.success('测试消息发送成功')
    } else {
      ElMessage.warning(res.data.message || '发送失败')
    }
  } catch(e: any) {
    ElMessage.error(e.response?.data?.detail || '测试失败')
  }
}

onMounted(fetchList)
</script>

<style scoped>
.notification-container { max-width: 1200px; margin: 0 auto; padding-bottom: 40px; }

.config-section { background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #f3f4f6; }
.table-header { display: flex; justify-content: space-between; margin-bottom: 16px; align-items: center; }

.form-tip { font-size: 12px; color: #909399; margin-top: 6px; }
.text-gray { color: #909399; font-size: 12px; }
</style>