<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title">菜单路由配置</div>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新增根菜单</el-button>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table
        :data="menuList"
        style="width: 100%"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
      >
        <el-table-column prop="title" label="菜单名称" width="220">
          <template #default="{ row }">
            <span class="font-medium">{{ row.title }}</span>
          </template>
        </el-table-column>

        <el-table-column label="图标" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.icon" :size="16" class="v-align">
              <component :is="row.icon" />
            </el-icon>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="path" label="路由路径" min-width="150">
          <template #default="{ row }">
            <el-tag size="small" type="info" class="font-mono">{{ row.path }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="component" label="组件标识" min-width="150">
          <template #default="{ row }">
             <span v-if="row.component" class="text-gray font-mono">{{ row.component }}</span>
             <span v-else class="text-gray italic">Layout</span>
          </template>
        </el-table-column>

        <el-table-column prop="sort" label="排序" width="80" align="center" />

        <el-table-column label="操作" width="180" align="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" :icon="Plus" @click="openDialog(row.id)">
              子菜单
            </el-button>
            <el-divider direction="vertical" />
            <el-popconfirm title="确定删除该菜单及其子菜单?" @confirm="handleDelete(row.id)">
              <template #reference>
                 <el-button size="small" link type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.parent_id ? '添加子菜单' : '添加根菜单'" width="480px" destroy-on-close>
      <el-form :model="form" label-width="90px" class="pt-2">
        <el-form-item label="菜单名称" required>
          <el-input v-model="form.title" placeholder="例如：用户管理" />
        </el-form-item>
        <el-form-item label="路由路径">
          <el-input v-model="form.path" placeholder="/users (父级可留空)" />
        </el-form-item>
        <el-form-item label="组件标识">
          <el-input v-model="form.component" placeholder="View组件名 (父级可留空)" />
        </el-form-item>
        <el-form-item label="图标名称">
          <el-input v-model="form.icon" placeholder="Element Plus Icon (如 User)" />
        </el-form-item>
        <el-form-item label="显示排序">
          <el-input-number v-model="form.sort" :min="0" controls-position="right" />
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
import { Plus, Delete } from '@element-plus/icons-vue'

const menuList = ref([])
const dialogVisible = ref(false)
const form = reactive({ title: '', path: '', component: '', icon: '', sort: 0, parent_id: null as number | null })

const fetchMenus = async () => {
  const res = await axios.get('/menus/')
  menuList.value = res.data
}

const openDialog = (parentId: number | null = null) => {
  Object.assign(form, { title: '', path: '', component: '', icon: '', sort: 0, parent_id: parentId })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await axios.post('/menus/', form)
    ElMessage.success('添加成功')
    dialogVisible.value = false
    fetchMenus()
  } catch(e) { ElMessage.error('失败') }
}

const handleDelete = async (id: number) => {
  try { await axios.delete(`/menus/${id}`); fetchMenus(); ElMessage.success('已删除') } catch(e) {}
}

onMounted(fetchMenus)
</script>

<style scoped>
.page-container { max-width: 1000px; margin: 0 auto; padding-top: 20px; }
.toolbar-card {
  background: #fff; padding: 16px 24px; border-radius: 8px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.title { font-size: 16px; font-weight: 600; color: #1f2937; }
.table-card { border: none; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); overflow: hidden; }

.font-medium { font-weight: 500; }
.font-mono { font-family: monospace; }
.text-gray { color: #9ca3af; }
.italic { font-style: italic; }
.v-align { vertical-align: middle; }
.pt-2 { padding-top: 8px; }
</style>