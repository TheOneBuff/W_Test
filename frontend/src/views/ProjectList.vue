<template>
  <div class="page-container">
    <div class="toolbar-card">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索项目名称..."
        style="width: 300px"
        prefix-icon="Search"
        clearable
      />
      <el-button type="primary" @click="openDialog()" :icon="Plus">新建项目</el-button>
    </div>

    <el-row :gutter="24" v-if="filteredList.length > 0">
      <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="item in filteredList" :key="item.id">
        <el-card class="project-card" shadow="hover" :body-style="{ padding: '20px' }">
          <div class="card-header">
            <div class="icon-box">{{ item.name.charAt(0).toUpperCase() }}</div>
            <div class="actions">
              <el-dropdown trigger="click" @command="(cmd: any) => handleCommand(cmd, item)">
                <el-icon class="more-btn"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="delete" :icon="Delete" style="color: #ef4444">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <h3 class="project-title">{{ item.name }}</h3>
          <p class="project-desc">{{ item.description || '暂无描述信息...' }}</p>

          <div class="project-footer">
            <span class="time">{{ formatDate(item.create_time) }}</span>
            <el-link type="primary" :underline="false" @click="handleEnter(item)">进入项目 <el-icon><ArrowRight /></el-icon></el-link>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-else description="暂无项目，快去创建一个吧！" :image-size="120" />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑项目' : '新建项目'" width="480px" destroy-on-close>
      <el-form :model="form" label-width="80px" label-position="top">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="简要描述项目用途..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from '@/utils/request'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, MoreFilled, Edit, Delete, ArrowRight } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const list = ref<any[]>([])
const searchKeyword = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)

const form = reactive({ id: null, name: '', description: '' })

const filteredList = computed(() => {
  if (!searchKeyword.value) return list.value
  return list.value.filter(item => item.name.toLowerCase().includes(searchKeyword.value.toLowerCase()))
})

const fetchProjects = async () => {
  const res = await axios.get('/projects/')
  list.value = res.data
}

const openDialog = (item?: any) => {
  if (item) {
    form.id = item.id
    form.name = item.name
    form.description = item.description
  } else {
    form.id = null
    form.name = ''
    form.description = ''
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.name) return ElMessage.warning('请输入名称')
  submitting.value = true
  try {
    if (form.id) await axios.put(`/projects/${form.id}`, form)
    else await axios.post('/projects/', form)
    ElMessage.success('操作成功')
    dialogVisible.value = false
    fetchProjects()
  } finally { submitting.value = false }
}

const handleCommand = (cmd: string, item: any) => {
  if (cmd === 'edit') openDialog(item)
  else if (cmd === 'delete') {
    ElMessageBox.confirm('确定删除该项目及其下所有用例吗?', '删除警告', {
      type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger'
    }).then(async () => {
      await axios.delete(`/projects/${item.id}`)
      ElMessage.success('已删除')
      fetchProjects()
    })
  }
}

const handleEnter = (item: any) => {
  // 可以在这里跳转到用例列表并自动筛选
  router.push({ path: '/testcases', query: { project_id: item.id } })
}

const formatDate = (str: string) => dayjs(str).format('YY/MM/DD')

onMounted(fetchProjects)
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 12px; margin-bottom: 24px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}

.project-card {
  border: none; border-radius: 12px; margin-bottom: 24px; position: relative;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px 0 rgba(0,0,0,0.05);
}
.project-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px -5px rgba(0,0,0,0.1); }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.icon-box {
  width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 12px; color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: bold;
}
.more-btn { transform: rotate(90deg); color: #9ca3af; cursor: pointer; font-size: 18px; }

.project-title { font-size: 18px; font-weight: 600; color: #111827; margin: 0 0 8px 0; }
.project-desc { font-size: 14px; color: #6b7280; line-height: 1.5; height: 42px; overflow: hidden; margin-bottom: 20px; }

.project-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f3f4f6; padding-top: 16px; }
.time { font-size: 13px; color: #9ca3af; }
</style>