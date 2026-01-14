<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">系统用户管理</div>
      <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新增用户</el-button>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table :data="userList" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" class-name="text-gray" />

        <el-table-column prop="username" label="用户名">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="28" class="mr-2">{{ row.username.charAt(0).toUpperCase() }}</el-avatar>
              <span class="font-medium">{{ row.username }}</span>
              <el-tag v-if="row.username === 'admin'" size="small" type="danger" class="ml-2">管理员</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="注册时间" width="200">
          <template #default>2024-01-01</template> </el-table-column>

        <el-table-column label="操作" width="120" fixed="right" align="right">
          <template #default="{ row }">
            <el-popconfirm
              title="确定要删除该用户吗?"
              @confirm="handleDelete(row.id)"
              confirm-button-type="danger"
            >
              <template #reference>
                <el-button
                  type="danger"
                  link
                  :disabled="row.username === 'admin'"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增用户" width="400px" destroy-on-close>
      <el-form :model="form" label-width="80px" @submit.prevent class="pt-4">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const userList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const creating = ref(false)
const form = reactive({ username: '', password: '' })

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await axios.get('/users/')
    userList.value = res.data
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

const handleCreate = async () => {
  if (!form.username || !form.password) return ElMessage.warning('请填写完整信息')
  creating.value = true
  try {
    await axios.post('/users/', form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    form.username = ''; form.password = ''
    fetchUsers()
  } catch (error: any) {
    if (error.response?.status === 400) ElMessage.error('该用户名已存在')
    else ElMessage.error('创建失败')
  } finally { creating.value = false }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/users/${id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch { ElMessage.error('删除失败') }
}

onMounted(fetchUsers)
</script>

<style scoped>
.page-container { max-width: 1000px; margin: 0 auto; padding-top: 20px; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 8px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.title { font-size: 16px; font-weight: 600; color: #1f2937; }
.table-card { border: none; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); }

.user-cell { display: flex; align-items: center; }
.mr-2 { margin-right: 8px; }
.ml-2 { margin-left: 8px; }
.text-gray { color: #9ca3af; font-family: monospace; }
.font-medium { font-weight: 500; }
.pt-4 { padding-top: 10px; }
</style>