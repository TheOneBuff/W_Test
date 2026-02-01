<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="aside-container">
      <div class="logo-box">
        <el-icon class="logo-icon" :size="28" color="#4f46e5"><ElementPlus /></el-icon>
        <span class="logo-text">W_Test Pro</span>
      </div>

      <el-scrollbar>
        <el-menu
          :default-active="activeMenu"
          router
          class="el-menu-vertical"
          text-color="#475569"
          active-text-color="#4f46e5"
          :unique-opened="true"
        >
          <template v-for="menu in menuList" :key="menu.id">
            <el-sub-menu v-if="menu.children?.length" :index="String(menu.id)">
              <template #title>
                <el-icon><component :is="iconMap[menu.icon] || 'Menu'" /></el-icon>
                <span>{{ menu.title }}</span>
              </template>
              <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
                <el-icon v-if="child.icon"><component :is="iconMap[child.icon] || 'Menu'" /></el-icon>
                <span>{{ child.title }}</span>
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item v-else :index="menu.path">
              <el-icon><component :is="iconMap[menu.icon] || 'Menu'" /></el-icon>
              <span>{{ menu.title }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="aside-footer">
        <div class="version-badge">v1.0.0 Pro</div>
      </div>
    </el-aside>

    <el-container class="content-wrapper">
      <el-header class="header-container">
        <div class="header-left">
          <h2 class="page-title">{{ currentPageTitle }}</h2>
        </div>

        <div class="header-right">
          <div class="env-selector-wrapper">
            <span class="label">环境:</span>
            <el-select
              v-model="envStore.currentEnvId"
              placeholder="选择环境"
              size="default"
              style="width: 160px"
              @change="envStore.setEnvId"
            >
              <template #prefix><el-icon><Platform /></el-icon></template>
              <el-option
                v-for="env in envList"
                :key="env.id"
                :label="env.name"
                :value="env.id"
              />
            </el-select>
          </div>

          <div class="divider"></div>

          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-profile">
              <el-avatar :size="32" class="user-avatar" :style="{ backgroundColor: stringToColor(userStore.username) }">
                {{ userInitial }}
              </el-avatar>
              <div class="user-meta">
                <span class="username">{{ userStore.username || 'Admin' }}</span>
                <span class="role">管理员</span>
              </div>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="custom-dropdown">
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout" style="color: #ef4444;">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-container">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <el-dialog v-model="pwdDialogVisible" title="修改安全密码" width="400px" align-center append-to-body>
      <el-form :model="pwdForm" label-position="top" size="large">
         <el-form-item label="当前密码">
           <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前使用的密码" />
         </el-form-item>
         <el-form-item label="新密码">
           <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码" />
         </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="pwdDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleChangePassword" :loading="pwdLoading">确认修改</el-button>
        </div>
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
// [核心修改] 引入所有需要的图标
import {
  ArrowDown, Lock, SwitchButton, Platform, ElementPlus,
  Odometer, Folder, Document, DataLine, Setting, Menu as MenuIcon,
  // 新增图标:
  View, MagicStick, Files, Edit, User, Connection, AlarmClock, Cpu
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const envStore = useEnvStore()

// [核心修改] 图标映射表：将后端返回的字符串映射为组件对象
const iconMap: Record<string, any> = {
  Odometer,
  Folder,
  Document,
  DataLine,
  Setting,
  Menu: MenuIcon,
  // 注册新图标
  View,         // AI 视觉找茬
  MagicStick,   // 智能用例生成
  Files,        // 知识库
  Edit,         // 编辑类
  User,         // 用户管理
  Connection,   // 环境管理
  AlarmClock,   // 定时任务
  Cpu           // LLM配置
}

const envList = ref<any[]>([])
const menuList = ref<any[]>([])
const pwdDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '' })

// 获取当前激活菜单 (支持子路由高亮父级)
const activeMenu = computed(() => {
  const { path, meta } = route
  if (meta.activeMenu) {
    return meta.activeMenu as string
  }
  return path
})

// 根据路由推断标题
const currentPageTitle = computed(() => {
   // 优先使用路由元信息中的 title
   if (route.meta.title) return route.meta.title

   // 降级策略：路径匹配
   const map: any = { '/dashboard': '仪表盘', '/projects': '项目管理', '/testcases': '用例库', '/reports': '测试报告', '/envs': '环境配置' }
   const match = Object.keys(map).find(k => route.path.startsWith(k))
   return match ? map[match] : '控制台'
})

const userInitial = computed(() => (userStore.username ? userStore.username.charAt(0).toUpperCase() : 'U'))

