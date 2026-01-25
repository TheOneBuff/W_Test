<template>
  <div class="llm-container">
    <div class="active-models-section">
      <div class="section-title">LLM 配置状态</div>
      <div class="status-grid">
        <div class="status-card chat">
          <div class="card-icon"><el-icon><ChatDotRound /></el-icon></div>
          <div class="card-info">
            <div class="label">文本/检索模型</div>
            <div class="value">{{ activeModels.chat?.name || '未配置' }}</div>
            <div class="sub-info">
              <span class="model-tag">{{ activeModels.chat?.model_name || '-' }}</span>
            </div>
          </div>
        </div>

        <div class="status-card gen">
          <div class="card-icon"><el-icon><MagicStick /></el-icon></div>
          <div class="card-info">
            <div class="label">生成用例模型</div>
            <div class="value">{{ activeModels.gen?.name || '未配置' }}</div>
            <div class="sub-info">
              <span class="model-tag">{{ activeModels.gen?.model_name || '-' }}</span>
              <el-tag v-if="activeModels.gen?.model_type === 'multimodal'" size="small" type="warning" effect="dark" style="transform: scale(0.8);">多模态</el-tag>
            </div>
          </div>
        </div>

        <div class="status-card exec">
          <div class="card-icon"><el-icon><VideoPlay /></el-icon></div>
          <div class="card-info">
            <div class="label">执行用例模型</div>
            <div class="value">{{ activeModels.exec?.name || '未配置' }}</div>
            <div class="sub-info">
              <span class="model-tag">{{ activeModels.exec?.model_name || '-' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="config-section modern-card">
      <div class="table-header">
        <h3>模型资源池</h3>
        <el-button type="primary" :icon="Plus" @click="openDialog()">添加模型</el-button>
      </div>

      <el-table :data="llmList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="配置名称" width="160" show-overflow-tooltip />

        <el-table-column prop="provider" label="供应商" width="100">
          <template #default="{ row }">
            <el-tag :type="getProviderType(row.provider)" effect="plain">{{ row.provider }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="model_type" label="能力类型" width="135" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.model_type === 'multimodal'"
              type="warning"
              size="small"
              effect="plain"
              style="width: 100%; justify-content: center; border: 1px solid #f3d19e;"
            >
              <div style="display: flex; align-items: center; gap: 4px;">
                <el-icon><Picture /></el-icon>
                <span>多模态</span>
              </div>
            </el-tag>

            <el-tag
              v-else
              type="info"
              size="small"
              effect="plain"
              style="width: 100%; justify-content: center;"
            >
              <div style="display: flex; align-items: center; gap: 4px;">
                <el-icon><Document /></el-icon>
                <span>纯文本</span>
              </div>
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="model_name" label="模型 ID" min-width="140" show-overflow-tooltip />

        <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip>
          <template #default="{ row }">
             <span style="color: #909399; font-size: 12px;">{{ row.base_url || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="应用场景激活" width="280" align="center">
          <template #default="{ row }">
            <div class="switch-group">
              <el-tooltip content="激活为：文本/检索模型 (RAG)" placement="top">
                <div
                  class="role-btn"
                  :class="{ active: row.is_active_chat }"
                  @click="activateModel(row, 'chat')"
                >
                  <el-icon><ChatDotRound /></el-icon> RAG
                </div>
              </el-tooltip>

              <el-tooltip content="激活为：用例生成模型" placement="top">
                <div
                  class="role-btn"
                  :class="{ active: row.is_active_gen }"
                  @click="activateModel(row, 'gen')"
                >
                  <el-icon><MagicStick /></el-icon> 生成
                </div>
              </el-tooltip>

              <el-tooltip content="激活为：自动化执行模型" placement="top">
                <div
                  class="role-btn"
                  :class="{ active: row.is_active_exec }"
                  @click="activateModel(row, 'exec')"
                >
                  <el-icon><VideoPlay /></el-icon> 执行
                </div>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑模型' : '添加模型'" width="600px" align-center>
      <el-form :model="form" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="配置名称 (Alias)" required>
              <el-input v-model="form.name" placeholder="例如: Qwen-VL-Max" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商" required>
               <el-select v-model="form.provider" style="width:100%">
                 <el-option label="OpenAI" value="openai" />
                 <el-option label="Ollama" value="ollama" />
                 <el-option label="DeepSeek" value="deepseek" />
                 <el-option label="Anthropic" value="anthropic" />
                 <el-option label="Azure" value="azure_openai" />
               </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="模型能力类型" required>
          <el-radio-group v-model="form.model_type">
            <el-radio label="text" border>
              <div style="display:flex;align-items:center;gap:4px">
                <el-icon><Document /></el-icon> 纯文本 (Text Only)
              </div>
            </el-radio>
            <el-radio label="multimodal" border>
              <div style="display:flex;align-items:center;gap:4px;color:#e6a23c">
                <el-icon><Picture /></el-icon> 多模态 (Vision/Image)
              </div>
            </el-radio>
          </el-radio-group>
          <div class="form-tip">
            * 多模态模型支持图片理解，可用于由图生成测试用例。
          </div>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="14">
            <el-form-item label="模型 ID (Model Name)" required>
              <el-input v-model="form.model_name" placeholder="例如: qwen-vl-max 或 gpt-4-vision" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="模型家族 (Family)">
              <el-input v-model="form.model_family" placeholder="可选, 如: qwen" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Base URL (API 代理地址)">
          <el-input v-model="form.base_url" placeholder="例如: http://localhost:11434/v1" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="如不修改请留空"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="form.memo" type="textarea" :rows="2" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, ChatDotRound, MagicStick, VideoPlay,
  Picture, Document // [新增] 引入图标
} from '@element-plus/icons-vue'

// [修改] 接口定义，增加 model_type
interface LLMConfig {
  id: number
  name: string
  provider: string
  model_name: string
  model_type: string // 'text' | 'multimodal'
  model_family?: string
  base_url?: string
  api_key?: string
  memo?: string
  is_active_chat: boolean
  is_active_gen: boolean
  is_active_exec: boolean
}

const llmList = ref<LLMConfig[]>([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)

// [修改] 表单对象，增加 model_type
const form = reactive({
  id: null as number | null,
  name: '',
  provider: 'openai',
  model_name: '',
  model_type: 'text', // 默认纯文本
  model_family: '',
  base_url: '',
  api_key: '',
  memo: ''
})

const activeModels = computed(() => {
  return {
    chat: llmList.value.find(i => i.is_active_chat),
    gen: llmList.value.find(i => i.is_active_gen),
    exec: llmList.value.find(i => i.is_active_exec)
  }
})

const fetchList = async () => {
  loading.value = true
  try {
    const res = await axios.get('/llm/')
    llmList.value = res.data
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const activateModel = async (row: LLMConfig, purpose: 'chat'|'gen'|'exec') => {
  try {
    const oldActive = llmList.value.find(i => i[`is_active_${purpose}`])
    if (oldActive) oldActive[`is_active_${purpose}`] = false
    row[`is_active_${purpose}`] = true

    await axios.post(`/llm/${row.id}/activate`, null, { params: { purpose } })
    ElMessage.success('设置成功')
  } catch (e) {
    ElMessage.error('设置失败')
    fetchList()
  }
}

const getProviderType = (p: string) => {
  if (p === 'openai') return 'success'
  if (p === 'ollama') return 'warning'
  if (p === 'deepseek') return 'primary'
  return 'info'
}

const openDialog = (row?: LLMConfig) => {
  if (row) {
    form.id = row.id
    form.name = row.name
    form.provider = row.provider
    form.model_name = row.model_name
    form.model_type = row.model_type || 'text' // [新增] 回显逻辑
    form.model_family = row.model_family || ''
    form.base_url = row.base_url || ''
    form.api_key = ''
    form.memo = row.memo || ''
  } else {
    form.id = null
    form.name = ''
    form.provider = 'openai'
    form.model_name = ''
    form.model_type = 'text' // [新增] 默认值
    form.model_family = ''
    form.base_url = ''
    form.api_key = ''
    form.memo = ''
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.name || !form.model_name) return ElMessage.warning('请填写必填项')

  submitting.value = true
  try {
    if (form.id) {
        await axios.put(`/llm/${form.id}`, form)
    } else {
        await axios.post('/llm/', form)
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

const handleDelete = (row: LLMConfig) => {
  ElMessageBox.confirm('确定删除该配置吗？', '警告', { type: 'warning' }).then(async () => {
    await axios.delete(`/llm/${row.id}`)
    ElMessage.success('删除成功')
    fetchList()
  })
}

onMounted(fetchList)
</script>

<style scoped>
.llm-container { max-width: 1200px; margin: 0 auto; padding-bottom: 40px; }

/* 顶部卡片 */
.active-models-section { margin-bottom: 24px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #374151; }
.status-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }

.status-card {
  background: #fff; border-radius: 10px; padding: 18px;
  display: flex; align-items: center;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  position: relative; overflow: hidden;
  transition: transform 0.2s;
}
.status-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.status-card::after { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }

.status-card.chat::after { background: #3b82f6; }
.status-card.gen::after { background: #8b5cf6; }
.status-card.exec::after { background: #10b981; }

.card-icon {
  width: 42px; height: 42px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; margin-right: 14px; flex-shrink: 0;
}
.chat .card-icon { background: #eff6ff; color: #3b82f6; }
.gen .card-icon { background: #f5f3ff; color: #8b5cf6; }
.exec .card-icon { background: #ecfdf5; color: #10b981; }

.card-info { flex: 1; overflow: hidden; }
.card-info .label { font-size: 12px; color: #6b7280; margin-bottom: 2px; }
.card-info .value { font-size: 15px; font-weight: 700; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-info { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.card-info .model-tag { font-size: 11px; color: #9ca3af; font-family: monospace; }

/* 表格区 */
.config-section { background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #f3f4f6; }
.table-header { display: flex; justify-content: space-between; margin-bottom: 16px; align-items: center; }

/* 切换按钮 */
.switch-group { display: flex; gap: 6px; justify-content: center; }
.role-btn {
  padding: 4px 10px; border-radius: 6px; font-size: 11px;
  cursor: pointer; display: flex; align-items: center; gap: 4px;
  background: #f9fafb; color: #6b7280; transition: all 0.2s;
  border: 1px solid #e5e7eb;
}
.role-btn:hover { background: #f3f4f6; }

.role-btn.active { font-weight: 600; border-color: transparent; }
.role-btn.active:nth-child(1) { background: #eff6ff; color: #3b82f6; }
.role-btn.active:nth-child(2) { background: #f5f3ff; color: #8b5cf6; }
.role-btn.active:nth-child(3) { background: #ecfdf5; color: #10b981; }

.form-tip { font-size: 12px; color: #909399; margin-top: 6px; }
</style>