<template>
  <div class="case-edit">
    <el-page-header @back="handleBack" :icon="ArrowLeft" title="返回列表" style="margin-bottom: 20px">
      <template #content>
        <span class="text-large font-600 mr-3">{{ isEdit ? '编辑用例' : '新建用例' }}</span>
      </template>
      <template #extra>
        <el-button @click="handleDebug" type="warning" :loading="running" :disabled="!isEdit">
          <el-icon class="mr-1"><Tools /></el-icon> 调试
        </el-button>

        <el-button @click="handleRun" type="success" :loading="running" :disabled="!isEdit">
          <el-icon class="mr-1"><VideoPlay /></el-icon> 仅运行
        </el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon class="mr-1"><Check /></el-icon> 保存
        </el-button>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="main-row">
      <!-- 左侧：表单配置 -->
      <el-col :span="6" class="left-panel">
        <el-card shadow="never" class="h-100">
          <el-form :model="form" label-position="top">
            <el-form-item label="用例名称" required>
              <el-input v-model="form.name" placeholder="例如：GitHub Search" />
            </el-form-item>
            <el-form-item label="所属项目">
              <el-select v-model="form.project_id" placeholder="选择项目" clearable style="width: 100%">
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
                <el-radio-button label="yaml">YAML</el-radio-button>
                <el-radio-button label="typescript">TypeScript</el-radio-button>
                <el-radio-button label="prompt">自然语言</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="4"
                placeholder="简要描述该用例的测试目的..."
              />
            </el-form-item>

            <div class="tips-box">
              <p v-if="form.script_type === 'yaml'">
                <el-icon><InfoFilled /></el-icon> Midscene YAML 格式。支持 target, tasks, flow 等字段。
              </p>
              <p v-else-if="form.script_type === 'typescript'">
                <el-icon><InfoFilled /></el-icon> Node.js 环境。内置 puppeteer, @midscene/web。请确保代码可直接执行。
              </p>
              <p v-else>
                <el-icon><InfoFilled /></el-icon> 输入纯文本指令，系统将自动规划执行路径。
              </p>
            </div>

            <el-divider />

            <el-button type="primary" plain class="w-100" @click="handleSaveAndRun" :loading="running">
              保存并立即运行
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：代码编辑器 -->
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



    <el-drawer v-model="debugDrawerVisible" title="实时调试控制台" direction="rtl" size="50%" :before-close="handleCloseDebug">
      <div class="debug-container">
        <div class="status-bar">
          <el-tag :type="statusMap[debugStatus]">{{ debugStatus.toUpperCase() }}</el-tag>
          <span class="ml-2" v-if="debugStatus === 'running'">
            <el-icon class="is-loading"><Loading /></el-icon> 运行中...
          </span>
        </div>

        <div class="console-box">
           <pre>{{ debugLogs || '等待日志...' }}</pre>
        </div>

        <div class="footer" v-if="debugStatus === 'success'">
          <el-button type="success" @click="openReport">查看完整报告</el-button>
        </div>
      </div>
    </el-drawer>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ArrowLeft, VideoPlay, Check, InfoFilled } from '@element-plus/icons-vue'
import { Tools, Loading } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.params.id !== undefined)


const saving = ref(false)
const running = ref(false)
// 使用 shallowRef 避免 Monaco 实例被 Vue 深度代理导致性能问题
const editorRef = shallowRef()

const form = reactive({
  name: '',
  description: '',
  project_id: null as number | null,
  script_type: 'yaml',
  script_content: ''
})

// Monaco Editor 配置
const editorOptions = {
  automaticLayout: true,
  minimap: { enabled: false },
  fontSize: 14,
  scrollBeyondLastLine: false,
  tabSize: 2
}

const editorLanguage = computed(() => {
  switch (form.script_type) {
    case 'typescript': return 'typescript'
    case 'yaml': return 'yaml'
    default: return 'plaintext'
  }
})

// --- 模板定义 ---
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
import { expect } from '@playwright/test'; // 只保留 expect 用于断言

