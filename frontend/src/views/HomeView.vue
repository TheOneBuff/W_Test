<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside-container">
      <div class="logo-box">
        <img src="@/assets/logo.svg" alt="Logo" class="logo-img" />
        <span class="logo-text">MidScene 平台</span>
      </div>

      <el-scrollbar>
        <el-menu
          :default-active="$route.path"
          router
          class="el-menu-vertical"
          background-color="#1f2937"
          text-color="#9ca3af"
          active-text-color="#ffffff"
          :unique-opened="false"
          :collapse-transition="false"
        >
          <template v-for="menu in menuList" :key="menu.id">
            <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="String(menu.id)">
              <template #title>
                <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
                <span>{{ menu.title }}</span>
              </template>
              <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
                <el-icon v-if="child.icon"><component :is="child.icon" /></el-icon>
                <span>{{ child.title }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="menu.path">
              <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
              <span>{{ menu.title }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container>
      <el-header class="header-container">
        <div class="header-left">
          <h2 class="page-title">{{ currentPageTitle }}</h2>
        </div>

        <div class="header-right">
          <div class="env-selector">
            <span class="env-label">环境:</span>
            <el-select
              v-model="envStore.currentEnvId"
              placeholder="默认环境"
              clearable
              style="width: 160px"
              @change="envStore.setEnvId"
              size="default"
            >
              <el-option
                v-for="env in envList"
                :key="env.id"
                :label="env.name"
                :value="env.id"
              />
            </el-select>
          </div>

          <el-dropdown @command="handleCommand" trigger="click" class="user-dropdown">
            <div class="user-info">
              <el-avatar :size="32" class="user-avatar">{{ userInitial }}</el-avatar>
              <span class="user-name">{{ userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password"><el-icon><Lock /></el-icon>修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout" style="color: #f56c6c;">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-container">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px" destroy-on-close append-to-body>
      <el-form :model="pwdForm" label-width="80px" @submit.prevent>
        <el-form-item label="旧密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword" :loading="pwdLoading">提交</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useEnvStore } from '@/stores/env'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import {
  ArrowDown, Lock, SwitchButton,
  Odometer, Folder, Document, DataLine, Timer, Setting, User as UserIcon, Menu as MenuIcon
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const envStore = useEnvStore()

// --- 环境列表逻辑 ---
const envList = ref<any[]>([])
const fetchEnvs = async () => {
  try {
    const res = await axios.get('/envs/')
    envList.value = res.data
  } catch(e) { console.error(e) }
}

// --- 菜单逻辑 ---
const menuList = ref<any[]>([])
const fetchUserMenus = async () => {
  try {
    const res = await axios.get('/menus/')
    menuList.value = res.data.map((m: any) => ({
      ...m,
      icon: m.icon || 'Menu',
      children: m.children?.map((c: any) => ({ ...c, icon: c.icon || 'Document' }))
    }))
  } catch (e) {
    // Fallback 如果接口失败
    menuList.value = [
      { id: 1, title: '仪表盘', path: '/dashboard', icon: 'Odometer' },
      { id: 2, title: '项目管理', path: '/projects', icon: 'Folder' },
      { id: 3, title: '用例管理', path: '/testcases', icon: 'Document' },
      { id: 4, title: '测试报告', path: '/reports', icon: 'DataLine' },
    ]
  }
}

// --- UI 逻辑 ---
const userInitial = computed(() => userStore.username ? userStore.username.charAt(0).toUpperCase() : 'U')

const currentPageTitle = computed(() => {
  const map: Record<string, string> = {
    '/dashboard': '仪表盘',
    '/projects': '项目管理',
    '/testcases': '测试用例',
    '/reports': '测试报告',
    '/tasks': '定时任务',
    '/llm-config': '模型配置',
    '/envs': '环境管理',
    '/users': '用户管理',
    '/menus': '菜单管理'
  }
  const key = Object.keys(map).find(k => route.path.startsWith(k))
  if (route.path === '/') return '仪表盘'
  return key ? map[key] : 'MidScene'
})

const handleCommand = (command: string) => {
  if (command === 'logout') handleLogout()
  else if (command === 'password') pwdDialogVisible.value = true
}

const handleLogout = () => {
  userStore.clearUser()
  router.push('/login')
  ElMessage.success('已退出登录')
}

// --- 修改密码 ---
const pwdDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '' })

const handleChangePassword = async () => {
  if (!pwdForm.old_password || !pwdForm.new_password) return ElMessage.warning('请填写完整')
  pwdLoading.value = true
  try {
    await axios.put('/auth/password', pwdForm)
    ElMessage.success('密码修改成功，请重新登录')
    pwdDialogVisible.value = false
    handleLogout()
  } catch (error: any) {
    if (error.response?.status === 400) ElMessage.error('旧密码错误')
    else ElMessage.error('修改失败')
  } finally { pwdLoading.value = false }
}

onMounted(() => {
  fetchUserMenus()
  fetchEnvs()
})
</script>

<style scoped>
.layout-container { height: 100vh; width: 100vw; display: flex; overflow: hidden; }

/* 侧边栏样式 */
.aside-container {
  background-color: #1f2937;
  color: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 6px rgba(0,0,0,0.1);
  z-index: 10;
}

.logo-box {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background-color: #111827;
  border-bottom: 1px solid #374151;
}
.logo-img { width: 28px; height: 28px; margin-right: 12px; }
.logo-text { font-size: 18px; font-weight: 600; color: #fff; letter-spacing: 0.5px; }

.el-menu-vertical { border-right: none; flex: 1; }
:deep(.el-menu-item.is-active) {
  background-color: #374151 !important;
  border-left: 4px solid #6366f1;
  color: #fff !important;
}

/* 顶部 Header */
.header-container {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  z-index: 9;
}

.page-title { font-size: 18px; font-weight: 600; color: #1f2937; margin: 0; }

.header-right { display: flex; align-items: center; gap: 24px; }

.env-selector { display: flex; align-items: center; }
.env-label { font-size: 14px; color: #6b7280; margin-right: 8px; font-weight: 500; }

.user-info {
  display: flex; align-items: center; cursor: pointer;
  padding: 4px 8px; border-radius: 6px; transition: background 0.2s;
}
.user-info:hover { background: #f3f4f6; }
.user-avatar { background: #6366f1; margin-right: 8px; font-size: 14px; font-weight: 600; }
.user-name { font-size: 14px; font-weight: 500; color: #374151; margin-right: 6px; }

/* 主内容区 */
.main-container {
  background-color: #f3f4f6;
  padding: 24px;
  overflow-y: auto;
  overflow-x: hidden; /* 修复滚动条问题的关键 */
}

/* 页面切换动画 */
.fade-transform-enter-active,
.fade-transform-leave-active { transition: all 0.3s ease; }
.fade-transform-enter-from { opacity: 0; transform: translateX(-10px); }
.fade-transform-leave-to { opacity: 0; transform: translateX(10px); }
</style>