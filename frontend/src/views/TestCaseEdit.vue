<template>
  <div class="edit-container">
    <div class="header-bar">
      <div class="left">
        <el-button link @click="handleBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <span class="divider">|</span>
        <span class="title">{{ isEdit ? '编辑测试用例' : '新建测试用例' }}</span>
        <el-tag v-if="isEdit" type="info" size="small" class="ml-2">ID: {{ route.params.id }}</el-tag>
      </div>
      <div class="right">
        <el-button-group class="mr-3">
          <el-button @click="openDebugDrawer" :disabled="!isEdit" :icon="Tools">调试控制台</el-button>
          <el-button @click="handleRun" :loading="running" :disabled="!isEdit" :icon="VideoPlay">仅运行</el-button>
        </el-button-group>
        <el-button type="primary" @click="handleSave" :loading="saving" :icon="Check">保存更改</el-button>
      </div>
    </div>

    <div class="main-body">
      <div class="left-panel">
        <el-scrollbar>
          <el-form :model="form" label-position="top" class="setting-form">
            <el-form-item label="用例名称" required>
              <el-input v-model="form.name" placeholder="例如：GitHub Search" size="large" />
            </el-form-item>

            <el-form-item label="所属项目">
              <el-select v-model="form.project_id" placeholder="选择项目" clearable class="w-100">
                <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="脚本模式">
              <el-radio-group v-model="form.script_type" @change="handleTypeChange" class="w-100 type-radio">
                <el-radio-button label="typescript">TypeScript</el-radio-button>
                <el-radio-button label="yaml">YAML</el-radio-button>
                <el-radio-button label="prompt">自然语言</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <div class="tips-wrapper">
              <el-alert v-if="form.script_type === 'typescript'" type="info" :closable="false" show-icon>
                <template #title>TS 模式 (推荐)</template>
                <template #default>支持 Playwright 原生 API + Midscene Agent 智能指令。</template>
              </el-alert>
              <el-alert v-else-if="form.script_type === 'yaml'" type="warning" :closable="false" show-icon>
                <template #title>YAML 模式</template>
                <template #default>声明式写法，适合简单的线性流程。</template>
              </el-alert>
              <el-alert v-else type="success" :closable="false" show-icon>
                <template #title>Prompt 模式</template>
                <template #default>直接输入自然语言指令，AI 自动规划执行。</template>
              </el-alert>
            </div>

            <el-form-item label="描述备注" class="mt-4">
              <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简要描述测试意图..." resize="none" />
            </el-form-item>

            <div class="action-footer">
               <el-button type="primary" plain class="w-100" @click="handleSaveAndRun" :loading="running" :icon="VideoPlay">
                 保存并立即运行
               </el-button>
            </div>
          </el-form>
        </el-scrollbar>
      </div>

      <div class="right-panel">
        <div class="editor-header">
          <span class="file-tab">
            <el-icon class="mr-1"><Document /></el-icon>
            script.{{ fileExt }}
          </span>
          <span class="editor-tip">按 Ctrl+S 保存</span>
        </div>
        <div class="monaco-container">
          <div v-if="editorReady && !useFallbackEditor" ref="editorContainer" class="monaco-editor"></div>
          <textarea 
            v-else-if="editorReady && useFallbackEditor"
            v-model="form.script_content"
            class="fallback-editor"
            :class="{ 'script-typescript': form.script_type === 'typescript', 'script-yaml': form.script_type === 'yaml' }"
          ></textarea>
          <div v-else class="editor-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载编辑器中...</span>
          </div>
        </div>
        
        <!-- YAML 校验状态显示 -->
        <div v-if="form.script_type === 'yaml'" class="validation-status">
          <el-alert
            v-if="yamlValidationError"
            type="error"
            :title="'YAML 格式错误'"
            :closable="false"
            show-icon
          >
            {{ yamlValidationError }}
          </el-alert>
          <el-alert
            v-else-if="yamlValidationSuccess"
            type="success"
            title="YAML 格式正确"
            :closable="false"
            show-icon
          />
        </div>
      </div>
    </div>

    <el-drawer
      v-model="debugDrawerVisible"
      title="实时调试控制台"
      direction="rtl"
      size="600px"
      :before-close="handleCloseDebug"
      destroy-on-close
      class="debug-drawer"
    >
      <div class="debug-layout">
        <div class="debug-toolbar">
          <el-select v-model="selectedEnvId" placeholder="选择运行环境" style="width: 220px" clearable>
             <el-option v-for="e in envList" :key="e.id" :label="e.name" :value="e.id">
               <span style="float: left">{{ e.name }}</span>
               <span class="env-desc">{{ e.description }}</span>
             </el-option>
          </el-select>
          <el-button type="primary" @click="startDebugRun" :loading="running" :icon="VideoPlay">
            {{ running ? '运行中...' : '开始执行' }}
          </el-button>
        </div>

        <div v-if="debugStatus" class="status-banner" :class="debugStatus">
          <div class="status-icon">
            <el-icon v-if="debugStatus === 'running'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else-if="debugStatus === 'success'"><Select /></el-icon>
            <el-icon v-else><CloseBold /></el-icon>
          </div>
          <div class="status-text">
            <h4>{{ debugStatus.toUpperCase() }}</h4>
            <span v-if="debugStatus === 'running'">Midscene 正在分析页面并执行操作...</span>
          </div>
        </div>

        <div class="console-wrapper">
           <div class="console-header">TERMINAL OUTPUT</div>
           <div class="console-body" ref="consoleBoxRef">
             <pre>{{ debugLogs || '// 等待运行...' }}</pre>
           </div>
        </div>

        <div class="drawer-footer" v-if="debugStatus === 'success'">
          <el-button type="success" @click="openReport" plain class="w-100" :icon="Document">
            查看完整测试报告
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, shallowRef, nextTick, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay, Check, Tools, Document, Loading, Select, CloseBold } from '@element-plus/icons-vue'
import * as yaml from 'js-yaml'

