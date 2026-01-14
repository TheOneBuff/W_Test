<template>
  <div class="llm-config-page">
    <div class="header-actions">
      <el-button type="primary" @click="openDialog()">
        <el-icon class="mr-1"><Plus /></el-icon> 新增配置
      </el-button>
    </div>

    <el-row :gutter="20">
      <el-col :span="8" v-for="item in list" :key="item.id">
        <el-card class="config-card" :class="{ 'active-card': item.is_active }">
          <template #header>
            <div class="card-header">
              <span class="title">{{ item.name }}</span>
              <el-tag v-if="item.is_active" type="success" effect="dark">使用中</el-tag>
              <el-button v-else size="small" @click="handleActivate(item)">启用</el-button>
            </div>
          </template>

          <div class="card-body">
            <p><strong>Provider:</strong> {{ item.provider }}</p>
            <p><strong>Model:</strong> {{ item.model_name }}</p>
            <p><strong>URL:</strong> {{ item.base_url || 'Default' }}</p>
            <p class="memo">{{ item.memo }}</p>
          </div>

          <div class="card-footer">
            <el-button link type="primary" @click="openDialog(item)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(item.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑配置' : '新增配置'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="配置名称" required>
          <el-input v-model="form.name" placeholder="例如: 个人OpenAI" />
        </el-form-item>
        <el-form-item label="提供商">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Qwen" value="qwen" />
            <el-option label="Custom" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.model_name" placeholder="gpt-4o" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key_masked" type="password" show-password />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" />
        </el-form-item>
        <el-form-item label="Family">
          <el-input v-model="form.model_family" placeholder="Optional" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.memo" type="textarea" />
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
import { Plus } from '@element-plus/icons-vue'

const list = ref<any[]>([])
const dialogVisible = ref(false)
const form = reactive({
  id: null,
  name: '',
  provider: 'openai',
  model_name: 'gpt-4o',
  api_key_masked: '',
  base_url: '',
  model_family: '',
  memo: '',
  is_active: false
})

const fetchList = async () => {
  const res = await axios.get('/llm/')
  list.value = res.data
}

const openDialog = (row?: any) => {
  if (row) {
    Object.assign(form, row)
  } else {
    form.id = null
    form.name = 'New Config'
    form.api_key_masked = ''
    // ... 其他重置
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
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const handleActivate = async (row: any) => {
  await axios.post(`/llm/${row.id}/activate`)
  ElMessage.success('已切换')
  fetchList()
}

const handleDelete = async (id: number) => {
  await axios.delete(`/llm/${id}`)
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.llm-config-page { padding: 20px; }
.active-card { border: 1px solid #67C23A; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: bold; }
.card-body p { margin: 5px 0; font-size: 13px; color: #606266; }
.card-footer { margin-top: 15px; border-top: 1px solid #eee; padding-top: 10px; text-align: right; }
</style>
