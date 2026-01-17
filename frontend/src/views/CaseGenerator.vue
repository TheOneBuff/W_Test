<template>
  <div class="gen-container">
    <div class="left-panel">
      <div class="panel-card">
        <div class="panel-header">
          <span class="title">新建生成任务</span>
          <el-tag
            size="small"
            :type="currentModel ? (isMultimodal ? 'success' : 'warning') : 'danger'"
            effect="dark"
          >
            <el-icon v-if="!currentModel"><WarnTriangleFilled /></el-icon>
            <span v-else>
              {{ currentModel.name }} ({{ isMultimodal ? '多模态' : '纯文本' }})
            </span>
          </el-tag>
        </div>

        <div class="panel-body">
          <el-input
            v-model="requirement"
            type="textarea"
            :rows="12"
            placeholder="请输入详细的需求描述，例如：
1. 登录模块：手机号必须11位...
2. 订单模块：金额计算规则..."
            resize="none"
            class="req-input"
          />

          <div class="upload-section">
            <div class="upload-header">
              <span>参考图片 (可选)</span>
              <span v-if="!isMultimodal && currentModel" class="unsupported-tip">
                * 当前模型不支持识图，图片将被忽略
              </span>
            </div>

            <el-upload
              action="#"
              ref="uploadRef"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="1"
              list-type="picture-card"
              accept=".jpg,.jpeg,.png"
              :class="{ 'hide-upload-btn': fileList.length >= 1 }"
            >
              <el-icon><Plus /></el-icon>
            </el-upload>
          </div>

          <div class="actions">
            <el-button
              type="primary"
              class="generate-btn"
              @click="handleSubmit"
              :loading="submitting"
              :icon="MagicStick"
              :disabled="!currentModel"
            >
              {{ submitting ? '正在生成中(请稍候)...' : '提交生成任务' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="right-panel">
      <div class="panel-card">
        <div class="panel-header">
          <span class="title">生成历史记录</span>
          <el-button :icon="Refresh" circle size="small" @click="fetchRecords" title="刷新列表" />
        </div>

        <div class="panel-body table-body">
          <el-table
            :data="records"
            stripe
            height="100%"
            v-loading="loadingRecords"
            element-loading-text="加载历史记录..."
          >
            <el-table-column prop="id" label="ID" width="60" align="center" />

            <el-table-column label="需求摘要" min-width="180">
              <template #default="{ row }">
                <div class="text-truncate" :title="row.requirement">
                  {{ row.requirement }}
                </div>
              </template>
            </el-table-column>

            <el-table-column label="图片" width="70" align="center">
              <template #default="{ row }">
                <el-icon v-if="row.image_path"><Picture /></el-icon>
                <span v-else class="text-gray">-</span>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.status==='success'" type="success" size="small" effect="light">成功</el-tag>
                <el-tag v-else-if="row.status==='processing'" type="primary" size="small" effect="light">生成中</el-tag>
                <el-tag v-else-if="row.status==='failed'" type="danger" size="small" effect="light">失败</el-tag>
                <el-tag v-else type="info" size="small">排队</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="创建时间" width="140" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.create_time) }}</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="140" align="center" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'success'"
                  type="primary"
                  link
                  @click="goToDetail(row.id)"
                >
                  详情
                </el-button>

                <el-popover
                  v-if="row.status === 'failed'"
                  placement="top"
                  title="失败原因"
                  :width="200"
                  trigger="hover"
                  :content="row.error_msg || '未知错误'"
                >
                  <template #reference>
                    <el-button type="danger" link>原因</el-button>
                  </template>
                </el-popover>

                <el-button type="primary" link @click="handleReuse(row)">复用</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/request'
