<template>
  <div class="case-edit">
    <!-- 顶部导航 -->
    <el-page-header @back="handleBack" :icon="ArrowLeft" title="返回列表" style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
      <template #content>
        <span class="text-large font-600 mr-3">{{ isEdit ? '编辑用例' : '新建用例' }}</span>
        <el-tag type="info" v-if="isEdit">ID: {{ route.params.id }}</el-tag>
      </template>
      <template #extra>
        <!-- 调试按钮 -->
        <el-button @click="openDebugDrawer" type="warning" plain :disabled="!isEdit">
          <el-icon class="mr-1"><Tools /></el-icon> 调试
        </el-button>

        <!-- 仅运行按钮 -->
        <el-button @click="handleRun" type="success" :loading="running" :disabled="!isEdit">
          <el-icon class="mr-1"><VideoPlay /></el-icon> 仅运行
        </el-button>

        <!-- 保存按钮 -->
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon class="mr-1"><Check /></el-icon> 保存
        </el-button>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="main-row">
      <!-- 左侧表单 -->
      <el-col :span="6" class="left-panel">
        <el-card shadow="never" class="h-100 form-card">
          <el-form :model="form" label-position="top">
            <el-form-item label="用例名称" required>
              <el-input v-model="form.name" placeholder="例如：GitHub Search" />
            </el-form-item>

            <el-form-item label="所属项目">
              <el-select v-model="form.project_id" placeholder="选择项目" clearable class="w-100">
                <el-option
                  v-for="p in projectList"
                  :key="p.id"
                  :label="p.name"
                  :value="p.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="脚本类型">
              <el-radio-group v-model="form.script_type" @change="handleTypeChange" class="w-100">
                <el-radio-button label="typescript">TypeScript</el-radio-button>
                <el-radio-button label="yaml">YAML</el-radio-button>
                <el-radio-button label="prompt">自然语言</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="3"
                placeholder="简要描述..."
              />
            </el-form-item>

            <div class="tips-box">
              <p v-if="form.script_type === 'typescript'">
                <el-icon><InfoFilled /></el-icon> TS 模式 (推荐)：支持 Playwright 原生 API + Midscene Agent。
              </p>
              <p v-else-if="form.script_type === 'yaml'">
                <el-icon><InfoFilled /></el-icon> YAML 模式：声明式写法。
              </p>
              <p v-else>
                <el-icon><InfoFilled /></el-icon> Prompt 模式：输入自然语言指令。
              </p>
            </div>

            <el-divider />

            <el-button type="primary" plain class="w-100" @click="handleSaveAndRun" :loading="running">
              保存并立即运行
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧编辑器 -->
      <el-col :span="18" class="right-panel">
        <div class="editor-wrapper">
          <vue-monaco-editor
            v-model:value="form.script_content"
            :language="editorLanguage"
            theme="vs-dark"
            :options="editorOptions"
            @mount="handleEditorMount"
          />
        </div>
      </el-col>
    </el-row>

    <!-- 调试抽屉 -->
    <el-drawer
      v-model="debugDrawerVisible"
      title="实时调试控制台"
      direction="rtl"
      size="50%"
      :before-close="handleCloseDebug"
      destroy-on-close
    >
      <div class="debug-container">
        <!-- 调试工具栏：选择环境 -->
        <div class="debug-toolbar">
          <el-select v-model="selectedEnvId" placeholder="选择运行环境" style="width: 200px" clearable>
             <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id">
               <span style="float: left">{{ e.name }}</span>
               <span style="float: right; color: #8492a6; font-size: 12px">{{ e.description }}</span>
             </el-option>
          </el-select>
          <el-button type="primary" @click="startDebugRun" :loading="running" :icon="VideoPlay">
            {{ running ? '运行中...' : '开始运行' }}
          </el-button>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar" v-if="debugStatus">
          <el-alert
            :title="debugStatus.toUpperCase()"
            :type="statusMap[debugStatus]"
            :description="debugStatus === 'running' ? 'Midscene 正在执行中...' : ''"
            show-icon
            :closable="false"
          />
        </div>

        <!-- 日志输出 -->
        <div class="console-box" ref="consoleBoxRef">
           <pre>{{ debugLogs || '// 等待运行...' }}</pre>
        </div>

        <!-- 底部操作 -->
        <div class="drawer-footer" v-if="debugStatus === 'success'">
          <el-button type="success" @click="openReport" plain class="w-100">
            查看完整报告
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, shallowRef, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ArrowLeft, VideoPlay, Check, InfoFilled, Tools } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.params.id !== undefined)

