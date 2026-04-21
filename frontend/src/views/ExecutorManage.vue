<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="filter-group">
        <el-radio-group v-model="filterStatus" @change="handleFilterChange" size="default">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="online">在线</el-radio-button>
          <el-radio-button label="offline">离线</el-radio-button>
          <el-radio-button label="busy">忙碌</el-radio-button>
        </el-radio-group>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索名称/主机名..."
          prefix-icon="Search"
          clearable
          style="width: 240px; margin-left: 16px"
          @input="handleSearch"
        />
      </div>
      <div class="action-group">
        <el-button type="primary" :icon="Refresh" @click="fetchList" :loading="loading">
          刷新列表
        </el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card" :body-style="{ padding: '0' }">
      <el-table
        :data="list"
        v-loading="loading"
        style="width: 100%"
        :header-cell-style="{ background: '#f9fafb', color: '#374151', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center">
          <template #default="{ row }">
            <span class="text-gray">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="执行器名称" min-width="180">
          <template #default="{ row }">
            <div class="executor-name">
              <el-icon :size="20" class="host-icon"><Monitor /></el-icon>
              <span class="name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <div class="status-badge" :class="row.status">
              <span class="dot"></span>
              {{ statusText[row.status] || row.status }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="version" label="版本" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ row.version || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP地址" width="140">
          <template #default="{ row }">
            <span class="ip-text">{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="hostname" label="主机名" min-width="150">
          <template #default="{ row }">
            <span class="hostname-text">{{ row.hostname || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="最后心跳" width="160">
          <template #default="{ row }">
            <div class="heartbeat-info" v-if="row.last_heartbeat">
              <el-icon><Clock /></el-icon>
              {{ formatRelativeTime(row.last_heartbeat) }}
            </div>
            <div class="heartbeat-info" v-else>
              <span class="no-heartbeat">无记录</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="handleToggleActive(row)"
              :loading="row._loading"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">
              详情
            </el-button>
            <el-divider direction="vertical" />
            <el-popconfirm title="确定删除该执行器记录?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无执行器记录" :image-size="100">
            <template #image>
              <el-icon :size="60" color="#dcdfe6"><Monitor /></el-icon>
            </template>
          </el-empty>
        </template>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
          background
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="执行器详情" width="600px" align-center>
      <div class="detail-content" v-if="currentExecutor">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ currentExecutor.id }}</el-descriptions-item>
          <el-descriptions-item label="UUID">
            <span class="uuid-text">{{ currentExecutor.uuid }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="名称">{{ currentExecutor.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentExecutor.executor_type }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ currentExecutor.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <div class="status-badge" :class="currentExecutor.status">
              <span class="dot"></span>
              {{ statusText[currentExecutor.status] || currentExecutor.status }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ currentExecutor.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主机名">{{ currentExecutor.hostname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作系统">{{ currentExecutor.os_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="启用状态">
            <el-tag :type="currentExecutor.is_active ? 'success' : 'info'" size="small">
              {{ currentExecutor.is_active ? '已启用' : '已禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="能力" :span="2">
            <div v-if="currentExecutor.capabilities">
              <el-tag
                v-for="(cap, idx) in (currentExecutor.capabilities.script_types || [])"
                :key="idx"
                size="small"
                style="margin-right: 4px"
              >
                {{ cap }}
              </el-tag>
            </div>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ formatDate(currentExecutor.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="最后心跳">{{ formatDate(currentExecutor.last_heartbeat) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { getExecutorList, updateExecutor, deleteExecutor } from '@/api/pc'
import { ElMessage } from 'element-plus'
import { Refresh, Monitor, Clock, Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const list = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const searchKeyword = ref('')
const detailVisible = ref(false)
const currentExecutor = ref<any>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const statusText: any = {
  online: '在线',
  offline: '离线',
  busy: '忙碌'
}

const fetchList = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const res = await getExecutorList(params)
    list.value = (res.data || []).map((item: any) => ({ ...item, _loading: false }))
    total.value = list.value.length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  page.value = 1
  fetchList()
}

const handleSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchList()
  }, 300)
}

const showDetail = (row: any) => {
  currentExecutor.value = row
  detailVisible.value = true
}

const handleToggleActive = async (row: any) => {
  row._loading = true
  try {
    await updateExecutor(row.id, { is_active: row.is_active })
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (e) {
    row.is_active = !row.is_active
    ElMessage.error('更新失败')
  } finally {
    row._loading = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteExecutor(id)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const formatDate = (str: string) => str ? dayjs(str).format('YYYY-MM-DD HH:mm:ss') : '-'

const formatRelativeTime = (str: string) => {
  if (!str) return '-'
  return dayjs(str).fromNow()
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  fetchList()
  refreshTimer = setInterval(() => {
    fetchList()
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }

.toolbar-card {
  background: #fff;
  padding: 16px 24px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
}
.filter-group { display: flex; align-items: center; }

.table-card { border: none; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1); }
.text-gray { color: #9ca3af; font-family: monospace; }

.executor-name { display: flex; align-items: center; gap: 8px; }
.host-icon { color: #6366f1; }
.name-text { font-weight: 600; color: #111827; }

.status-badge { display: inline-flex; align-items: center; font-size: 13px; font-weight: 500; }
.status-badge .dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }

.status-badge.online { color: #059669; }
.status-badge.online .dot { background: #10b981; }

.status-badge.offline { color: #6b7280; }
.status-badge.offline .dot { background: #9ca3af; }

.status-badge.busy { color: #d97706; }
.status-badge.busy .dot { background: #f59e0b; animation: pulse 2s infinite; }

.ip-text { font-family: monospace; color: #374151; }
.hostname-text { color: #4b5563; }

.heartbeat-info { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #6b7280; }
.no-heartbeat { color: #d1d5db; }

.pagination-bar { padding: 16px 24px; display: flex; justify-content: flex-end; border-top: 1px solid #f3f4f6; }

.detail-content { padding: 8px 0; }
.uuid-text { font-family: monospace; font-size: 12px; color: #6b7280; word-break: break-all; }

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>