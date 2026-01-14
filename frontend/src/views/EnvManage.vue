<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">环境配置列表</div>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新建环境</el-button>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table :data="list" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" class-name="text-gray" />

        <el-table-column prop="name" label="环境名称" width="200">
          <template #default="{ row }">
            <span class="font-medium">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />

        <el-table-column label="变量配置" width="120">
          <template #default="{ row }">
            <el-popover placement="top" width="300" trigger="hover">
              <template #reference>
                <el-tag type="info" size="small" class="cursor-pointer">查看 JSON</el-tag>
              </template>
              <pre class="json-preview">{{ formatJson(row.variables) }}</pre>
            </el-popover>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-divider direction="vertical" />
            <el-popconfirm title="确定删除该环境?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑环境' : '新建环境'" width="550px" destroy-on-close>
      <el-form :model="form" label-width="80px" label-position="top">
        <el-form-item label="环境名称" required>
          <el-input v-model="form.name" placeholder="例如：Staging / Production" />
        </el-form-item>
        <el-form-item label="描述信息">
          <el-input v-model="form.description" placeholder="该环境的用途说明..." />
        </el-form-item>
        <el-form-item label="环境变量 (JSON)">
          <div class="code-editor-wrapper">
            <el-input
              v-model="form.variables"
              type="textarea"
              :rows="8"
              placeholder='{ "BASE_URL": "https://..." }'
              class="code-input"
            />
          </div>
          <div class="form-tip">请输入合法的 JSON 格式，例如: {"KEY": "VALUE"}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
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
    JSON.parse(form.variables)
  } catch {
    return ElMessage.error('变量格式错误：必须是合法的 JSON')
  }

  try {
    if (form.id) await axios.put(`/envs/${form.id}`, form)
    else await axios.post('/envs/', form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
  } catch(e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/envs/${id}`)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) { ElMessage.error('删除失败') }
}

const formatJson = (str: string) => {
  try { return JSON.stringify(JSON.parse(str), null, 2) } catch { return str }
}

onMounted(fetchList)
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 8px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.toolbar-card .title { font-size: 16px; font-weight: 600; color: #1f2937; }

.table-card { border: none; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); overflow: hidden; }
.text-gray { color: #9ca3af; font-family: monospace; }
.font-medium { font-weight: 500; }
.cursor-pointer { cursor: pointer; }

.json-preview { font-family: monospace; font-size: 12px; margin: 0; white-space: pre-wrap; color: #4b5563; }
.form-tip { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.code-editor-wrapper { border: 1px solid #dcdfe6; border-radius: 4px; overflow: hidden; }
:deep(.el-textarea__inner) { box-shadow: none; border: none; background: #f9fafb; font-family: monospace; }
</style>