<template>
  <div class="page-container">
    <div class="toolbar-card">
      <div class="title-section">
        <span class="title">知识库管理</span>
        <span class="subtitle">支持 PDF, Word, Txt, Excel (历史用例导入)</span>
      </div>

      <div class="actions">
        <el-button :icon="Search" @click="openSearchDialog" style="margin-right: 12px">
          检索测试
        </el-button>

        <el-button :icon="Refresh" circle @click="() => fetchList(true)" title="刷新列表" style="margin-right: 12px" />

        <el-upload
          :action="uploadUrl"
          :headers="headers"
          :show-file-list="false"
          :on-success="handleSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          accept=".pdf,.docx,.txt,.xlsx,.xls,.csv"
          :disabled="uploading"
        >
          <el-button type="primary" :icon="Upload" :loading="uploading">上传文档 / 历史用例</el-button>
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
            <el-tag v-else-if="['pending', 'processing'].includes(row.status)" type="warning" effect="light">解析中</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger" effect="light">失败</el-tag>
            <el-tag v-else type="info" effect="plain">{{ row.status || '未知' }}</el-tag>
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

    <el-dialog v-model="searchDialogVisible" title="向量库检索测试" width="600px">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="输入测试用例需求或关键字"
          @keyup.enter="handleSearch"
          clearable
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" :loading="searching">搜索</el-button>
          </template>
        </el-input>
      </div>

      <div class="search-results" v-loading="searching">
        <el-empty v-if="!searchResults.length && !searching" description="暂无相关匹配数据" :image-size="80" />
        <div v-else class="result-list">
          <div v-for="(item, index) in searchResults" :key="index" class="result-item">
            <div class="result-meta">
              <el-tag size="small" effect="plain">匹配度参考: Top {{ index + 1 }}</el-tag>
              <span class="source-file" v-if="item.metadata?.source">
                📄 {{ getFileName(item.metadata.source) }}
              </span>
            </div>
            <div class="result-content">{{ item.content }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from '@/utils/request'
import { Upload, Document, Delete, Refresh, RefreshRight, Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const loading = ref(false)
const uploading = ref(false) // 上传状态锁
const reprocessingId = ref<number | null>(null)
let timer: any = null

const uploadUrl = '/api/knowledge/upload'
const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const searchDialogVisible = ref(false)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searching = ref(false)

// [修改] 增加时间戳，防止浏览器缓存
const fetchList = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const res = await axios.get(`/knowledge/list?_t=${new Date().getTime()}`)
    list.value = res.data
  } catch(e) {
    console.error(e)
  } finally {
    if (showLoading) loading.value = false
  }
}

const startPolling = () => {
  if (timer) clearInterval(timer)
  let count = 0

  timer = setInterval(async () => {
    count++
    try {
      await fetchList(false)

      const hasPending = list.value.some((item: any) =>
        ['pending', 'processing'].includes(item.status)
      )

      if (!hasPending || count > 40) { // 延长轮询时间到2分钟
        clearInterval(timer)
        timer = null
      }
    } catch (e) {
      console.error('Polling error', e)
      clearInterval(timer)
      timer = null
    }
  }, 3000)
}

const handleReprocess = async (row: any) => {
  reprocessingId.value = row.id
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
    row.status = 'pending'
    row.error_msg = ''
    startPolling()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重试失败')
  } finally {
    reprocessingId.value = null
  }
}

const handleDelete = async (row: any) => {
  try {
    await axios.delete(`/knowledge/${row.id}`)
    ElMessage.success('删除成功')
    fetchList(true)
  } catch (e: any) {
    ElMessage.error('删除失败')
  }
}

const beforeUpload = () => {
  if (uploading.value) return false
  uploading.value = true
  ElMessage.info('正在上传文件...')
  return true
}

const handleSuccess = (response: any) => {
  uploading.value = false
  if (response.status === 'success' || response.id) {
    ElMessage.success('上传成功，开始后台解析')
    // 强制立即刷新一次
    fetchList(true).then(() => {
        startPolling()
    })
  } else {
    ElMessage.warning('上传响应异常')
  }
}

const handleUploadError = (err: any) => {
  uploading.value = false
  let errorMsg = '上传失败'
  if (err.message) {
    try {
      const parsed = JSON.parse(err.message)
      if (parsed.detail) errorMsg = parsed.detail
    } catch (e) { console.log(e) }
  }
  ElMessage.error(errorMsg)
}

const formatDate = (str: string) => dayjs(str).format('YYYY-MM-DD HH:mm')
const getFileName = (path: string) => {
  if (!path) return '未知来源'
  return path.split(/[/\\]/).pop() || path
}

const openSearchDialog = () => {
  searchDialogVisible.value = true
  searchResults.value = []
  searchQuery.value = ''
}

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await axios.post('/knowledge/search', {
      query: searchQuery.value,
      top_k: 4
    })
    searchResults.value = res.data.results
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '检索失败')
  } finally {
    searching.value = false
  }
}

onMounted(() => {
  fetchList(true)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
/* 保持样式不变 */
.page-container { max-width: 1200px; margin: 0 auto; padding-top: 20px; }
.toolbar-card { background: #fff; padding: 16px 24px; border-radius: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.title-section { display: flex; flex-direction: column; }
.title { font-size: 18px; font-weight: 600; color: #1f2937; }
.subtitle { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.table-card { border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.file-info { display: flex; align-items: center; gap: 8px; }
.file-icon { color: #6b7280; font-size: 16px; }
.file-name { font-weight: 500; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.error-text { color: #ef4444; font-size: 12px; cursor: help; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; max-width: 100%; }
.text-gray { color: #d1d5db; }
.chunk-count { font-weight: bold; color: #10b981; }

.search-box { margin-bottom: 20px; }
.search-results { max-height: 400px; overflow-y: auto; padding-right: 4px; }
.result-list { display: flex; flex-direction: column; gap: 12px; }
.result-item { background: #f9fafb; border-radius: 8px; padding: 12px; border: 1px solid #e5e7eb; }
.result-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; color: #6b7280; }
.source-file { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-content { font-size: 13px; line-height: 1.6; color: #374151; white-space: pre-wrap; word-break: break-all; }
</style>