// 尝试动态加载 Monaco 编辑器
let monaco: any = null
let editor: any = null

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.params.id !== undefined)

const saving = ref(false)
const running = ref(false)
const editorReady = ref(false)
const useFallbackEditor = ref(false)
const editorContainer = ref<HTMLElement | null>(null)

const projectList = ref<any[]>([])
const envList = ref<any[]>([])

const form = reactive({
  name: '', description: '', project_id: null as number | null,
  script_type: 'typescript', script_content: ''
})

const debugDrawerVisible = ref(false)
const selectedEnvId = ref<number | null>(null)
const debugReportId = ref(0)
const debugLogs = ref('')
const debugStatus = ref('')
let debugTimer: any = null
const consoleBoxRef = ref<HTMLElement>()

// YAML 校验相关
const yamlValidationError = ref('')
const yamlValidationSuccess = ref(false)

const editorLanguage = computed(() => {
  if (form.script_type === 'typescript') return 'typescript'
  if (form.script_type === 'yaml') return 'yaml'
  return 'plaintext'
})

const fileExt = computed(() => {
  if (form.script_type === 'typescript') return 'ts'
  if (form.script_type === 'yaml') return 'yaml'
  return 'txt'
})

// TEMPLATES 常量保持不变，此处省略以节省空间...
const TEMPLATES: any = {
  yaml: `target:\n  url: https://www.google.com\ntasks:\n  - name: search\n    flow:\n      - ai: type "Midscene"\n      - sleep: 3000`,
  typescript: `import { chromium } from 'playwright-core';\nimport { PlaywrightAgent } from '@midscene/web/playwright';\n\nasync function run() {\n  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });\n  const page = await browser.newPage();\n  await page.goto(process.env.BASE_URL || 'https://www.baidu.com');\n\n  const agent = new PlaywrightAgent(page);\n  await agent.aiAction('输入 "Midscene" 并回车');\n  await agent.aiAssert('搜索结果包含 "Midscene"');\n\n  await browser.close();\n}\n\nrun();`,
  prompt: `打开百度首页\n在搜索框输入 Midscene\n点击搜索按钮`
}

const initEditor = async () => {
  if (!editorContainer.value) return
  
  try {
    // 尝试动态加载 Monaco 编辑器
    const monacoModule = await import('monaco-editor')
    monaco = monacoModule.default || monacoModule
    
    // 初始化编辑器
    editor = monaco.editor.create(editorContainer.value, {
      value: form.script_content,
      language: editorLanguage.value,
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 13,
      scrollBeyondLastLine: false,
      tabSize: 2,
      wordWrap: 'on',
      fontFamily: "'JetBrains Mono', Consolas, 'Courier New', monospace",
      theme: 'vs-dark'
    })
    
    // 监听内容变化
    editor.onDidChangeModelContent(() => {
      if (editor) {
        form.script_content = editor.getValue()
      }
    })
  } catch (error) {
    console.error('Monaco editor initialization error:', error)
    ElMessage.warning('Monaco 编辑器加载失败，使用备用编辑器')
    useFallbackEditor.value = true
  }
}

