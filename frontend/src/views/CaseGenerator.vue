<template>
  <div class="gen-container">
    <div class="left-panel">
      <div class="panel-card">
        <div class="panel-header">
          <span class="title">智能用例生成</span>

          <el-tag :type="modelStatus.type" effect="dark" class="status-tag">
            <div class="tag-content">
              <template v-if="modelStatus.code === 'error'">
                <el-icon><CircleCloseFilled /></el-icon>
                <span>生成服务不可用 (is_active_gen=0)</span>
              </template>

              <template v-else>
                <el-icon v-if="modelStatus.code === 'success'"><CircleCheckFilled /></el-icon>
                <el-icon v-else><WarnTriangleFilled /></el-icon>

                <span>
                  {{ currentGenModel?.name }}
                  <span class="sub-text">
                    | {{ isMultimodal ? '多模态' : '纯文本' }}
                    | {{ hasChatModel ? '检索✅' : '无检索⚠️' }}
                  </span>
                </span>
              </template>
            </div>
          </el-tag>
        </div>

        <div class="panel-body">
          <el-input
            v-model="requirement"
            type="textarea"
            :rows="12"
            placeholder="请输入详细的测试需求，例如：
1. 登录模块：验证手机号格式、验证码超时逻辑...
2. 支付模块：余额不足时的提示..."
            resize="none"
            class="req-input"
          />

          <div class="skill-section" style="margin-top: 16px;">
            <div class="upload-header">
              <span>选择技能 (可选)</span>
              <el-link type="primary" :underline="false" @click="$router.push('/skills')">管理技能</el-link>
            </div>
            <el-select
              v-model="selectedSkillId"
              placeholder="使用默认提示词"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="skill in availableSkills"
                :key="skill.id"
                :label="skill.name"
                :value="skill.id"
              >
                <span>{{ skill.name }}</span>
                <el-tag size="small" type="info" style="margin-left: 8px;">
                  {{ skill.skill_type === 'image' ? '图片' : skill.skill_type === 'text' ? '文本' : '通用' }}
                </el-tag>
              </el-option>
            </el-select>
          </div>

          <div class="rule-section" style="margin-top: 16px;">
            <div class="upload-header" style="display: flex; justify-content: space-between; align-items: center;">
              <span>规则/规则集 (可选)</span>
              <div>
                <el-link type="primary" :underline="false" @click="$router.push('/rules')">管理规则</el-link>
              </div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <el-select
                v-model="selectedRuleSetId"
                placeholder="选择规则集"
                clearable
                style="flex: 1"
                @change="onRuleSetChange"
              >
                <el-option
                  v-for="set in availableRuleSets"
                  :key="set.id"
                  :label="set.name"
                  :value="set.id"
                >
                  <span>{{ set.name }}</span>
                  <el-tag v-if="set.is_default" size="small" type="success" style="margin-left: 8px;">默认</el-tag>
                </el-option>
              </el-select>
              <el-select
                v-model="selectedRuleIds"
                placeholder="手动选择规则"
                multiple
                collapse-tags
                collapse-tags-tooltip
                clearable
                style="flex: 1.5"
                :disabled="!!selectedRuleSetId"
              >
                <el-option
                  v-for="rule in availableRules"
                  :key="rule.id"
                  :label="rule.name"
                  :value="rule.id"
                >
                  <span>{{ rule.name }}</span>
                  <el-tag :type="ruleTypeTag(rule.rule_type)" size="small" style="margin-left: 6px;">
                    {{ ruleTypeLabel(rule.rule_type) }}
                  </el-tag>
                </el-option>
              </el-select>
            </div>
            <div v-if="selectedRuleSetId || selectedRuleIds.length" class="rule-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>已选择 {{ selectedRuleSetId ? '1个规则集' : selectedRuleIds.length + '条规则' }}，生成时将自动匹配业务规则和约束条件</span>
            </div>
          </div>

          <div class="upload-section">
            <div class="upload-header">
              <span>参考图片 (UI/原型图)</span>
            </div>

            <template v-if="isMultimodal">
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

              <div class="upload-desc">
                <span v-if="reusedImagePath" class="reuse-tag">已复用历史图片</span>
                <span v-else>当前使用 <b>{{ currentGenModel?.name }}</b>，支持视觉分析</span>
              </div>
            </template>

            <template v-else>
              <div class="unsupported-box">
                <el-icon class="icon"><Warning /></el-icon>
                <div class="text">
                  当前模型仅支持纯文本<br>
                  <span class="sub">如需传图，请在配置页激活 Multimodal 模型</span>
                </div>
              </div>
            </template>
          </div>

          <div class="actions">
            <el-button
              type="primary"
              class="generate-btn"
              @click="handleSubmit"
              :loading="submitting"
              :icon="MagicStick"
              :disabled="!currentGenModel"
            >
              {{ submitting ? 'AI 正在生成中...' : '提交生成任务' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="right-panel">
      <div class="panel-card">
        <div class="panel-header">
          <span class="title">任务历史</span>
          <el-button :icon="Refresh" circle size="small" @click="fetchRecords" title="刷新列表" />
        </div>

        <div class="panel-body table-body">
          <el-table
            :data="records"
            stripe
            height="100%"
            v-loading="loadingRecords"
            element-loading-text="加载中..."
          >
            <el-table-column prop="id" label="ID" width="60" align="center" />

            <el-table-column label="需求摘要" min-width="150">
              <template #default="{ row }">
                <div class="text-truncate" :title="row.requirement">{{ row.requirement }}</div>
              </template>
            </el-table-column>

            <el-table-column label="图片" width="70" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.image_path"
                  style="width: 36px; height: 36px; border-radius: 4px"
                  :src="getImageUrl(row.image_path)"
                  :preview-src-list="[getImageUrl(row.image_path)]"
                  preview-teleported
                  fit="cover"
                />
                <span v-else class="text-gray">-</span>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.status==='success'" type="success" size="small" effect="light">成功</el-tag>
                <el-tag v-else-if="row.status==='processing'" type="primary" size="small" effect="light">生成中</el-tag>
                <el-tag v-else-if="row.status==='failed'" type="danger" size="small" effect="light">失败</el-tag>
                <el-tag v-else type="info" size="small">等待</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="时间" width="120" align="center">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.create_time) }}</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="130" align="center" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'success'"
                  type="primary" link
                  @click="goToDetail(row.id)"
                >详情</el-button>

                <el-popover
                  v-if="row.status === 'failed'"
                  :content="row.error_msg || '未知错误'"
                  trigger="hover"
                  width="200"
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
import {
  Picture, Plus, MagicStick, Refresh, Warning, InfoFilled,
  WarnTriangleFilled, CircleCloseFilled, CircleCheckFilled
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import * as skillApi from '../api/skills'
import * as ruleSetsApi from '../api/rule_sets'
import * as rulesApi from '../api/rules'

const router = useRouter()

// --- 状态变量 ---
const requirement = ref('')
const submitting = ref(false)
const loadingRecords = ref(false)
const records = ref<any[]>([])
const fileList = ref<any[]>([])
const availableSkills = ref<any[]>([])
const selectedSkillId = ref<number | null>(null)

// 规则选择
const selectedRuleSetId = ref<number | null>(null)
const selectedRuleIds = ref<number[]>([])
const availableRuleSets = ref<any[]>([])
const availableRules = ref<any[]>([])

// 模型状态
const currentGenModel = ref<any>(null) // 生成模型
const hasChatModel = ref(false)        // 检索模型
const reusedImagePath = ref('')        // 复用的图片路径

// --- 计算属性 ---

// [逻辑1] 判断是否多模态 (支持图片)
// 规则：model_type == 'multimodal' 或者 名字里包含 'vl' (适配 qwen3-vl)
const isMultimodal = computed(() => {
  if (!currentGenModel.value) return false
  const type = currentGenModel.value.model_type?.toLowerCase()
  const name = currentGenModel.value.model_name?.toLowerCase()
  return type === 'multimodal' || (name && name.includes('vl'))
})

// [逻辑2] 整体系统状态颜色
const modelStatus = computed(() => {
  if (!currentGenModel.value) {
    return { type: 'danger', code: 'error' } // 红：无法生成
  }
  if (!hasChatModel.value) {
    return { type: 'warning', code: 'warning' } // 橙：无法检索
  }
  return { type: 'success', code: 'success' } // 绿：正常
})

// --- 方法 ---

// 1. 获取模型配置
const fetchActiveModel = async () => {
  try {
    const res = await axios.get('/llm')
    const configs = res.data || []

    // 筛选 is_active_gen = 1
    const activeGen = configs.find((item: any) => item.is_active_gen === true)

    // 筛选 is_active_chat = 1
    const activeChat = configs.find((item: any) => item.is_active_chat === true)

    currentGenModel.value = activeGen || null
    hasChatModel.value = !!activeChat

    // 检查并清理复用状态：如果切换到了纯文本模型，必须清空已选择的图片
    if (!isMultimodal.value) {
      fileList.value = []
      reusedImagePath.value = ''
    }

    // 提示
    if (!activeGen) ElMessage.error('未检测到激活的生成模型 (is_active_gen=1)')
    else if (!activeChat) ElMessage.warning('未检测到激活的检索模型 (is_active_chat=1)')

  } catch (e) {
    console.error(e)
    ElMessage.error('模型配置获取失败')
  }
}

// 2. 提交任务
const handleSubmit = async () => {
  if (!currentGenModel.value) return ElMessage.error('服务不可用')
  if (!requirement.value.trim()) return ElMessage.warning('请输入需求描述')
  if (!selectedSkillId.value) return ElMessage.warning('请选择一个技能（提示词）')

  // 校验：如果上传了图片，只能选择图片或通用类型的技能
  const hasImage = isMultimodal.value && (fileList.value.length > 0 || reusedImagePath.value)
  if (hasImage && selectedSkillId.value) {
    const selectedSkill = availableSkills.value.find(s => s.id === selectedSkillId.value)
    if (selectedSkill && selectedSkill.skill_type === 'text') {
      ElMessage.error('上传了图片时，不能选择"文本"类型的技能，请选择"图片"或"通用"类型的技能')
      return
    }
  }

  submitting.value = true
  const formData = new FormData()
  formData.append('requirement', requirement.value)

  // 图片逻辑：只有多模态才允许传图
  if (isMultimodal.value) {
    if (fileList.value.length > 0 && fileList.value[0].raw) {
      formData.append('image_file', fileList.value[0].raw)
    } else if (reusedImagePath.value) {
      formData.append('reuse_image_path', reusedImagePath.value)
    }
  }

  // 技能 ID：如果选择了技能，添加到表单中
  if (selectedSkillId.value) {
    formData.append('skill_id', String(selectedSkillId.value))
  }

  // 规则/规则集
  if (selectedRuleSetId.value) {
    formData.append('rule_set_id', String(selectedRuleSetId.value))
  } else if (selectedRuleIds.value.length > 0) {
    formData.append('rule_ids', selectedRuleIds.value.join(','))
  }

  try {
    const res = await axios.post('/knowledge/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000
    })

    if (res.data.status === 'success') {
      ElMessage.success('任务已提交')
      requirement.value = ''
      fileList.value = []
      reusedImagePath.value = ''
      selectedSkillId.value = null
      await fetchRecords()
    } else {
      ElMessage.error(res.data.msg || '提交失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '网络异常')
  } finally {
    submitting.value = false
  }
}

// 加载所有可用技能
const loadAvailableSkills = async () => {
  try {
    const res = await skillApi.getSkills({ is_active: true })
    availableSkills.value = res.data || []
  } catch (error) {
    console.error('加载技能失败:', error)
    availableSkills.value = []
  }
}

const loadAvailableRuleSets = async () => {
  try {
    const res = await ruleSetsApi.getRuleSets({ is_active: true })
    availableRuleSets.value = res.data || []
  } catch (error) {
    console.error('加载规则集失败:', error)
    availableRuleSets.value = []
  }
}

const loadAvailableRules = async () => {
  try {
    const res = await rulesApi.getRules({ is_active: true, limit: 200 })
    availableRules.value = res.data || []
  } catch (error) {
    console.error('加载规则失败:', error)
    availableRules.value = []
  }
}

const onRuleSetChange = () => {
  if (selectedRuleSetId.value) {
    selectedRuleIds.value = []
  }
}

const ruleTypeTag = (type: string) => {
  const map: Record<string, string> = {
    boundary: 'danger', equivalence: 'warning', constraint: 'primary',
    biz_rule: 'success', data_rule: 'info', security: 'danger', compatibility: ''
  }
  return map[type] || 'info'
}

const ruleTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    boundary: '边界值', equivalence: '等价类', constraint: '约束校验',
    biz_rule: '业务规则', data_rule: '数据规则', security: '安全规则', compatibility: '兼容性',
  }
  return map[type] || type
}

