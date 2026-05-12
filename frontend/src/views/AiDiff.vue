<template>
  <div class="diff-container">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold text-lg">🧠 AI 智能视觉找茬 (纯文本模式)</span>
          <el-button type="primary" :loading="loading" @click="handleAnalyze">
            <el-icon class="mr-1"><MagicStick /></el-icon> 开始 AI 分析
          </el-button>
        </div>
      </template>

      <div class="mb-6">
        <div class="mb-2 text-sm text-gray-500">AI 指令 (Prompt):</div>
        <el-input
          v-model="prompt"
          placeholder="例如：找出所有key不一致的地方，不比较value"
          clearable
        >
          <template #prepend>关注点</template>
        </el-input>
      </div>

      <div class="content-grid">
        <div class="upload-section">
            <div class="upload-item">
                <div class="label">1. 预期图 (Baseline)</div>
                <el-upload
                  class="uploader"
                  action="#"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => handleFileChange(f, 1)"
                >
                  <img v-if="preview1" :src="preview1" class="preview-img" />
                  <div v-else class="placeholder">
                    <el-icon :size="24"><Plus /></el-icon>
                    <span>点击上传基准图</span>
                  </div>
                </el-upload>
            </div>

            <div class="upload-item">
                <div class="label">2. 实际图 (Target)</div>
                <el-upload
                  class="uploader"
                  action="#"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => handleFileChange(f, 2)"
                >
                  <img v-if="preview2" :src="preview2" class="preview-img" />
                  <div v-else class="placeholder">
                    <el-icon :size="24"><Plus /></el-icon>
                    <span>点击上传对比图</span>
                  </div>
                </el-upload>
            </div>
        </div>

        <div class="result-section">
             <div class="flex items-center justify-between mb-2">
                <div class="label text-red-600">AI 分析结果</div>
                <el-tag v-if="hasResult" :type="diffCount > 0 ? 'danger' : 'success'">
                    {{ diffCount }} 处差异
                </el-tag>
             </div>

             <div class="result-box">
                 <div v-if="loading" class="empty-result">
                    <el-icon class="is-loading mr-2"><Loading /></el-icon>
                    AI 正在通过视觉大模型对比差异，这可能需要几分钟...
                 </div>

                 <div v-else-if="!hasResult" class="empty-result">
                    <span class="text-gray-400">请上传两张图片并点击“开始分析”</span>
                 </div>

                 <div v-else-if="diffDetails.length > 0" class="diff-list-container">
                   <el-scrollbar height="100%">
                     <div v-for="(item, index) in diffDetails" :key="index" class="diff-item">
                       <div class="item-header">
                           <el-tag size="small" type="danger" effect="dark" class="diff-idx">{{ index + 1 }}</el-tag>
                           <el-tag v-if="item.type" size="small" effect="plain" class="ml-2">{{ item.type }}</el-tag>
                       </div>
                       <div class="diff-text mt-1">{{ item.reason }}</div>
                     </div>
                   </el-scrollbar>
                 </div>

                 <div v-else class="empty-result">
                    <el-result icon="success" title="完美一致" sub-title="AI 未发现明显的视觉或文案差异"></el-result>
                 </div>
             </div>

             <div v-if="rawResponse" class="mt-2">
                <el-collapse>
                    <el-collapse-item title="查看原始思维链 (Raw Response)" name="1">
                        <pre class="text-xs text-gray-400 bg-gray-50 p-2 rounded overflow-auto max-h-32">{{ rawResponse }}</pre>
                    </el-collapse-item>
                </el-collapse>
             </div>
        </div>
      </div>
    </el-card>

    <div class="mt-4 text-xs text-gray-400">
        * 本功能仅通过 AI 视觉理解生成文字描述，不包含坐标定位，请结合原图查看。
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus, MagicStick, Loading } from '@element-plus/icons-vue'
import request from '@/utils/request' // 确保这里指向你的 axios 封装
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

