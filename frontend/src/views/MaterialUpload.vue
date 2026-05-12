<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">{{ currentCategory === 'pc' ? 'PC素材管理' : 'Web素材管理' }}</div>
      <div class="category-tabs">
        <el-radio-group v-model="currentCategory" @change="handleCategoryChange" size="small">
          <el-radio-button label="web">Web素材</el-radio-button>
          <el-radio-button label="pc">PC素材</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <el-card shadow="never" class="upload-card">
      <template #header>
        <div class="card-header">
          <span>上传素材</span>
        </div>
      </template>
      
      <el-form :model="form" label-width="100px" class="upload-form">
        <el-form-item label="素材名称" required>
          <el-input v-model="form.name" placeholder="请输入素材名称" />
        </el-form-item>
        
        <el-form-item label="所属项目">
          <el-select v-model="form.project_id" placeholder="选择项目" clearable>
            <el-option v-for="project in projectList" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="选择文件" required>
          <el-upload
            class="upload-demo"
            :action="''"
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
            :accept="'image/*'"
            :limit="1"
          >
            <el-button type="primary" :icon="Upload">选择图片</el-button>
            <template #tip>
              <div class="el-upload__tip">
                请上传图片文件（支持 JPG、PNG、GIF 等格式）
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            {{ uploading ? '上传中...' : '开始上传' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="list-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>素材列表</span>
          <el-select v-model="filterProjectId" placeholder="按项目筛选" clearable class="filter-select">
            <el-option v-for="project in projectList" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </div>
      </template>
      
      <el-table :data="materialList" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="素材名称" min-width="180" />
        <el-table-column label="预览" width="120" align="center">
          <template #default="{ row }">
            <el-image
              :src="getMaterialUrl(row.file_path)"
              :preview-src-list="[getMaterialUrl(row.file_path)]"
              fit="cover"
              class="material-preview"
            />
          </template>
        </el-table-column>
        <el-table-column prop="file_path" label="文件路径" min-width="300">
          <template #default="{ row }">
            <span class="file-path">{{ row.file_path }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="文件类型" width="120" />
        <el-table-column prop="file_size" label="文件大小" width="100" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="上传时间" width="180" />
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="danger" link @click="handleDelete(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'

const currentCategory = ref('web')

const handleCategoryChange = (val: string) => {
  currentCategory.value = val
  fetchMaterials()
}

const form = reactive({
  name: '',
  project_id: null as number | null
})

const fileList = ref<any[]>([])
const uploading = ref(false)
const projectList = ref<any[]>([])
const materialList = ref<any[]>([])
const filterProjectId = ref<number | null>(null)

// 获取项目列表
const fetchProjects = async () => {
  try {
    const res = await axios.get('/projects/')
    projectList.value = res.data
  } catch (e) {
    console.error(e)
  }
}

// 获取素材列表（根据当前分类筛选）
const fetchMaterials = async () => {
  try {
    const params: any = {}
    if (filterProjectId.value) {
      params.project_id = filterProjectId.value
    }
    params.category = currentCategory.value
    
    const res = await axios.get('/materials/', { params })
    materialList.value = res.data
  } catch (e) {
    console.error(e)
  }
}

// 处理文件选择
const handleFileChange = (file: any) => {
  fileList.value = [file]
}

// 处理上传
const handleUpload = async () => {
  if (!form.name) {
    return ElMessage.warning('请输入素材名称')
  }
  
  if (fileList.value.length === 0) {
    return ElMessage.warning('请选择文件')
  }
  
  const file = fileList.value[0].raw
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('name', form.name)
  if (form.project_id) {
    formData.append('project_id', form.project_id.toString())
  }
  formData.append('category', currentCategory.value)
  
  uploading.value = true
  
  try {
    await axios.post('/materials/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    ElMessage.success('上传成功')
    
    // 重置表单
    form.name = ''
    form.project_id = null
    fileList.value = []
    
    // 刷新素材列表
    await fetchMaterials()
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 处理删除
const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/materials/${id}`)
    ElMessage.success('删除成功')
    await fetchMaterials()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 获取素材 URL
const getMaterialUrl = (filePath: string) => {
  return filePath.replace('/data/uploads', '/uploads')
}

// 格式化文件大小
const formatFileSize = (size: number) => {
  if (size < 1024) {
    return size + ' B'
  } else if (size < 1024 * 1024) {
    return (size / 1024).toFixed(2) + ' KB'
  } else {
    return (size / (1024 * 1024)).toFixed(2) + ' MB'
  }
}

onMounted(async () => {
  await fetchProjects()
  await fetchMaterials()
})
</script>

<style scoped>
.page-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-top: 20px;
}

.toolbar-card {
  background: #fff;
  padding: 16px 24px;
  border-radius: 8px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.category-tabs {
  display: flex;
  gap: 8px;
}

.upload-card,
.list-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  color: #333;
}

.upload-form {
  padding: 20px 0;
}

.filter-select {
  width: 200px;
}

.material-preview {
  width: 80px;
  height: 60px;
  border-radius: 4px;
}

.el-upload__tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.file-path {
  font-family: monospace;
  font-size: 12px;
  color: #666;
  word-break: break-all;
}
</style>
