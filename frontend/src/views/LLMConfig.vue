<template>
  <div class="llm-container">
    <div class="active-models-section">
      <div class="section-title">LLM配置</div>
      <div class="status-grid">
        <div class="status-card chat">
          <div class="card-icon"><el-icon><ChatDotRound /></el-icon></div>
          <div class="card-info">
            <div class="label">文本模型</div>
            <div class="value">{{ activeModels.chat?.name || '未配置' }}</div>
            <div class="model-tag">{{ activeModels.chat?.model_name || '-' }}</div>
          </div>
        </div>

        <div class="status-card gen">
          <div class="card-icon"><el-icon><MagicStick /></el-icon></div>
          <div class="card-info">
            <div class="label">生成用例模型</div>
            <div class="value">{{ activeModels.gen?.name || '未配置' }}</div>
            <div class="model-tag">{{ activeModels.gen?.model_name || '-' }}</div>
          </div>
        </div>

        <div class="status-card exec">
          <div class="card-icon"><el-icon><VideoPlay /></el-icon></div>
          <div class="card-info">
            <div class="label">执行用例模型</div>
            <div class="value">{{ activeModels.exec?.name || '未配置' }}</div>
            <div class="model-tag">{{ activeModels.exec?.model_name || '-' }}</div>
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
        <el-table-column prop="name" label="配置名称" width="180" show-overflow-tooltip />
        <el-table-column prop="provider" label="供应商" width="120">
          <template #default="{ row }">
            <el-tag :type="getProviderType(row.provider)">{{ row.provider }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型名称" min-width="140" show-overflow-tooltip />
        
        <el-table-column prop="model_family" label="模型家族" width="120" show-overflow-tooltip>
           <template #default="{ row }">
             <span v-if="row.model_family" class="family-tag">{{ row.model_family }}</span>
             <span v-else style="color: #d1d5db">-</span>
           </template>
        </el-table-column>

        <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip />

        <el-table-column label="应用场景设置" width="300" align="center">
          <template #default="{ row }">
            <div class="switch-group">
              <el-tooltip content="设为文本模型 (用于知识库RAG)" placement="top">
                <div
                  class="role-btn"
                  :class="{ active: row.is_active_chat }"
                  @click="activateModel(row, 'chat')"
                >
                  <el-icon><ChatDotRound /></el-icon> 文本
                </div>
              </el-tooltip>

              <el-tooltip content="设为生成模型" placement="top">
                <div
                  class="role-btn"
                  :class="{ active: row.is_active_gen }"
                  @click="activateModel(row, 'gen')"
                >
                  <el-icon><MagicStick /></el-icon> 生成
                </div>
              </el-tooltip>

              <el-tooltip content="设为执行模型" placement="top">
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

        <el-table-column label="操作" width="150" align="right">
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
            <el-form-item label="配置名称" required>
              <el-input v-model="form.name" placeholder="例如: DeepSeek-V3" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商" required>
               <el-select v-model="form.provider" style="width:100%" placeholder="选择厂商">
                 <el-option label="OpenAI" value="openai" />
                 <el-option label="Ollama" value="ollama" />
                 <el-option label="DeepSeek" value="deepseek" />
                 <el-option label="Anthropic" value="anthropic" />
                 <el-option label="Azure" value="azure_openai" />
               </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="模型代码 (Model ID)" required>
              <el-input v-model="form.model_name" placeholder="例如: deepseek-chat" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型家族 (Family)">
              <el-input v-model="form.model_family" placeholder="例如: qwen, gpt, llama" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Base URL (可选)">
          <el-input v-model="form.base_url" placeholder="例如: https://api.deepseek.com" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="留空则不修改 (仅编辑时)"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="form.memo"
            type="textarea"
            :rows="2"
            placeholder="可选备注信息..."
          />
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
import { Plus, ChatDotRound, MagicStick, VideoPlay } from '@element-plus/icons-vue'

// 定义接口以获得更好的类型提示
interface LLMConfig {
  id: number
  name: string
  provider: string
  model_name: string
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

const form = reactive({
  id: null as number | null,
  name: '',
  provider: 'openai',
  model_name: '',
  model_family: '',
  base_url: '',
  api_key: '',
  memo: ''
})

// 计算属性：快速获取当前生效的三个模型
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

// 激活模型的核心逻辑
const activateModel = async (row: LLMConfig, purpose: 'chat'|'gen'|'exec') => {
  try {
    // 乐观更新 UI
    const oldActive = llmList.value.find(i => i[`is_active_${purpose}`])
    if (oldActive) oldActive[`is_active_${purpose}`] = false
    row[`is_active_${purpose}`] = true

    await axios.post(`/llm/${row.id}/activate`, null, { params: { purpose } })
    ElMessage.success('设置成功')
  } catch (e) {
    ElMessage.error('设置失败')
    fetchList() // 失败回滚
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
    // 编辑模式：回显数据
    form.id = row.id
    form.name = row.name
    form.provider = row.provider
    form.model_name = row.model_name
    form.model_family = row.model_family || ''
    form.base_url = row.base_url || ''
    form.api_key = ''
    form.memo = row.memo || ''
  } else {
    // 新增模式：重置表单
    form.id = null
    form.name = ''
    form.provider = 'openai'
    form.model_name = ''
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

/* 顶部卡片区 */
.active-models-section { margin-bottom: 32px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #374151; }
.status-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }

.status-card {
  background: #fff; border-radius: 12px; padding: 20px;
  display: flex; align-items: center;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  position: relative; overflow: hidden;
}
.status-card::after { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }

.status-card.chat::after { background: #3b82f6; } /* Blue */
.status-card.gen::after { background: #8b5cf6; } /* Purple */
.status-card.exec::after { background: #10b981; } /* Green */

.card-icon {
  width: 48px; height: 48px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; margin-right: 16px;
}
.chat .card-icon { background: #eff6ff; color: #3b82f6; }
.gen .card-icon { background: #f5f3ff; color: #8b5cf6; }
.exec .card-icon { background: #ecfdf5; color: #10b981; }

.card-info .label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
.card-info .value { font-size: 16px; font-weight: 700; color: #111827; }
.card-info .model-tag { font-size: 12px; color: #9ca3af; font-family: monospace; margin-top: 2px; }

/* 底部表格区 */
.config-section { background: #fff; padding: 24px; border-radius: 12px; border: 1px solid #f3f4f6; }
.table-header { display: flex; justify-content: space-between; margin-bottom: 16px; align-items: center; }

/* 切换按钮样式 */
.switch-group { display: flex; gap: 8px; justify-content: center; }
.role-btn {
  padding: 4px 12px; border-radius: 6px; font-size: 12px;
  cursor: pointer; display: flex; align-items: center; gap: 4px;
  background: #f3f4f6; color: #6b7280; transition: all 0.2s;
  border: 1px solid transparent;
}
.role-btn:hover { background: #e5e7eb; }

/* 激活状态 */
.role-btn.active { font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.role-btn.active:nth-child(1) { background: #eff6ff; color: #3b82f6; border-color: #bfdbfe; } /* Chat (Vector) */
.role-btn.active:nth-child(2) { background: #f5f3ff; color: #8b5cf6; border-color: #ddd6fe; } /* Gen */
.role-btn.active:nth-child(3) { background: #ecfdf5; color: #10b981; border-color: #bbf7d0; } /* Exec */

.family-tag {
  background: #f0fdf4; color: #15803d; font-size: 11px;
  padding: 2px 6px; border-radius: 4px; border: 1px solid #dcfce7;
}
</style>