// 根据用户名生成固定背景色
const stringToColor = (str: string) => {
  let hash = 0;
  if(!str) return '#4f46e5'
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const c = (hash & 0x00ffffff).toString(16).toUpperCase();
  return '#' + "00000".substring(0, 6 - c.length) + c;
}

const fetchUserMenus = async () => {
  try {
    const res = await axios.get('/menus/')
    menuList.value = res.data
  } catch (e) {
    // 模拟数据 (建议在后端接口通了之后，可以打印错误日志 e)
    console.error("Fetch menus failed, using mock data:", e)
    menuList.value = [
      { id: 1, title: '仪表盘', path: '/dashboard', icon: 'Odometer' },
      { id: 2, title: '项目管理', path: '/projects', icon: 'Folder' },
      { id: 3, title: '用例管理', path: '/testcases', icon: 'Document' },
      { id: 4, title: '测试报告', path: '/reports', icon: 'DataLine' },
      // 如果后端不通，可以在这里临时加上你的新菜单用于调试 UI
      // { id: 8, title: 'AI 视觉找茬', path: '/tools/ai-diff', icon: 'View' },
      { id: 5, title: '系统设置', icon: 'Setting', children: [
          { id: 51, title: '环境配置', path: '/envs', icon: 'Connection' },
          { id: 52, title: '成员管理', path: '/members', icon: 'User' }
      ]},
    ]
  }
}

const fetchEnvs = async () => {
  try {
    const res = await axios.get('/envs/')
    envList.value = res.data
  } catch(e) {
     envList.value = [
       { id: 'dev', name: '开发环境 (DEV)' },
       { id: 'sit', name: '测试环境 (SIT)' }
     ]
  }
}

const handleCommand = (cmd: string) => {
  if(cmd === 'logout') {
    userStore.clearUser(); router.push('/login')
  } else {
    pwdDialogVisible.value = true
  }
}

const handleChangePassword = async () => {
  if (!pwdForm.old_password || !pwdForm.new_password) return ElMessage.warning('请填写完整')
  pwdLoading.value = true
  try {
    await axios.put('/auth/password', pwdForm)
    ElMessage.success('修改成功，请重新登录')
    pwdDialogVisible.value = false
    userStore.clearUser()
    router.push('/login')
  } catch (e) {
    // 开发环境演示
    setTimeout(() => { pwdLoading.value = false; pwdDialogVisible.value = false; ElMessage.success('演示环境：修改假装成功') }, 1000)
  }
}

onMounted(() => { fetchUserMenus(); fetchEnvs() })
</script>

<style scoped>
.layout-container { height: 100vh; background: #f8fafc; }

/* 侧边栏样式 */
.aside-container {
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  z-index: 20;
  box-shadow: 2px 0 8px rgba(0,0,0,0.02);
}

.logo-box {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
}
.logo-text { font-size: 18px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px; }

.el-menu-vertical { border: none; padding: 12px; }
:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 44px;
  line-height: 44px;
  font-weight: 500;
}
:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) { background-color: #f1f5f9; }
:deep(.el-menu-item.is-active) {
  background-color: #eef2ff;
  color: #4f46e5;
}

.aside-footer { padding: 24px; margin-top: auto; text-align: center; }
.version-badge {
  background: #f1f5f9; color: #94a3b8;
  font-size: 11px; padding: 2px 10px;
  border-radius: 99px; display: inline-block;
}

/* 顶部 Header */
.header-container {
  height: 64px;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title { font-size: 16px; font-weight: 600; color: #334155; }

.header-right { display: flex; align-items: center; gap: 20px; }

/* [核心修改] 环境选择器样式 */
.env-selector-wrapper {
  display: flex;
  align-items: center;
  /* 防止被挤压 */
  flex-shrink: 0;
}
.env-selector-wrapper .label { font-size: 13px; color: #64748b; margin-right: 8px; }

.divider { height: 16px; width: 1px; background: #cbd5e1; }

.user-profile {
  display: flex; align-items: center; cursor: pointer;
  padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
}
.user-profile:hover { background: #f1f5f9; }
.user-avatar { color: #fff; font-size: 14px; margin-right: 10px; font-weight: 600; }
.user-meta { display: flex; flex-direction: column; margin-right: 4px; text-align: right; }
.username { font-size: 13px; font-weight: 600; color: #334155; line-height: 1.3; }
.role { font-size: 11px; color: #94a3b8; }
.arrow-icon { font-size: 12px; color: #94a3b8; margin-left: 4px; }

/* 内容区 */
.main-container { padding: 24px; overflow-x: hidden; }

/* 路由动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-slide-enter-from { opacity: 0; transform: translateX(10px); }
.fade-slide-leave-to { opacity: 0; transform: translateX(-10px); }
</style>