import { Picture, Plus, MagicStick, WarnTriangleFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

// --- 状态定义 ---
const router = useRouter()
const requirement = ref('')
const submitting = ref(false)   // 提交loading
const loadingRecords = ref(false) // 列表loading
const records = ref<any[]>([])  // 历史记录数据
const fileList = ref<any[]>([])
const currentModel = ref<any>(null)

// --- 计算属性 ---
const isMultimodal = computed(() => {
  return currentModel.value?.model_type === 'multimodal'
})

// --- 核心逻辑 ---

// 1. 获取当前模型配置
const fetchActiveModel = async () => {
  try {
    const res = await axios.get('/llm')
    const configs = res.data || []
    const activeGenModel = configs.find((item: any) =>
      item.is_active === true && item.use_for === 'generation'
    )
    if (activeGenModel) {
      currentModel.value = activeGenModel
    } else {
      currentModel.value = null
      ElMessage.warning('未检测到激活的生成模型')
    }
  } catch (e) {
    console.error(e)
  }
}

// 2. 获取历史记录列表
const fetchRecords = async () => {
  loadingRecords.value = true
  try {
    // 假设后端新增了 GET /knowledge/records 接口
    const res = await axios.get('/knowledge/records')
    records.value = res.data
  } catch (e) {
    console.error('获取历史记录失败', e)
  } finally {
    loadingRecords.value = false
  }
}

// 3. 提交任务
const handleSubmit = async () => {
  if (!currentModel.value) return ElMessage.error('请先激活模型')

  const hasText = requirement.value.trim().length > 0
  const hasImg = fileList.value.length > 0

  if (!hasText && !hasImg) {
    return ElMessage.warning('请输入需求描述，或上传参考图片')
  }

  submitting.value = true

  try {
    const formData = new FormData()
    formData.append('requirement', requirement.value)

    if (fileList.value.length > 0) {
      formData.append('image_file', fileList.value[0].raw)
    }

    // 调用后端生成接口 (注意：后端现在返回的是 record_id，不再是直接的 json)
    const res = await axios.post('/knowledge/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000 // 10分钟超时
    })

    if (res.data.status === 'success') {
      ElMessage.success('任务提交成功')
      // 清空输入
      requirement.value = ''
      fileList.value = []
      // 刷新列表
      await fetchRecords()

      // 可选：如果想直接跳转详情
      // if (res.data.record_id) goToDetail(res.data.record_id)
    } else {
      ElMessage.error('提交异常')
    }

  } catch (e: any) {
    console.error(e)
    ElMessage.error(e.response?.data?.detail || '请求超时或服务异常')
  } finally {
    submitting.value = false
  }
}

// 4. 跳转详情页
const goToDetail = (id: number) => {
  router.push(`/testcase/result/${id}`)
}

// 5. 复用需求
const handleReuse = (row: any) => {
  requirement.value = row.requirement
  ElMessage.info('需求内容已回填，可修改后重新提交')
}

// 文件处理
const handleFileChange = (file: any) => { fileList.value = [file] }
const handleFileRemove = () => { fileList.value = [] }
const formatDate = (str: string) => dayjs(str).format('MM-DD HH:mm')

onMounted(() => {
  fetchActiveModel()
  fetchRecords()
})
</script>

<style scoped>
.gen-container {
  display: flex;
  gap: 16px;
  height: calc(100vh - 84px);
  padding: 16px;
  background-color: #f5f7fa;
  box-sizing: border-box;
}

.left-panel { width: 400px; flex-shrink: 0; display: flex; flex-direction: column; }
.right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.panel-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.title { font-weight: 600; font-size: 15px; color: #1f2937; }

.panel-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.table-body { padding: 0; }

.req-input :deep(.el-textarea__inner) {
  padding: 12px;
  font-size: 14px;
}

.upload-section {
  background: #fafafa;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  padding: 16px;
  position: relative;
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
}

.unsupported-tip { color: #e6a23c; font-size: 12px; }

.generate-btn {
  width: 100%;
  height: 40px;
  font-size: 15px;
  letter-spacing: 1px;
}

.hide-upload-btn :deep(.el-upload--picture-card) { display: none; }

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #606266;
}

.time-text { font-size: 12px; color: #909399; }
.text-gray { color: #dcdfe6; }

:deep(.el-table .cell) { padding: 8px 12px; }
</style>