// 简单的 sleep 辅助函数
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function run() {
  // 1. 手动启动浏览器
  // 必须加上 --no-sandbox 以适应 Docker 环境
  const browser = await chromium.launch({
    headless: true, // "new" 或 true
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // --- 对应原来的 beforeEach ---
  // 设置一个固定的大分辨率，代替 window.screen.availWidth (Headless模式下获取屏幕尺寸可能不准)
  await page.setViewportSize({ width: 1920, height: 1080 });

  await page.goto('https://xxxxx');
  await sleep(5000);
  await page.waitForLoadState('networkidle');

  // 2. 初始化 Midscene Agent
  // 这一步代替了 fixture 的自动注入
  const agent = new PlaywrightAgent(page, {
    generateReport: true,
    reportFileName: 'report.html', // 确保生成报告
    waitForNetworkIdleTimeout: 2000 // 对应原来 fixture 的配置
  });

  // --- 对应原来的 test body ---

  // aiInput -> agent.aiAction
  // 注意：Midscene 核心方法是 aiAction, aiAssert, aiQuery

  // 输入帐号 (aiInput 只是 aiAction 的语法糖，这里直接用自然语言描述)
  await agent.aiAction('在 "用户名" 输入框中输入 "admin"');

  // 获取数据 (aiQuery)
  const items = await agent.aiQuery(
    '从页面的查询结果表格中，获取所有行的批次号（对应“批次号”列）和产品型号（对应“产品型号”列），返回数组'
  );

  // 断言
  if (!items || items.length === 0) {
    throw new Error('未查询到任何数据');
  }

  // 验证 (aiAssert)
  await agent.aiAssert('能查询到数据');

  // 截图留证
  await page.screenshot({ path: 'screenshot.png', fullPage: true });

  // 3. 清理资源
  await browser.close();
}

// 执行入口
run().catch(err => {
  console.error(err);
  process.exit(1);
});`,

  prompt: `打开百度首页
在搜索框输入 Midscene
点击搜索按钮
检查页面是否包含 "AI自动化" 字样`
}

// --- 生命周期 & 方法 ---

const handleEditorMount = (editor: any) => {
  editorRef.value = editor
}

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await axios.get(`/testcases/${route.params.id}`)
      Object.assign(form, res.data)
    } catch (e) {
      console.error(e)
    }
  } else {
    // 新建时，默认填充 YAML 模板
    form.script_content = TEMPLATES.yaml
  }
})

const handleTypeChange = (val: string) => {
  // 只有当内容为空，或者内容是其他类型的默认模板时，才自动替换
  // 这里简化处理：如果是新建模式且未修改过，或者是空内容，则填充
  const currentContent = form.script_content.trim()
  const isDefaultYaml = currentContent === TEMPLATES.yaml.trim()
  const isDefaultTs = currentContent === TEMPLATES.typescript.trim()
  const isDefaultPrompt = currentContent === TEMPLATES.prompt.trim()

  if (!currentContent || isDefaultYaml || isDefaultTs || isDefaultPrompt) {
    form.script_content = TEMPLATES[val as keyof typeof TEMPLATES]
  }
}

const handleBack = () => {
  router.push('/testcases')
}

const handleSave = async () => {
  if (!form.name) return ElMessage.warning('请输入用例名称')
  if (!form.script_content) return ElMessage.warning('脚本内容不能为空')

  saving.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/testcases/${route.params.id}`, form)
    } else {
      const res = await axios.post('/testcases/', form)
      // 创建后跳转到编辑模式，替换路由，防止刷新丢失
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

const handleRun = async () => {
  if (!isEdit.value) return
  running.value = true
  try {
    const id = route.params.id
    const res = await axios.post(`/testcases/${id}/run`)
    ElMessage.success('任务已提交')
    router.push(`/reports/${res.data.id}`)
  } catch(e: any) {
    const msg = e.response?.data?.detail || '运行失败'
    ElMessage.error(msg)
  } finally {
    running.value = false
  }
}

const handleSaveAndRun = async () => {
  const success = await handleSave()
  if (success) {
    // 保存成功后，如果之前是新建，路由已经变成了 edit/:id，可以直接获取 params.id
    // 但为了保险，我们可以直接用 handleRun (它依赖路由参数)
    // 稍微延迟一下确保路由更新完成
    setTimeout(() => {
      handleRun()
    }, 100)
  }
}


const projectList = ref<any[]>([])
const envList = ref([])
const selectedEnvId = ref(null) // 当前选中的环境

onMounted(async () => {
  // 1. 并行加载项目列表和用例详情
  const [projectsRes, caseRes] = await Promise.all([
    axios.get('/projects/'),
    isEdit.value ? axios.get(`/testcases/${route.params.id}`) : Promise.resolve({ data: {} })
  ])

  const envRes = await axios.get('/envs/')
  envList.value = envRes.data

  projectList.value = projectsRes.data

  if (isEdit.value) {
    Object.assign(form, caseRes.data)
  } else {
    form.script_content = TEMPLATES.yaml
  }
})

const debugDrawerVisible = ref(false)
const debugReportId = ref(0)
const debugLogs = ref('')
const debugStatus = ref('')
let debugTimer: any = null

const statusMap: any = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }

const handleDebug = async () => {
  if (!isEdit.value) return

  // 先保存
  await handleSave()

  running.value = true
  debugDrawerVisible.value = true
  debugLogs.value = ''
  debugStatus.value = 'pending'

  try {
    const id = route.params.id
    const res = await axios.post(`/testcases/${id}/run`)
    debugReportId.value = res.data.id

    // 开始轮询日志
    pollDebugStatus()
  } catch(e) {
    ElMessage.error('启动失败')
    running.value = false
  }
}

const pollDebugStatus = async () => {
  if (!debugDrawerVisible.value) return // 关闭了抽屉就停止轮询

  try {
    const res = await axios.get(`/testcases/reports/${debugReportId.value}`)
    const data = res.data
    debugStatus.value = data.status
    debugLogs.value = data.logs

    if (['pending', 'running'].includes(data.status)) {
      debugTimer = setTimeout(pollDebugStatus, 2000)
    } else {
      running.value = false
      // 如果成功，自动提示
      if (data.status === 'success') {
         ElMessage.success('调试完成')
      }
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
  window.open(`/#/reports/${debugReportId.value}`, '_blank')
}
</script>

<style scoped>
.case-edit {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.main-row {
  flex: 1;
  /* 减去 header 的高度 (大约 60px) */
  height: calc(100% - 60px);
}

.left-panel {
  height: 100%;
}
.right-panel {
  height: 100%;
}

.h-100 {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.w-100 {
  width: 100%;
}

.tips-box {
  background: #f0f9eb;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 20px;
  font-size: 12px;
  color: #67c23a;
}
.tips-box p {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0;
}

.editor-wrapper {
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.mr-1 { margin-right: 5px; }
.debug-container { height: 100%; display: flex; flex-direction: column; }
.console-box { flex: 1; background: #1e1e1e; color: #fff; padding: 10px; overflow: auto; margin: 10px 0; border-radius: 4px; }
.console-box pre { white-space: pre-wrap; font-family: monospace; font-size: 12px; }

</style>