const saving = ref(false)
const running = ref(false)
const editorRef = shallowRef()

// 数据列表
const projectList = ref<any[]>([])
const envList = ref<any[]>([])

const form = reactive({
  name: '',
  description: '',
  project_id: null as number | null,
  script_type: 'typescript',
  script_content: ''
})

// 调试状态
const debugDrawerVisible = ref(false)
const selectedEnvId = ref<number | null>(null)
const debugReportId = ref(0)
const debugLogs = ref('')
const debugStatus = ref('')
let debugTimer: any = null
const consoleBoxRef = ref<HTMLElement>()

const statusMap: any = { pending: 'info', running: 'warning', success: 'success', failed: 'error' }

// Monaco 配置
const editorOptions = {
  automaticLayout: true,
  minimap: { enabled: false },
  fontSize: 14,
  scrollBeyondLastLine: false,
  tabSize: 2,
  wordWrap: 'on'
}

const editorLanguage = computed(() => {
  switch (form.script_type) {
    case 'typescript': return 'typescript'
    case 'yaml': return 'yaml'
    default: return 'plaintext'
  }
})

// 模板
const TEMPLATES = {
  yaml: `target:
  url: https://www.google.com
tasks:
  - name: search midscene
    flow:
      - ai: type "Midscene" in search box, hit enter
      - sleep: 3000`,

  typescript: `import { chromium } from 'playwright-core';
import { PlaywrightAgent } from '@midscene/web/playwright';

async function run() {
  // 1. 启动浏览器
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // 使用环境变量 (在调试栏选择环境)
  const baseUrl = process.env.BASE_URL || 'https://www.baidu.com';
  await page.goto(baseUrl);

  // 2. 初始化 Midscene
  const agent = new PlaywrightAgent(page, {
    generateReport: true,
    reportFileName: 'report.html'
  });

  // 3. 执行
  await agent.aiAction('输入 "Midscene" 并回车');
  await agent.aiAssert('搜索结果包含 "Midscene"');
  await page.screenshot({ path: 'screenshot.png' });

  await browser.close();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});`,

  prompt: `打开百度首页
在搜索框输入 Midscene
点击搜索按钮`
}

const handleEditorMount = (editor: any) => {
  editorRef.value = editor
}

// 合并后的 onMounted
onMounted(async () => {
  const promises: Promise<any>[] = [
    axios.get('/projects/'),
    axios.get('/envs/')
  ]

  if (isEdit.value) {
    promises.push(axios.get(`/testcases/${route.params.id}`))
  }

  try {
    const results = await Promise.all(promises)
    const pRes = results[0]
    const eRes = results[1]
    const cRes = isEdit.value ? results[2] : null

    projectList.value = pRes.data
    envList.value = eRes.data

    if (isEdit.value && cRes) {
      Object.assign(form, cRes.data)
    } else {
      form.script_content = TEMPLATES.typescript
    }
  } catch (e) {
    console.error(e)
  }
})

const handleTypeChange = (val: string) => {
  const current = form.script_content.trim()
  const isDefault = Object.values(TEMPLATES).some(t => t.trim() === current)
  if (!current || isDefault) {
    form.script_content = TEMPLATES[val as keyof typeof TEMPLATES]
  }
}

const handleBack = () => router.push('/testcases')

