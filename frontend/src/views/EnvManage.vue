<template>
  <div class="env-manage">
    <div class="header-actions">
      <el-button type="primary" @click="openDialog()">
        <el-icon class="mr-1"><Plus /></el-icon> 新建环境
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="环境名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="变量预览" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.variables }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑环境' : '新建环境'" width="600px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="例如：Test Env" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="变量配置">
          <div class="json-editor-tip">请输入 JSON 格式，例如: {"BASE_URL": "http://..."}</div>
          <el-input
            v-model="form.variables"
            type="textarea"
            :rows="10"
            placeholder='{ "KEY": "VALUE" }'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const list = ref([])
const dialogVisible = ref(false)
const form = reactive({ id: null, name: '', description: '', variables: '{}' })

const fetchList = async () => {
  const res = await axios.get('/envs/')
  list.value = res.data
}

const openDialog = (row?: any) => {
  if (row) {
    Object.assign(form, row)
  } else {
    form.id = null
    form.name = ''
    form.description = ''
    form.variables = '{\n  "BASE_URL": "https://example.com"\n}'
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    // 简单校验 JSON
    JSON.parse(form.variables)
  } catch {
    return ElMessage.error('变量格式必须是合法的 JSON')
  }

  try {
    if (form.id) await axios.put(`/envs/${form.id}`, form)
    else await axios.post('/envs/', form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
  } catch(e) {
    ElMessage.error('保存失败')
  }
}

const handleDelete = async (id: number) => {
  await axios.delete(`/envs/${id}`)
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.env-manage { padding: 20px; }
.json-editor-tip { font-size: 12px; color: #999; margin-bottom: 5px; }
</style>
