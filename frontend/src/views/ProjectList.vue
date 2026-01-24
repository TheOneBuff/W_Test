<template>
  <div class="page-container">
    <div class="toolbar-section">
      <div class="search-wrapper">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索项目..."
          class="custom-search"
          prefix-icon="Search"
          clearable
        />
      </div>
      <el-button type="primary" @click="openDialog()" class="create-btn" :icon="Plus">
        创建新项目
      </el-button>
    </div>

    <div v-if="filteredList.length > 0" class="project-grid">
      <div 
        v-for="(item, index) in filteredList" 
        :key="item.id" 
        class="project-card"
        @click="handleEnter(item)"
      >
        <div class="card-header">
          <div class="project-icon" :class="getGradientClass(index)">
            {{ item.name.charAt(0).toUpperCase() }}
          </div>
          <div class="actions" @click.stop>
            <el-dropdown trigger="click" @command="(cmd: any) => handleCommand(cmd, item)">
              <div class="more-btn-wrapper">
                <el-icon><MoreFilled /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu class="custom-dropdown">
                  <el-dropdown-item command="edit" :icon="Edit">编辑项目</el-dropdown-item>
                  <el-dropdown-item command="delete" :icon="Delete" style="color: #ef4444">删除项目</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="card-content">
          <h3 class="project-title">{{ item.name }}</h3>
          <p class="project-desc">{{ item.description || '暂无描述信息...' }}</p>
        </div>

        <div class="card-footer">
          <div class="meta-tag">
            <el-icon><Clock /></el-icon>
            <span>{{ formatDate(item.create_time) }}</span>
          </div>
          <div class="enter-hint">
            进入 <el-icon><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-wrapper">
      <el-empty description="暂无项目数据" :image-size="160">
        <el-button type="primary" @click="openDialog()">立即创建</el-button>
      </el-empty>
    </div>

    <el-dialog 
      v-model="dialogVisible" 
      :title="form.id ? '编辑项目' : '新建项目'" 
      width="480px" 
      align-center
      destroy-on-close
      class="custom-dialog"
    >
      <el-form :model="form" label-position="top" size="large">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="例如：电商后台自动化测试" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="4" 
            resize="none"
            placeholder="简要描述项目的测试范围和用途..." 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false" class="cancel-btn">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">确认保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from '@/utils/request'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, MoreFilled, Edit, Delete, ArrowRight, Clock } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const list = ref<any[]>([])
const searchKeyword = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)

const form = reactive({ id: null, name: '', description: '' })

// 预定义几种渐变色类名，用于随机分配给项目图标
const gradientClasses = ['gradient-blue', 'gradient-purple', 'gradient-green', 'gradient-orange', 'gradient-pink']
const getGradientClass = (index: number) => gradientClasses[index % gradientClasses.length]

const filteredList = computed(() => {
  if (!searchKeyword.value) return list.value
  return list.value.filter(item => item.name.toLowerCase().includes(searchKeyword.value.toLowerCase()))
})

const fetchProjects = async () => {
  try {
    const res = await axios.get('/projects/')
    list.value = res.data
  } catch (e) {
    console.error(e)
  }
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
  if (!form.name) return ElMessage.warning('请输入项目名称')
  submitting.value = true
  try {
    if (form.id) await axios.put(`/projects/${form.id}`, form)
    else await axios.post('/projects/', form)
    ElMessage.success('操作成功')
    dialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

const handleCommand = (cmd: string, item: any) => {
  if (cmd === 'edit') openDialog(item)
  else if (cmd === 'delete') {
    ElMessageBox.confirm('确定删除该项目及其下所有数据吗? 此操作不可恢复。', '删除警告', {
      type: 'warning',
      confirmButtonText: '确定删除',
      confirmButtonClass: 'el-button--danger',
      cancelButtonText: '取消',
      title: '删除警告'
    }).then(async () => {
      await axios.delete(`/projects/${item.id}`)
      ElMessage.success('已删除')
      fetchProjects()
    })
  }
}

const handleEnter = (item: any) => {
  router.push({ path: '/testcases', query: { project_id: item.id } })
}

const formatDate = (str: string) => dayjs(str).format('YYYY-MM-DD')

onMounted(fetchProjects)
</script>

<style scoped>
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

/* 顶部工具栏 */
.toolbar-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  gap: 16px;
}

.search-wrapper {
  flex: 1;
  max-width: 400px;
}

:deep(.custom-search .el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
  border: 1px solid transparent;
  background: #fff;
  transition: all 0.3s;
  padding: 4px 12px;
}
:deep(.custom-search .el-input__wrapper:hover),
:deep(.custom-search .el-input__wrapper.is-focus) {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  border-color: var(--primary-light, #e0e7ff);
}

.create-btn {
  height: 42px;
  padding: 0 24px;
  border-radius: 10px;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
}

/* Grid 布局 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

/* 项目卡片 */
.project-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #f1f5f9;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  cursor: pointer;
  height: 220px; /* 固定高度保持整齐 */
}

.project-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 24px -8px rgba(0,0,0,0.1);
  border-color: transparent;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.project-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

/* 随机渐变色 */
.gradient-blue { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
.gradient-purple { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
.gradient-green { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.gradient-orange { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.gradient-pink { background: linear-gradient(135deg, #ec4899 0%, #db2777 100%); }

.more-btn-wrapper {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #94a3b8;
  transition: all 0.2s;
}
.more-btn-wrapper:hover {
  background: #f1f5f9;
  color: #334155;
}

/* 卡片内容 */
.card-content {
  flex: 1;
}

.project-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 42px;
}

/* 卡片底部 */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #f8fafc;
  margin-top: auto;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.enter-hint {
  font-size: 13px;
  color: #3b82f6;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transform: translateX(-10px);
  transition: all 0.3s ease;
}

.project-card:hover .enter-hint {
  opacity: 1;
  transform: translateX(0);
}

.empty-wrapper {
  margin-top: 80px;
}

/* 对话框微调 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.cancel-btn {
  border: none;
  background: #f1f5f9;
  color: #64748b;
}
.cancel-btn:hover {
  background: #e2e8f0;
}
</style>