const handleSave = async () => {
  if (!form.name) return ElMessage.warning('请输入用例名称')
  if (!form.script_content) return ElMessage.warning('脚本内容不能为空')

  saving.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/testcases/${route.params.id}`, form)
    } else {
      const res = await axios.post('/testcases/', form)
      await router.replace(`/testcases/edit/${res.data.id}`)
    }
    ElMessage.success('保存成功')
    return true
  } catch (e) {
    ElMessage.error('保存失败')
    return false
  } finally {
    saving.value = false
  }
}

// 调试逻辑：打开抽屉
const openDebugDrawer = () => {
  if (!isEdit.value) return
  debugDrawerVisible.value = true
  if (debugStatus.value === '') debugLogs.value = ''
}

// 调试逻辑：开始运行
const startDebugRun = async () => {
  await handleSave()
  running.value = true
  debugLogs.value = ''
  debugStatus.value = 'running'

  try {
    // 关键：传递选中的 env_id
    const params = selectedEnvId.value ? { env_id: selectedEnvId.value } : {}
    const res = await axios.post(`/testcases/${route.params.id}/run`, null, { params })
    debugReportId.value = res.data.id
    pollDebugStatus()
  } catch(e: any) {
    ElMessage.error('启动失败')
    running.value = false
    debugStatus.value = 'failed'
  }
}

// 普通运行逻辑
const handleRun = async () => {
  if (!isEdit.value) return
  running.value = true
  try {
    // 普通运行默认不传 env_id (使用默认环境)，如果需要也能选，建议用调试功能选
    const res = await axios.post(`/testcases/${route.params.id}/run`)
    ElMessage.success('任务已提交')
    router.push(`/reports/${res.data.id}`)
  } catch(e) {
    ElMessage.error('运行失败')
  } finally {
    running.value = false
  }
}

const handleSaveAndRun = async () => {
  if (await handleSave()) {
    setTimeout(handleRun, 100)
  }
}

const pollDebugStatus = async () => {
  if (!debugDrawerVisible.value) return

  try {
    const res = await axios.get(`/testcases/reports/${debugReportId.value}`)
    console.log('Report Data:', res.data) // <--- Debug
    const data = res.data
    debugStatus.value = data.status
    debugLogs.value = data.logs

    nextTick(() => {
      if (consoleBoxRef.value) consoleBoxRef.value.scrollTop = consoleBoxRef.value.scrollHeight
    })

    if (['pending', 'running'].includes(data.status)) {
      debugTimer = setTimeout(pollDebugStatus, 2000)
    } else {
      running.value = false
      if (data.status === 'success') ElMessage.success('调试完成')
    }
  } catch (e) {
    console.error(e)
  }
}

const handleCloseDebug = (done: any) => {
  if (debugTimer) clearTimeout(debugTimer)
  done()
}

const openReport = () => {
  // 使用 Vue Router 生成标准链接，自动处理 History/Hash 模式
  const { href } = router.resolve({
    path: `/report-view/${debugReportId.value}`
  })
  window.open(href, '_blank')
}


</script>

<style scoped>
.case-edit { height: 100%; display: flex; flex-direction: column; }
.main-row { flex: 1; height: calc(100% - 60px); }
.left-panel { height: 100%; }
.right-panel { height: 100%; }
.form-card { overflow-y: auto; }
.h-100 { height: 100%; }
.w-100 { width: 100%; }
.mr-1 { margin-right: 5px; }

.tips-box {
  background: #f4f4f5;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
  border-left: 3px solid #909399;
}
.tips-box p { margin: 0; font-size: 13px; color: #303133; display: flex; align-items: center; gap: 5px; }

.editor-wrapper {
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.debug-container { height: 100%; display: flex; flex-direction: column; padding: 0 20px 20px; }
.debug-toolbar { display: flex; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.status-bar { margin: 10px 0; }
.console-box { flex: 1; background: #1e1e1e; color: #ccc; padding: 15px; border-radius: 4px; overflow: auto; font-family: monospace; font-size: 12px; }
.console-box pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
.drawer-footer { margin-top: 15px; }
</style>
