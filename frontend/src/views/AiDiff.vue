<template>
  <div class="diff-container">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold text-lg">🧠 AI 智能视觉找茬 (Semantic Diff)</span>
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
                <div class="label">预期图 (Expected)</div>
                <el-upload
                  class="uploader"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => handleFileChange(f, 1)"
                >
                  <img v-if="preview1" :src="preview1" class="preview-img" />
                  <div v-else class="placeholder">
                    <el-icon :size="24"><Plus /></el-icon>
                    <span>点击上传</span>
                  </div>
                </el-upload>
            </div>

            <div class="upload-item">
                <div class="label">实际图 (Actual)</div>
                <el-upload
                  class="uploader"
                  :auto-upload="false"
                  :show-file-list="false"
                  :on-change="(f: any) => handleFileChange(f, 2)"
                >
                  <img v-if="preview2" :src="preview2" class="preview-img" />
                  <div v-else class="placeholder">
                    <el-icon :size="24"><Plus /></el-icon>
                    <span>点击上传</span>
                  </div>
                </el-upload>
            </div>
        </div>

        <div class="result-section">
             <div class="label text-red-600">AI 分析结果 ({{ diffCount }} 处差异)</div>

             <div class="result-box">
                 <div v-if="resultImage" class="img-container">
                     <el-image
                        :src="resultImage"
                        :preview-src-list="[resultImage]"
                        fit="contain"
                        class="result-img"
                     />
                 </div>
                 <div v-else class="empty-result">
                    <span v-if="loading">AI 正在思考中...</span>
                    <span v-else>等待分析结果</span>
                 </div>
             </div>

             <div v-if="diffDetails.length > 0" class="diff-list">
               <div class="list-title">差异详情:</div>
               <el-scrollbar max-height="300px">
                 <div v-for="(item, index) in diffDetails" :key="index" class="diff-item">
                   <el-tag size="small" type="danger" effect="dark" class="diff-idx">{{ index + 1 }}</el-tag>
                   <span class="diff-text">{{ item.reason }}</span>
                 </div>
               </el-scrollbar>
             </div>
        </div>
      </div>
    </el-card>

    <div class="mt-4 text-xs text-gray-400">
        * 依赖 LLM (如 GPT-4o) 的视觉理解能力，可能会产生幻觉或位置偏差，仅供参考。
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus, MagicStick } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

const prompt = ref("找出所有key不一致的地方，不比较value（例如文案、标签、按钮文字不同），忽略动态数据")
const file1 = ref<File>()
const file2 = ref<File>()
const preview1 = ref('')
const preview2 = ref('')
const loading = ref(false)
const resultImage = ref('')
const diffCount = ref(0)
const diffDetails = ref<any[]>([]) // 存储差异详情

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
}

const handleAnalyze = async () => {
    if (!file1.value || !file2.value) {
        ElMessage.warning('请上传两张图片')
        return
    }

    loading.value = true
    resultImage.value = ''
    diffDetails.value = []
    diffCount.value = 0

    try {
        const formData = new FormData()
        formData.append('file1', file1.value!)
        formData.append('file2', file2.value!)
        formData.append('prompt_hint', prompt.value)

        // 确保你的 request baseURL 配置正确，如果是 /api，则这里路径是 /vision/ai-diff
        // 如果后端注册路径是 /api/vision，且 request baseURL 是 /api，则此处写 /vision/ai-diff
        const res = await request.post('/vision/ai-diff', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })

        // 处理返回数据
        resultImage.value = res.data.result_image
        diffCount.value = res.data.diff_count
        diffDetails.value = res.data.details || []

        if (res.data.diff_count === 0) {
            ElMessage.success('AI 未发现符合条件的差异')
        } else {
            ElMessage.warning(`AI 发现了 ${res.data.diff_count} 处差异`)
        }

    } catch (e: any) {
        console.error(e)
        // 尝试提取后端返回的具体错误信息
        const msg = e.response?.data?.detail || '请求失败'
        ElMessage.error(`分析失败: ${msg}`)
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.diff-container { max-width: 1200px; margin: 20px auto; }
.content-grid { display: flex; gap: 24px; margin-top: 20px; }

/* 左侧上传区 */
.upload-section { flex: 1; display: flex; flex-direction: column; gap: 20px; }
.upload-item { display: flex; flex-direction: column; gap: 8px; }
.label { font-weight: 600; color: #374151; font-size: 14px; text-align: center; }

.uploader { width: 100%; }
.preview-img { width: 100%; height: 280px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; }
.placeholder {
  width: 100%; height: 280px; border: 2px dashed #d1d5db; border-radius: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #9ca3af; cursor: pointer; transition: all 0.3s;
}
.placeholder:hover { border-color: #4f46e5; color: #4f46e5; background: #f5f3ff; }

/* 右侧结果区 */
.result-section { flex: 1.2; display: flex; flex-direction: column; gap: 10px; }
.result-box { border: 2px solid #fecaca; border-radius: 8px; padding: 4px; background: #fef2f2; min-height: 300px; }
.img-container { width: 100%; height: 400px; }
.result-img { width: 100%; height: 100%; }
.empty-result {
  height: 400px; display: flex; align-items: center; justify-content: center;
  color: #9ca3af; font-size: 14px;
}

/* 差异列表 */
.diff-list { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-top: 10px; }
.list-title { font-weight: 600; font-size: 13px; margin-bottom: 8px; color: #374151; }
.diff-item { display: flex; align-items: start; gap: 8px; margin-bottom: 8px; font-size: 13px; color: #4b5563; padding-bottom: 8px; border-bottom: 1px dashed #f3f4f6; }
.diff-item:last-child { border-bottom: none; margin-bottom: 0; }
.diff-idx { min-width: 20px; text-align: center; }
.diff-text { line-height: 1.4; }
</style>