// 3. 历史记录复用
const handleReuse = (row: any) => {
  requirement.value = row.requirement

  // 只有当前模型支持多模态，且历史记录里有图，才回填图片
  if (isMultimodal.value && row.image_path) {
    reusedImagePath.value = row.image_path
    fileList.value = [{
      name: '历史图片.jpg',
      url: getImageUrl(row.image_path),
      status: 'success',
      uid: Date.now()
    }]
  } else {
    reusedImagePath.value = ''
    fileList.value = []
  }
  
  ElMessage.success('内容已回填')
}

// 工具函数
const getImageUrl = (dbPath: string) => {
  if (!dbPath) return ''
  return dbPath.replace('/app/uploads', '/uploads').replace('/data/uploads', '/uploads')
}

const fetchRecords = async () => {
  loadingRecords.value = true
  try {
    const res = await axios.get('/knowledge/records')
    records.value = res.data
  } finally {
    loadingRecords.value = false
  }
}

const handleFileChange = (file: any) => {
  if (file.raw) {
    reusedImagePath.value = ''
    fileList.value = [file]
  }
}
const handleFileRemove = () => {
  reusedImagePath.value = ''
  fileList.value = []
}
const goToDetail = (id: number) => router.push(`/testcase/result/${id}`)
const formatDate = (str: string) => str ? dayjs(str).format('MM-DD HH:mm') : '-'

