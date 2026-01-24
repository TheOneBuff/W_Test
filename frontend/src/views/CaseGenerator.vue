<template>
  <div class="gen-container">
    <div class="left-panel">
      <div class="panel-card">
        <div class="panel-header">
          <span class="title">需求录入</span>
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
              :file-list="fileList"
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
            <div class="upload-desc" v-if="isMultimodal">
              上传图片后，AI 将结合图片内容设计用例
            </div>
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
                <div class="text-truncate" :title="row.requirement">{{ row.requirement }}</div>
              </template>
            </el-table-column>
            <el-table-column label="图片" width="70" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image_path"
                  style="width: 30px; height: 30px"
                  :src="getImageUrl(row.image_path)"
                  :preview-src-list="[getImageUrl(row.image_path)]"
                  preview-teleported
                />
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
                <el-button v-if="row.status === 'success'" type="primary" link @click="goToDetail(row.id)">详情</el-button>
                <el-popover v-if="row.status === 'failed'" :content="row.error_msg" trigger="hover" width="200">
                   <template #reference><el-button type="danger" link>原因</el-button></template>
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

const router = useRouter()
const requirement = ref('')
const submitting = ref(false)
const loadingRecords = ref(false)
const records = ref<any[]>([])
const fileList = ref<any[]>([])
const currentModel = ref<any>(null)

// [新增] 用于存储复用的图片后端路径
const reusedImagePath = ref('')

const isMultimodal = computed(() => currentModel.value?.model_type === 'multimodal')

// [新增] 图片路径转换工具
const getImageUrl = (dbPath: string) => {
  if (!dbPath) return ''
  // 假设后端存的是 /app/uploads/xxx.jpg，替换为 Nginx 代理的 /uploads/xxx.jpg
  return dbPath.replace('/app/uploads', '/uploads')
}

// 1. 获取模型
const fetchActiveModel = async () => {
  try {
    const res = await axios.get('/llm') // 请确认接口路径
    const configs = res.data || []
    const activeGenModel = configs.find((item: any) => item.is_active === true && item.use_for === 'generation')
    currentModel.value = activeGenModel || null
    if (!activeGenModel) ElMessage.warning('未检测到激活的生成模型')
  } catch (e) {
    console.error(e)
  }
}

// 2. 获取记录
const fetchRecords = async () => {
  loadingRecords.value = true
  try {
    const res = await axios.get('/knowledge/records')
    records.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loadingRecords.value = false
  }
}

// 3. [修改] 提交逻辑
const handleSubmit = async () => {
  if (!currentModel.value) return ElMessage.error('请先激活模型')

  // 校验：有文字 OR 有新图 OR 有复用图
  const hasText = requirement.value.trim().length > 0
  const hasNewImg = fileList.value.length > 0 && fileList.value[0].raw
  const hasReuseImg = !!reusedImagePath.value

  console.log('提交状态:', { hasText, hasNewImg, hasReuseImg, reusePath: reusedImagePath.value })

  if (!hasText && !hasNewImg && !hasReuseImg) {
    return ElMessage.warning('请输入需求描述，或上传参考图片')
  }

  submitting.value = true

  try {
    const formData = new FormData()
    formData.append('requirement', requirement.value)

    // 逻辑：优先使用新上传的文件
    if (fileList.value.length > 0 && fileList.value[0].raw) {
      formData.append('image_file', fileList.value[0].raw)
    }
    // 如果没有新文件，但有复用路径，传路径
    else if (reusedImagePath.value) {
      formData.append('reuse_image_path', reusedImagePath.value)
    }

    const res = await axios.post('/knowledge/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000
    })

    if (res.data.status === 'success') {
      ElMessage.success('任务提交成功')
      requirement.value = ''
      fileList.value = []
      reusedImagePath.value = '' // 清空复用状态
      await fetchRecords()
    } else {
      ElMessage.error('提交异常')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '服务异常')
  } finally {
    submitting.value = false
  }
}

// 4. [修改] 复用逻辑
const handleReuse = (row: any) => {
  // 回填文字
  requirement.value = row.requirement

  // 回填图片
  if (row.image_path) {
    reusedImagePath.value = row.image_path // 1. 记录后端路径

    // 2. 构造假文件对象用于显示 (注意：没有 raw 属性)
    fileList.value = [{
      name: '历史图片.jpg',
      url: getImageUrl(row.image_path), // 用于预览
      status: 'success',
      uid: Date.now()
    }]
  } else {
    reusedImagePath.value = ''
    fileList.value = []
  }

  ElMessage.success('需求与图片已回填')
}

// 5. [修改] 文件状态变更
const handleFileChange = (file: any) => {
  // 核心逻辑：只有当文件包含 raw 属性时，才代表是用户手动选择的本地文件
  // 代码回填的图片对象只有 url，没有 raw
  if (file.raw) {
    console.log('用户选择了新文件:', file.name)
    reusedImagePath.value = '' // 用户选了新图，清空复用路径
    fileList.value = [file]    // 限制单选
  } else {
     console.log('检测到图片回填，保持复用路径不变')
  }
}

const handleFileRemove = () => {
  reusedImagePath.value = ''
  fileList.value = []
}

const goToDetail = (id: number) => { router.push(`/testcase/result/${id}`) }
const formatDate = (str: string) => dayjs(str).format('MM-DD HH:mm')

onMounted(() => {
  fetchActiveModel()
  fetchRecords()
})
</script>

<style scoped>
/* 保持原有样式不变 */
.gen-container { display: flex; gap: 16px; height: calc(100vh - 84px); padding: 16px; background-color: #f5f7fa; box-sizing: border-box; }
.left-panel { width: 400px; flex-shrink: 0; display: flex; flex-direction: column; }
.right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.panel-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; height: 100%; }
.panel-header { padding: 12px 20px; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
.title { font-weight: 600; font-size: 15px; color: #1f2937; }
.panel-body { padding: 20px; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 20px; }
.table-body { padding: 0; }
.req-input :deep(.el-textarea__inner) { padding: 12px; font-size: 14px; }
.upload-section { background: #fafafa; border: 1px dashed #d9d9d9; border-radius: 6px; padding: 16px; position: relative; }
.upload-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 13px; color: #606266; }
.unsupported-tip { color: #e6a23c; font-size: 12px; }
.generate-btn { width: 100%; height: 40px; font-size: 15px; letter-spacing: 1px; }
.hide-upload-btn :deep(.el-upload--picture-card) { display: none; }
.text-truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #606266; }
.time-text { font-size: 12px; color: #909399; }
.text-gray { color: #dcdfe6; }
:deep(.el-table .cell) { padding: 8px 12px; }
</style>