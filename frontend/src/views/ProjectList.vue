<template>
  <div class="project-list">
    <div class="header-actions">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索项目名称..."
        style="width: 250px"
        prefix-icon="Search"
        clearable
      />
      <el-button type="primary" @click="openDialog()">
        <el-icon class="mr-1"><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="item in filteredList" :key="item.id">
        <el-card class="project-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="title">{{ item.name }}</span>
              <el-dropdown trigger="click" @command="(cmd: any) => handleCommand(cmd, item)">
                <el-icon class="more-btn"><More /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="delete" style="color: red">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
          <div class="card-body">
            <p class="desc">{{ item.description || '暂无描述' }}</p>
            <div class="meta">
              <span class="time">{{ formatDate(item.create_time) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="filteredList.length === 0" description="暂无项目" />

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑项目' : '新建项目'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, More } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const list = ref<any[]>([])
const searchKeyword = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)

const form = reactive({
  id: null,
  name: '',
  description: ''
})

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
    if (form.id) {
      await axios.put(`/projects/${form.id}`, form)
    } else {
      await axios.post('/projects/', form)
    }
    ElMessage.success('操作成功')
    dialogVisible.value = false
    fetchProjects()
  } finally {
    submitting.value = false
  }
}

const handleCommand = (cmd: string, item: any) => {
  if (cmd === 'edit') {
    openDialog(item)
  } else if (cmd === 'delete') {
    ElMessageBox.confirm('确定删除该项目及其下所有用例吗?', '警告', {
      type: 'warning',
      confirmButtonText: '删除',
      confirmButtonClass: 'el-button--danger'
    }).then(async () => {
      await axios.delete(`/projects/${item.id}`)
      ElMessage.success('已删除')
      fetchProjects()
    })
  }
}

const formatDate = (str: string) => dayjs(str).format('YYYY-MM-DD HH:mm')

onMounted(fetchProjects)
</script>

<style scoped>
.project-list { padding: 20px; }
.header-actions { display: flex; justify-content: space-between; margin-bottom: 20px; }
.project-card { margin-bottom: 20px; transition: all 0.3s; }
.project-card:hover { transform: translateY(-5px); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: bold; font-size: 16px; }
.more-btn { cursor: pointer; transform: rotate(90deg); }
.card-body { height: 80px; display: flex; flex-direction: column; justify-content: space-between; }
.desc { color: #666; font-size: 14px; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.meta { font-size: 12px; color: #999; text-align: right; }
</style>