onMounted(() => {
  fetchActiveModel()
  fetchRecords()
  loadAvailableSkills()
  loadAvailableRuleSets()
  loadAvailableRules()
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

.left-panel { width: 420px; flex-shrink: 0; display: flex; flex-direction: column; }
.right-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.panel-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 头部样式优化，防止遮挡 */
.panel-header {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  gap: 10px;
}
.title { font-weight: 600; font-size: 15px; color: #1f2937; white-space: nowrap; }

.status-tag {
  height: auto !important; /* 关键：高度自适应 */
  padding: 6px 10px;
  max-width: 75%;
  flex-shrink: 0; /* 关键：不被挤压 */
}
.tag-content {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: normal; /* 关键：允许换行 */
  line-height: 1.2;
}
.sub-text { font-size: 11px; opacity: 0.85; margin-left: 4px; }

.panel-body { padding: 20px; flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 20px; }
.table-body { padding: 0; }

.req-input :deep(.el-textarea__inner) { padding: 12px; font-size: 14px; }

.upload-section { background: #fafafa; border: 1px dashed #d9d9d9; border-radius: 6px; padding: 16px; }
.upload-header { margin-bottom: 12px; font-size: 13px; color: #606266; }
.upload-desc { margin-top: 8px; font-size: 12px; color: #909399; }
.reuse-tag { color: #409eff; background: #ecf5ff; padding: 2px 6px; border-radius: 4px; }

/* 不支持上传时的样式 */
.unsupported-box {
  background: #fdf6ec;
  border: 1px dashed #e6a23c;
  border-radius: 6px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #e6a23c;
  text-align: center;
  height: 100px;
}
.unsupported-box .icon { font-size: 24px; margin-bottom: 8px; }
.unsupported-box .text { font-size: 13px; line-height: 1.5; }
.unsupported-box .sub { font-size: 11px; opacity: 0.8; }

.generate-btn { width: 100%; height: 40px; font-size: 15px; letter-spacing: 1px; }
.hide-upload-btn :deep(.el-upload--picture-card) { display: none; }
.rule-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 4px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.text-truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #606266; font-size: 13px; }
.time-text { font-size: 12px; color: #909399; font-family: monospace; }
.text-gray { color: #dcdfe6; }
:deep(.el-table .cell) { padding: 8px 8px; }
</style>