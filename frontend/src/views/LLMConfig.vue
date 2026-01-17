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
        <el-form-item label="模型用途" required>
          <el-radio-group v-model="form.use_for" @change="handleUseForChange">
            <el-radio-button label="generation">生成/测试 (Chat)</el-radio-button>
            <el-radio-button label="embedding">向量化 (Embedding)</el-radio-button>
          </el-radio-group>
          <div class="form-tip" v-if="form.use_for === 'generation'">
            用于：生成测试用例、执行UI自动化、对话。<br/>推荐模型：gpt-4o, qwen2.5, qwen-vl
          </div>
          <div class="form-tip" v-if="form.use_for === 'embedding'">
            用于：知识库文档解析、RAG 检索。<br/>推荐模型：text-embedding-3, nomic-embed-text
          </div>
        </el-form-item>

        <el-form-item label="视觉能力" v-if="form.use_for === 'generation'">
          <el-switch
            v-model="form.model_type"
            active-value="multimodal"
            inactive-value="text"
            active-text="支持识图 (Multimodal)"
            inactive-text="纯文本"
          />
        </el-form-item>
        <el-form-item label="模型类型" prop="model_type">
          <el-select v-model="form.model_type" placeholder="请选择模型能力类型">
            <el-option label="纯文本 (Text Only)" value="text" />
            <el-option label="多模态 (Multimodal / Vision)" value="multimodal" />
          </el-select>
          <div class="form-tip">选“多模态”时，用例生成功能将支持上传图片。请确保模型本身支持视觉能力（如 gpt-4o, qwen-vl）。</div>
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

// 定义表单默认结构
const defaultForm = {
  id: null,
  name: '',
  provider: 'openai',
  model_name: 'gpt-4o',
  api_key_masked: '',
  base_url: '',
  model_family: '',
  memo: '',
  is_active: false,
  model_type: 'text', // [修改] 默认为纯文本
  use_for: 'generation'
}
// 切换用途时重置一些默认值
const handleUseForChange = (val: string) => {
  if (val === 'embedding') {
    form.model_type = 'text' // 向量模型一般没有多模态概念
    // 如果是本地，可以自动填默认名
    if (form.provider === 'custom') form.model_name = 'nomic-embed-text'
  }
}
const form = reactive({ ...defaultForm })

const fetchList = async () => {
  try {
    const res = await axios.get('/llm/')
    list.value = res.data
  } catch (e) {
    console.error(e)
  }
}

const openDialog = (row?: any) => {
  if (row) {
    // [修改] 编辑模式：将 row 的数据覆盖到 form
    // 确保 api_key_masked 也能回显（通常后端返回的是掩码后的key或空，用户需重新输入）
    Object.assign(form, row)
    // 防止后端旧数据没有 model_type 导致前端显示为空
    if (!form.model_type) form.model_type = 'text'
  } else {
    // [修改] 新增模式：重置为默认值
    Object.assign(form, { ...defaultForm, name: 'New Config' })
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  // 构造提交载荷
  // 注意：后端通常接收 'api_key' 字段，而前端表单绑定的是 'api_key_masked'
  // 如果是编辑且用户没改密码（api_key_masked 为空或掩码），后端应处理不更新密码的逻辑
  const payload = {
    ...form,
    api_key: form.api_key_masked,
    // 显式确保 model_type 被发送
    model_type: form.model_type
  }

  try {
    if (form.id) {
      await axios.put(`/llm/${form.id}`, payload)
    } else {
      await axios.post('/llm/', payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
  } catch (e: any) {
    // 简单的错误提示优化
    const msg = e.response?.data?.detail || '保存失败'
    ElMessage.error(msg)
  }
}

const handleActivate = async (row: any) => {
  try {
    await axios.post(`/llm/${row.id}/activate`)
    ElMessage.success('已切换为当前配置')
    fetchList()
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/llm/${id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
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