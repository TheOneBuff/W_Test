<template>
  <div class="user-manage">
    <!-- 修改点 1: 添加 :icon="null" 隐藏左侧的返回箭头 -->
    <el-page-header :icon="null" title="" style="margin-bottom: 20px;">
      <template #content>
        <span class="text-large font-600 mr-3">用户管理</span>
      </template>

      <!-- 右侧的操作按钮 -->
      <template #extra>
        <el-button type="primary" @click="dialogVisible = true">
          <el-icon style="margin-right: 5px"><Plus /></el-icon> 新增用户
        </el-button>
      </template>
    </el-page-header>

    <!-- 用户列表表格 -->
    <el-card shadow="never">
      <el-table :data="userList" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-popconfirm
              title="确定要删除该用户吗?"
              @confirm="handleDelete(scope.row.id)"
              confirm-button-type="danger"
            >
              <template #reference>
                <el-button
                  type="danger"
                  size="small"
                  link
                  :disabled="scope.row.username === 'admin'"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增用户" width="400px" destroy-on-close>
      <el-form :model="form" label-width="80px" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreate" :loading="creating">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

// const router = useRouter() // 删除 router 初始化

// --- 以下业务逻辑保持不变 ---
const userList = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const creating = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await axios.get('/users/')
    userList.value = res.data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写完整信息')
    return
  }

  creating.value = true
  try {
    await axios.post('/users/', form)
    ElMessage.success('用户创建成功')
    dialogVisible.value = false
    form.username = ''
    form.password = ''
    fetchUsers()
  } catch (error: any) {
    if (error.response?.status === 400) {
      ElMessage.error('该用户名已存在')
    }
  } finally {
    creating.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/users/${id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-manage {
  padding: 20px;
  background-color: #fff;
  min-height: 100%;
}
</style>
