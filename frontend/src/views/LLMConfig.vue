<template>
  <div class="llm-config">
    <el-card shadow="never" class="config-card">
      <template #header>
        <div class="card-header">
          <span>大模型参数配置</span>
          <el-tag type="info">当前配置仅对您生效</el-tag>
        </div>
      </template>

      <el-form :model="form" label-width="120px" label-position="left">
        <el-form-item label="服务提供商">
          <el-select v-model="form.provider" placeholder="Select provider" style="width: 100%">
            <el-option label="qwen3-vl" value="qwen3-vl" />
            <el-option label="Custom (Ollama/vLLM)" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="form.model_name" placeholder="qwen3-vl-plus" />
          <div class="tips">Midscene 推荐使用 xxx 以获得最佳效果。</div>
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key_masked"
            type="password"
            placeholder="sk-..."
            show-password
          />
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="可选，例如国内代理地址" />
        </el-form-item>

        <el-form-item label="Model Family">
          <el-select v-model="form.model_family" placeholder="Optional" clearable>
             <el-option label="qwen3-vl" value="qwen3-vl" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.memo"
            type="textarea"
            :rows="2"
            placeholder="例如：这是公司内部部署的 deepseek 模型..."
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
          <el-button @click="fetchConfig">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'

const saving = ref(false)
const form = reactive({
  provider: 'openai',
  model_name: 'gpt-4o',
  api_key_masked: '',
  base_url: '',
  model_family: '',
  memo: ''

})

const fetchConfig = async () => {
  try {
    const res = await axios.get('/llm/')
    const data = res.data
    form.provider = data.provider
    form.model_name = data.model_name
    form.base_url = data.base_url
    form.api_key_masked = data.api_key_masked
    form.model_family = data.model_family
    form.memo = data.memo
  } catch (error) {
    console.error(error)
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    // 构造发送的数据，将 masked 字段映射回 api_key
    const payload = {
      provider: form.provider,
      model_name: form.model_name,
      base_url: form.base_url,
      api_key: form.api_key_masked, // 后端会判断如果包含 **** 就不更新
      memo: form.memo,
      model_family: form.model_family
    }

    await axios.put('/llm/', payload)
    ElMessage.success('配置已保存')
    fetchConfig() // 刷新以确认
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.llm-config {
  padding: 20px;
  background-color: #fff;
  min-height: 100%;
}
.config-card {
  max-width: 800px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.tips {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