onMounted(async () => {
  try {
    const [pRes, eRes] = await Promise.all([axios.get('/projects/'), axios.get('/envs/')])
    projectList.value = pRes.data; envList.value = eRes.data

    if (isEdit.value) {
      const cRes = await axios.get(`/testcases/${route.params.id}`)
      Object.assign(form, cRes.data)
    } else {
      form.script_content = TEMPLATES.typescript
    }
    
    // 确保DOM渲染完成后再初始化编辑器
    nextTick(() => {
      editorReady.value = true
      // 延迟一下确保容器已经渲染完成
      setTimeout(initEditor, 100)
    })
  } catch (e) {
    console.error('初始化错误:', e)
    // 即使出错也显示编辑器
    nextTick(() => {
      editorReady.value = true
      useFallbackEditor.value = true
    })
  }
})

onBeforeUnmount(() => {
  // 清理编辑器实例
  if (editor) {
    editor.dispose()
  }
})

const validateYaml = (content: string) => {
  if (form.script_type !== 'yaml') {
    yamlValidationError.value = ''
    yamlValidationSuccess.value = false
    return
  }
  
  try {
    yaml.load(content)
    yamlValidationError.value = ''
    yamlValidationSuccess.value = true
  } catch (error) {
    yamlValidationError.value = (error as Error).message
    yamlValidationSuccess.value = false
  }
}

const handleTypeChange = (val: string) => {
  const current = form.script_content.trim()
  const isDefault = Object.values(TEMPLATES).some((t: any) => t.trim() === current)
  if (!current || isDefault) form.script_content = TEMPLATES[val]
  
  // 更新编辑器语言
  if (editor && !useFallbackEditor.value) {
    monaco.editor.setModelLanguage(editor.getModel()!, editorLanguage.value)
  }
  
  // 验证 YAML
  validateYaml(form.script_content)
}

// 监听脚本内容变化，进行 YAML 验证
watch(
  () => form.script_content,
  (newContent) => {
    validateYaml(newContent)
  }
)

const handleBack = () => router.push('/testcases')

const handleSave = async () => {
  if (!form.name) return ElMessage.warning('请输入用例名称')
  
  // YAML 格式校验
  if (form.script_type === 'yaml') {
    validateYaml(form.script_content)
    if (yamlValidationError.value) {
      return ElMessage.error(`YAML 格式错误: ${yamlValidationError.value}`)
    }
  }
  
  saving.value = true
  try {
    if (isEdit.value) await axios.put(`/testcases/${route.params.id}`, form)
    else {
      const res = await axios.post('/testcases/', form)
      await router.replace(`/testcases/edit/${res.data.id}`)
    }
    ElMessage.success('保存成功')
    return true
  } catch (e) { ElMessage.error('保存失败'); return false }
  finally { saving.value = false }
}

const openDebugDrawer = () => {
  if (!isEdit.value) return
  debugDrawerVisible.value = true
  if (!debugStatus.value) debugLogs.value = ''
}

const startDebugRun = async () => {
  await handleSave()
  running.value = true
  debugLogs.value = ''
  debugStatus.value = 'running'
  try {
    const params = selectedEnvId.value ? { env_id: selectedEnvId.value } : {}
    const res = await axios.post(`/testcases/${route.params.id}/run`, null, { params })
    debugReportId.value = res.data.id
    pollDebugStatus()
  } catch(e) { ElMessage.error('启动失败'); running.value = false; debugStatus.value = 'failed' }
}

const handleRun = async () => {
  if (!isEdit.value) return
  running.value = true
  try {
    const res = await axios.post(`/testcases/${route.params.id}/run`)
    ElMessage.success('任务已提交')
    router.push(`/report-view/${res.data.id}`)
  } catch(e) { ElMessage.error('运行失败') }
  finally { running.value = false }
}

const handleSaveAndRun = async () => { if (await handleSave()) handleRun() }

const pollDebugStatus = async () => {
  if (!debugDrawerVisible.value) return
  try {
    const res = await axios.get(`/testcases/reports/${debugReportId.value}`)
    debugStatus.value = res.data.status
    debugLogs.value = res.data.logs
    nextTick(() => { if (consoleBoxRef.value) consoleBoxRef.value.scrollTop = consoleBoxRef.value.scrollHeight })
    if (['pending', 'running'].includes(res.data.status)) debugTimer = setTimeout(pollDebugStatus, 2000)
    else { running.value = false; if (res.data.status === 'success') ElMessage.success('调试完成') }
  } catch (e) { console.error(e) }
}

