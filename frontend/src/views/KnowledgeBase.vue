<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title-section">
        <span class="title">知识库管理</span>
        <span class="subtitle">支持 PDF, Word, Txt, Excel (历史用例导入)</span>
      </div>

      <div class="actions">
        <el-button :icon="Refresh" circle @click="fetchList" title="刷新列表" style="margin-right: 12px" />

        <el-upload
          :action="uploadUrl"
          :headers="headers"
          :show-file-list="false"
          :on-success="handleSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          accept=".pdf,.docx,.txt,.xlsx,.xls,.csv"
        >
          <el-button type="primary" :icon="Upload">上传文档 / 历史用例</el-button>
        </el-upload>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-info">
              <el-icon class="file-icon"><Document /></el-icon>
              <span class="file-name" :title="row.filename">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="doc_type" label="类型" width="90" align="center">
           <template #default="{row}">
             <el-tag size="small" type="info">{{ row.doc_type }}</el-tag>
           </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="110" align="center">
          <template #default="{row}">
            <el-tag v-if="row.status === 'success'" type="success" effect="light">已完成</el-tag>
            <el-tag v-else-if="row.status === 'pending'" type="warning" effect="light">解析中</el-tag>
            <el-tag v-else type="danger" effect="light">失败</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="chunk_count" label="切片数" width="90" align="center">
          <template #default="{row}">
            <span class="chunk-count" v-if="row.status === 'success'">{{ row.chunk_count }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column label="备注/错误" min-width="150">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.error_msg"
              class="box-item"
              effect="dark"
              :content="row.error_msg"
              placement="top"
            >
              <span class="error-text">{{ row.error_msg }}</span>
            </el-tooltip>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" label="上传时间" width="160" align="center">
           <template #default="{row}">{{ formatDate(row.create_time) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-tooltip
              :content="row.status === 'success' ? '更新向量库数据 (先删后存)' : '重新尝试解析'"
              placement="top"
            >
              <el-button
                type="primary"
                link
                :icon="RefreshRight"
                @click="handleReprocess(row)"
                :loading="reprocessingId === row.id"
              >
                {{ row.status === 'success' ? '更新' : '重试' }}
              </el-button>
            </el-tooltip>

            <el-popconfirm
              title="确认删除此文件及相关的向量数据?"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" link :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/utils/request'
import { Upload, Document, Delete, Refresh, RefreshRight } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

// --- 状态定义 ---
const list = ref([])
const loading = ref(false)
const reprocessingId = ref<number | null>(null) // 记录正在重试的行ID，用于显示 loading
let timer: any = null // 轮询定时器

// 上传配置 (vite 代理转发 /api -> 后端)
const uploadUrl = '/api/knowledge/upload'
const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` }

// --- 核心方法 ---

// 1. 获取列表
const fetchList = async () => {
  // 如果是静默刷新(例如轮询中)，不需要 loading 遮罩
  if (!timer) loading.value = true
  try {
    const res = await axios.get('/knowledge/list')
    list.value = res.data
  } catch(e) {
    console.error(e)
  } finally {
    if (!timer) loading.value = false
  }
}

// 2. 重新解析 (Reprocess)
const handleReprocess = async (row: any) => {
  reprocessingId.value = row.id

  // 对于已经成功的任务，给一个二次确认，防止误操作
  if (row.status === 'success') {
    try {
      await ElMessageBox.confirm(
        '该文件已成功入库。重新解析将【先删除旧向量数据】，然后重新入库。是否继续？',
        '确认更新',
        { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      reprocessingId.value = null
      return
    }
  }

  try {
    await axios.post(`/knowledge/${row.id}/reprocess`)
    ElMessage.success('已清理旧数据，后台正在重新解析...')

    // 乐观更新状态，让用户立即看到变化
    row.status = 'pending'
    row.error_msg = ''

    // 开启短期轮询检查状态
    startPolling()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重试失败，请检查模型配置')
  } finally {
    reprocessingId.value = null
  }
}

// 3. 删除文件
const handleDelete = async (row: any) => {
  try {
    // 假设后端有 DELETE 接口，如果没有请确保后端已实现
    // 如果没有 delete 接口，可以暂时隐藏或报错
    await axios.delete(`/knowledge/${row.id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e: any) {
    ElMessage.error('删除失败')
  }
}

// 4. 上传回调
const beforeUpload = () => {
  ElMessage.info('正在上传文件...')
  return true
}

const handleSuccess = (response: any) => {
  // 后端返回 {status: "success", id: ...}
  if (response.status === 'success' || response.id) {
    ElMessage.success('上传成功，开始后台解析')
    fetchList()
    startPolling() // 上传后自动开启轮询
  } else {
    ElMessage.warning('上传响应异常')
  }
}

const handleUploadError = (err: any) => {
  ElMessage.error('上传失败，请检查网络或文件大小')
  console.error(err)
}

// 5. 工具函数
const formatDate = (str: string) => dayjs(str).format('YYYY-MM-DD HH:mm')

// 6. 轮询机制 (用于自动更新 pending 状态)
const startPolling = () => {
  if (timer) clearInterval(timer)
  let count = 0

  timer = setInterval(async () => {
    count++
    // 静默刷新列表数据
    const res = await axios.get('/knowledge/list')
    list.value = res.data

    // 检查是否还有 pending 的任务
    const hasPending = list.value.some((item: any) => item.status === 'pending')

    // 如果没有 pending 任务了，或者轮询超过 20 次 (约1分钟)，停止轮询
    if (!hasPending || count > 20) {
      clearInterval(timer)
      timer = null
    }
  }, 3000) // 每3秒刷新一次
}

onMounted(() => {
  fetchList()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding-top: 20px;
}

.toolbar-card {
  background: #fff;
  padding: 16px 24px;
  border-radius: 12px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.title-section {
  display: flex;
  flex-direction: column;
}
.title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}
.subtitle {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

.table-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* 文件名样式 */
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-icon {
  color: #6b7280;
  font-size: 16px;
}
.file-name {
  font-weight: 500;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 错误文字样式 */
.error-text {
  color: #ef4444;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 100%;
  cursor: help;
}
.text-gray {
  color: #d1d5db;
}

.chunk-count {
  font-weight: bold;
  color: #10b981;
}
</style>