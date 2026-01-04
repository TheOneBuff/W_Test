<template>
  <div class="menu-manage">
    <div class="header-actions">
      <el-button type="primary" @click="openDialog()">
        <el-icon class="mr-1"><Plus /></el-icon> 新增根菜单
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table
        :data="menuList"
        style="width: 100%; margin-bottom: 20px;"
        row-key="id"
        border
        default-expand-all
      >
        <el-table-column prop="title" label="菜单名称" sortable width="200" />
        <el-table-column prop="icon" label="图标" width="100">
          <template #default="scope">
            <el-icon v-if="scope.row.icon">
              <component :is="scope.row.icon" />
            </el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路由路径" />
        <el-table-column prop="component" label="组件/标识" />
        <el-table-column prop="sort" label="排序" width="80" />

        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="openDialog(scope.row.id)">
              添加子菜单
            </el-button>
            <el-popconfirm title="确定删除?" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                 <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.parent_id ? '添加子菜单' : '添加根菜单'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="菜单名称">
          <el-input v-model="form.title" placeholder="例如：用户管理" />
        </el-form-item>
        <el-form-item label="路由路径">
          <el-input v-model="form.path" placeholder="例如：/users (父菜单可留空)" />
        </el-form-item>
        <el-form-item label="组件标识">
          <el-input v-model="form.component" placeholder="例如：UserManage (父菜单可留空)" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="例如：User (Element Plus Icon Name)" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" />
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

const menuList = ref([])
const dialogVisible = ref(false)
const form = reactive({
  title: '',
  path: '',
  component: '',
  icon: '',
  sort: 0,
  parent_id: null as number | null
})

const fetchMenus = async () => {
  const res = await axios.get('/menus/')
  menuList.value = res.data
}

const openDialog = (parentId: number | null = null) => {
  form.title = ''
  form.path = ''
  form.component = ''
  form.icon = ''
  form.sort = 0
  form.parent_id = parentId
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await axios.post('/menus/', form)
    ElMessage.success('添加成功')
    dialogVisible.value = false
    fetchMenus()
  } catch(e) {
    ElMessage.error('失败')
  }
}

const handleDelete = async (id: number) => {
  await axios.delete(`/menus/${id}`)
  fetchMenus()
}

onMounted(fetchMenus)
</script>

<style scoped>
.menu-manage { padding: 20px; }
.header-actions { margin-bottom: 20px; }
.mr-1 { margin-right: 5px; }
</style>