const prompt = ref("找出所有key不一致的地方，不比较value（例如文案、标签、按钮文字不同），忽略动态数据")
const file1 = ref<any>()
const file2 = ref<any>()
const preview1 = ref('')
const preview2 = ref('')
const loading = ref(false)
const hasResult = ref(false)

// 结果数据
const diffCount = ref(0)
const diffDetails = ref<any[]>([])
const rawResponse = ref('')

const handleFileChange = (file: UploadFile, index: number) => {
    const raw = file.raw
    if (!raw) return

    const url = URL.createObjectURL(raw)
    if (index === 1) {
        file1.value = raw
        preview1.value = url
    } else {
        file2.value = raw
        preview2.value = url
    }
    // 图片变更后重置结果状态
    hasResult.value = false
}

const handleAnalyze = async () => {
    if (!file1.value || !file2.value) {
        ElMessage.warning('请确保两张图片都已上传')
        return
    }

    loading.value = true
    hasResult.value = false
    diffDetails.value = []
    diffCount.value = 0
    rawResponse.value = ''

    try {
        const formData = new FormData()
        formData.append('file1', file1.value)
        formData.append('file2', file2.value)
        formData.append('prompt_hint', prompt.value)

        // [修改 1] 路径修正为 /vision_llm/ai-diff (匹配后端路由前缀)
        // [修改 2] 超时时间增加到 300000ms (5分钟)
        const res = await request.post('/vision/ai-diff', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 600000
        })

        // 处理返回数据
        diffCount.value = res.data.diff_count
        diffDetails.value = res.data.details || []
        rawResponse.value = res.data.raw_response
        hasResult.value = true

        if (res.data.diff_count === 0) {
            ElMessage.success(res.data.msg || 'AI 未发现符合条件的差异')
        } else {
            ElMessage.warning(`AI 发现了 ${res.data.diff_count} 处差异`)
        }

    } catch (e: any) {
        console.error(e)
        // 错误处理优化
        let msg = e.response?.data?.detail || '请求失败，请检查网络或模型配置'
        if (e.code === 'ECONNABORTED' && e.message.includes('timeout')) {
            msg = 'AI 响应超时，建议检查网络或稍后重试'
        }
        ElMessage.error(`分析失败: ${msg}`)
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.diff-container { max-width: 1200px; margin: 20px auto; }
.content-grid { display: flex; gap: 24px; margin-top: 20px; min-height: 500px; }

/* 左侧上传区 */
.upload-section { flex: 1; display: flex; flex-direction: column; gap: 20px; }
.upload-item { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.label { font-weight: 600; color: #374151; font-size: 14px; }

.uploader { width: 100%; height: 100%; display: flex; flex-direction: column; }
/* 让图片预览区域撑满 */
:deep(.el-upload) { width: 100%; height: 100%; }

.preview-img {
    width: 100%;
    height: 100%;
    min-height: 240px;
    object-fit: contain;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f9fafb;
}
.placeholder {
  width: 100%;
  height: 100%;
  min-height: 240px;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.3s;
  background: #f9fafb;
}
.placeholder:hover { border-color: #4f46e5; color: #4f46e5; background: #f5f3ff; }

/* 右侧结果区 */
.result-section { flex: 1; display: flex; flex-direction: column; }
.result-box {
    flex: 1;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 400px;
}

.empty-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 14px;
  padding: 20px;
}

/* 差异列表 */
.diff-list-container {
    flex: 1;
    padding: 12px;
    background: #fff;
}

.diff-item {
    margin-bottom: 12px;
    padding: 12px;
    border-radius: 6px;
    border: 1px solid #f3f4f6;
    background: #fdfdfd;
    transition: all 0.2s;
}
.diff-item:hover {
    border-color: #d1d5db;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.item-header { display: flex; align-items: center; }
.diff-idx { min-width: 24px; text-align: center; }
.diff-text {
    font-size: 14px;
    color: #374151;
    line-height: 1.6;
    padding-left: 4px;
}
</style>