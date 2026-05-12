<template>
  <div class="skill-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>技能管理</span>
          <div>
            <el-button type="primary" @click="handleSeedDefaults">初始化默认技能</el-button>
            <el-button type="primary" @click="handleCreate">新建技能</el-button>
          </div>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="技能类型">
          <el-select v-model="filters.skill_type" placeholder="全部" clearable style="width: 150px">
            <el-option label="通用" value="general" />
            <el-option label="图片" value="image" />
            <el-option label="文本" value="text" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.is_active" placeholder="全部" clearable style="width: 120px">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadSkills">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="skills" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="技能名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="skill_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getSkillTypeTag(row.skill_type)">
              {{ getSkillTypeLabel(row.skill_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" @click="handleView(row)">查看</el-button>
              <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button size="small" :type="row.is_active ? 'warning' : 'success'" @click="handleToggle(row)">
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="70%"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="技能名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入技能名称" />
        </el-form-item>
        <el-form-item label="技能描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入技能描述" />
        </el-form-item>
        <el-form-item label="技能类型" prop="skill_type">
          <el-radio-group v-model="form.skill_type">
            <el-radio label="general">通用</el-radio>
            <el-radio label="image">图片</el-radio>
            <el-radio label="text">文本</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="提示词内容" prop="prompt_content">
          <el-input
            v-model="form.prompt_content"
            type="textarea"
            :rows="15"
            placeholder="请输入提示词内容（支持 Markdown 格式）"
            style="font-family: monospace"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="viewDialogVisible"
      title="技能详情"
      width="70%"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="技能名称">{{ viewSkill?.name }}</el-descriptions-item>
        <el-descriptions-item label="技能类型">
          <el-tag :type="getSkillTypeTag(viewSkill?.skill_type)">
            {{ getSkillTypeLabel(viewSkill?.skill_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="viewSkill?.is_active ? 'success' : 'info'">
            {{ viewSkill?.is_active ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(viewSkill?.create_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          {{ viewSkill?.description || '无' }}
        </el-descriptions-item>
      </el-descriptions>
      
      <el-divider>提示词内容</el-divider>
      <pre class="prompt-content">{{ viewSkill?.prompt_content }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import * as api from '../api/skills'
import type { Skill, SkillCreate, SkillUpdate } from '../api/skills'

const loading = ref(false)
const submitting = ref(false)
const skills = ref<Skill[]>([])
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref<FormInstance>()
const viewSkill = ref<Skill | null>(null)

const filters = reactive({
  skill_type: '',
  is_active: undefined as boolean | undefined
})

interface SkillFormData extends SkillCreate {
  id?: number
}

const form = reactive<SkillFormData>({
  name: '',
  description: '',
  prompt_content: '',
  skill_type: 'general',
  is_active: true
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入技能名称', trigger: 'blur' }],
  prompt_content: [{ required: true, message: '请输入提示词内容', trigger: 'blur' }],
  skill_type: [{ required: true, message: '请选择技能类型', trigger: 'change' }]
}

const loadSkills = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filters.skill_type) params.skill_type = filters.skill_type
    if (filters.is_active !== undefined) params.is_active = filters.is_active
    
    const res = await api.getSkills(params)
    skills.value = res.data || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogTitle.value = '新建技能'
  Object.assign(form, {
    name: '',
    description: '',
    prompt_content: '',
    skill_type: 'general',
    is_active: true
  })
  dialogVisible.value = true
}

const handleEdit = (row: Skill) => {
  dialogTitle.value = '编辑技能'
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    prompt_content: row.prompt_content,
    skill_type: row.skill_type,
    is_active: row.is_active
  })
  form.id = row.id
  dialogVisible.value = true
}

const handleView = async (row: Skill) => {
  try {
    const res = await api.getSkill(row.id)
    viewSkill.value = res.data
    viewDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.message || '加载详情失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (form.id) {
          const updateData: SkillUpdate = {
            name: form.name,
            description: form.description,
            prompt_content: form.prompt_content,
            skill_type: form.skill_type,
            is_active: form.is_active
          }
          await api.updateSkill(form.id, updateData)
          ElMessage.success('更新成功')
        } else {
          const createData: SkillCreate = {
            name: form.name,
            description: form.description,
            prompt_content: form.prompt_content,
            skill_type: form.skill_type,
            is_active: form.is_active
          }
          await api.createSkill(createData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadSkills()
      } catch (error: any) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleToggle = async (row: Skill) => {
  try {
    await api.toggleSkill(row.id)
    ElMessage.success(row.is_active ? '已禁用' : '已启用')
    loadSkills()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

const handleDelete = async (row: Skill) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除技能"${row.name}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.deleteSkill(row.id)
    ElMessage.success('删除成功')
    loadSkills()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleSeedDefaults = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要初始化默认技能吗？这将创建两个默认的技能模板。',
      '初始化确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    const res = await api.seedDefaultSkills()
    ElMessage.success(res.data?.message || '初始化成功')
    loadSkills()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '初始化失败')
    }
  }
}

const getSkillTypeLabel = (type: string | undefined) => {
  const map: Record<string, string> = {
    general: '通用',
    image: '图片',
    text: '文本'
  }
  return type ? (map[type] || type) : ''
}

const getSkillTypeTag = (type: string | undefined) => {
  const map: Record<string, string> = {
    general: '',
    image: 'success',
    text: 'warning'
  }
  return type ? (map[type] || '') : ''
}

const formatDate = (date: string | undefined) => {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSkills()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prompt-content {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

.action-buttons {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
}
</style>
