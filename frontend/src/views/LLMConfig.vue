<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">模型服务配置</div>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新增配置</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" v-for="item in list" :key="item.id">
        <el-card
          class="config-card"
          :class="{ 'active-card': item.is_active }"
          shadow="hover"
          :body-style="{ padding: '20px' }"
        >
          <div class="card-top">
            <div class="provider-icon" :class="item.provider">
              {{ item.provider.charAt(0).toUpperCase() }}
            </div>
            <div class="config-info">
              <div class="config-name">{{ item.name }}</div>
              <div class="model-tag">{{ item.model_name }}</div>
            </div>
            <div class="status-badge" v-if="item.is_active">
              <el-icon><Check /></el-icon> Active
            </div>
          </div>

          <div class="card-detail">
            <div class="detail-item">
              <span class="label">Base URL:</span>
              <span class="val">{{ item.base_url || 'Default' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">备注:</span>
              <span class="val">{{ item.memo || '-' }}</span>
            </div>
          </div>

          <div class="card-actions">
            <el-button
              v-if="!item.is_active"
              size="small"
              type="success"
              plain
              @click="handleActivate(item)"
            >
              启用
            </el-button>
            <div class="right-btns">
              <el-button size="small" :icon="Edit" circle @click="openDialog(item)" />
              <el-popconfirm title="确定删除?" @confirm="handleDelete(item.id)">
                <template #reference>
                  <el-button size="small" type="danger" :icon="Delete" circle plain />
                </template>
              </el-popconfirm>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="list.length === 0" description="暂无模型配置" />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑配置' : '新增配置'" width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px" class="pt-2">
        <el-form-item label="配置名称" required>
          <el-input v-model="form.name" placeholder="例如: 个人OpenAI" />
        </el-form-item>
        <el-form-item label="提供商" required>
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Qwen (通义千问)" value="qwen" />
            <el-option label="Custom (自定义)" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" required>
          <el-input v-model="form.model_name" placeholder="例如: gpt-4o" />
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key_masked" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="可选，默认官方地址" />
        </el-form-item>
        <el-form-item label="Model Family">
          <el-input v-model="form.model_family" placeholder="可选，例如: qwen" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.memo" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus, Check, Edit, Delete } from '@element-plus/icons-vue'

const list = ref<any[]>([])
const dialogVisible = ref(false)
const form = reactive({
  id: null, name: '', provider: 'openai', model_name: 'gpt-4o',
  api_key_masked: '', base_url: '', model_family: '', memo: '', is_active: false
})

const fetchList = async () => {
  const res = await axios.get('/llm/')
  list.value = res.data
}

const openDialog = (row?: any) => {
  if (row) Object.assign(form, row)
  else {
    Object.assign(form, { id: null, name: 'New Config', provider: 'openai', model_name: 'gpt-4o', api_key_masked: '', base_url: '', memo: '' })
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const payload = { ...form, api_key: form.api_key_masked }
  try {
    if (form.id) await axios.put(`/llm/${form.id}`, payload)
    else await axios.post('/llm/', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleActivate = async (row: any) => {
  await axios.post(`/llm/${row.id}/activate`)
  ElMessage.success('已切换为当前配置')
  fetchList()
}

const handleDelete = async (id: number) => {
  await axios.delete(`/llm/${id}`)
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; padding-top: 20px; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 12px; margin-bottom: 24px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.title { font-size: 16px; font-weight: 600; color: #1f2937; }

.config-card {
  border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  margin-bottom: 24px; position: relative; overflow: hidden; transition: all 0.3s;
}
.config-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }

.active-card { border: 2px solid #10b981; background: #ecfdf5; }
.active-card .status-badge {
  position: absolute; top: 12px; right: 12px; background: #10b981; color: #fff;
  padding: 4px 8px; border-radius: 4px; font-size: 12px; display: flex; align-items: center; gap: 4px;
}

.card-top { display: flex; align-items: center; margin-bottom: 16px; }
.provider-icon {
  width: 48px; height: 48px; border-radius: 10px; background: #f3f4f6; color: #6b7280;
  display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; margin-right: 12px;
}
.provider-icon.openai { background: #10a37f; color: #fff; }
.provider-icon.qwen { background: #615ced; color: #fff; }

.config-info { flex: 1; }
.config-name { font-weight: 600; font-size: 16px; color: #1f2937; }
.model-tag { font-size: 12px; color: #6b7280; background: rgba(0,0,0,0.05); display: inline-block; padding: 2px 6px; border-radius: 4px; margin-top: 4px; }

.card-detail { font-size: 13px; color: #4b5563; margin-bottom: 16px; }
.detail-item { margin-bottom: 6px; display: flex; }
.detail-item .label { color: #9ca3af; width: 70px; }
.detail-item .val { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; }

.card-actions { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 12px; }
.right-btns { margin-left: auto; }
</style>