const handleCloseDebug = (done: any) => { if (debugTimer) clearTimeout(debugTimer); done() }
const openReport = () => window.open(router.resolve(`/report-view/${debugReportId.value}`).href, '_blank')
</script>

<style scoped>
.edit-container { height: 100vh; display: flex; flex-direction: column; background: #fff; margin: -20px; /* 抵消父容器padding */ }

/* 头部 */
.header-bar {
  height: 56px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;
  padding: 0 20px; background: #fff; z-index: 10;
}
.left { display: flex; align-items: center; }
.back-btn { font-size: 18px; color: #606266; margin-right: 8px; }
.divider { color: #dcdfe6; margin: 0 12px; }
.title { font-size: 16px; font-weight: 600; color: #303133; }
.ml-2 { margin-left: 8px; }
.mr-3 { margin-right: 12px; }

/* 布局 */
.main-body { flex: 1; display: flex; overflow: hidden; background: #f9fafb; }

/* 左侧表单 */
.left-panel {
  width: 360px; background: #fff; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column;
  padding: 20px; box-sizing: border-box;
}
.setting-form { padding-right: 10px; }
.w-100 { width: 100%; }
.mt-4 { margin-top: 16px; }
.type-radio :deep(.el-radio-button__inner) { width: 100%; padding: 8px 0; }
.type-radio :deep(.el-radio-button) { flex: 1; display: flex; }
.tips-wrapper { margin-top: 12px; }
.action-footer { margin-top: 30px; }

/* 右侧编辑器 */
.right-panel { flex: 1; display: flex; flex-direction: column; background: #1e1e1e; }
.editor-header {
  height: 40px; background: #252526; display: flex; justify-content: space-between; align-items: center;
  padding: 0 16px; border-bottom: 1px solid #333;
}
.file-tab { color: #e0e0e0; font-size: 13px; display: flex; align-items: center; background: #1e1e1e; height: 100%; padding: 0 12px; border-top: 2px solid #409eff; }
.editor-tip { color: #666; font-size: 12px; }
.monaco-container { flex: 1; overflow: hidden; }
.monaco-editor { width: 100%; height: 100%; }
.fallback-editor {
  width: 100%;
  height: 100%;
  padding: 10px;
  border: none;
  outline: none;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: none;
  background-color: #1e1e1e;
  color: #d4d4d4;
  tab-size: 2;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.fallback-editor.script-typescript {
  /* TypeScript 特定样式 */
}

.fallback-editor.script-yaml {
  /* YAML 特定样式 */
}

.editor-loading {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  color: #666;
  background: #1e1e1e;
}
.editor-loading .el-icon {
  font-size: 24px;
}

/* 调试抽屉 */
.debug-layout { height: 100%; display: flex; flex-direction: column; padding: 0 20px 20px; }
.debug-toolbar { display: flex; gap: 12px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #f2f2f2; }
.env-desc { float: right; color: #8492a6; font-size: 12px; margin-left: 10px; }

.status-banner {
  padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; margin-bottom: 16px;
}
.status-banner.running { background: #fdf6ec; color: #e6a23c; }
.status-banner.success { background: #f0f9eb; color: #67c23a; }
.status-banner.failed { background: #fef0f0; color: #f56c6c; }

.status-icon { font-size: 24px; margin-right: 12px; display: flex; }
.status-text h4 { margin: 0; font-size: 14px; font-weight: 700; }
.status-text span { font-size: 12px; opacity: 0.8; }

.console-wrapper { flex: 1; background: #1e1e1e; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.console-header { background: #333; color: #aaa; font-size: 11px; padding: 6px 12px; font-weight: bold; border-bottom: 1px solid #444; }
.console-body { flex: 1; overflow: auto; padding: 12px; color: #d4d4d4; font-family: monospace; font-size: 12px; }
.console-body pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
.drawer-footer { margin-top: 16px; }

/* YAML 校验状态 */
.validation-status {
  padding: 10px 16px;
  background: #252526;
  border-top: 1px solid #333;
}

.validation-status :deep(.el-alert) {
  margin: 0;
  font-size: 12px;
}

.validation-status :deep(.el-alert__title) {
  font-size: 12px;
  font-weight: normal;
}

.validation-status :deep(.el-alert__content) {
  font-size: 11px;
  line-height: 1.4;
  margin-top: 4px;
}
</style>