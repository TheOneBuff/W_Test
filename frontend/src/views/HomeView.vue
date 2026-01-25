<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="aside-container">
      <div class="logo-box">
        <span class="logo-text">W_Test</span>
      </div>

      <el-scrollbar>
        <el-menu
          :default-active="$route.path"
          router
          class="el-menu-vertical"
          text-color="#4b5563"
          active-text-color="#4f46e5"
          :unique-opened="true"
        >
          <template v-for="menu in menuList" :key="menu.id">
            <el-sub-menu v-if="menu.children?.length" :index="String(menu.id)">
              <template #title>
                <el-icon><component :is="menu.icon" /></el-icon>
                <span>{{ menu.title }}</span>
              </template>
              <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
                <span>{{ child.title }}</span>
              </el-menu-item>
            </el-sub-menu>
            
            <el-menu-item v-else :index="menu.path">
              <el-icon><component :is="menu.icon" /></el-icon>
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
          <div class="env-selector">
            <span class="label">环境</span>
            <el-select
              v-model="envStore.currentEnvId"
              placeholder="选择环境"
              class="env-select"
              size="small"
              @change="envStore.setEnvId"
            >
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
              <el-avatar :size="32" class="user-avatar">{{ userInitial }}</el-avatar>
              <div class="user-meta">
                <span class="username">{{ userStore.username }}</span>
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

    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px" align-center>
      <el-form :model="pwdForm" label-position="top" size="large">
         <el-form-item label="旧密码">
           <el-input v-model="pwdForm.old_password" type="password" show-password />
         </el-form-item>
         <el-form-item label="新密码">
           <el-input v-model="pwdForm.new_password" type="password" show-password />
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
import { 
  ArrowDown, Lock, SwitchButton, 
  Odometer, Folder, Document, DataLine, Setting, Menu as MenuIcon 
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const envStore = useEnvStore()

const envList = ref<any[]>([])
const menuList = ref<any[]>([])
const pwdDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '' })

// 模拟或获取菜单数据
const fetchUserMenus = async () => {
  try {
    const res = await axios.get('/menus/')
    menuList.value = res.data.map((m: any) => ({
      ...m,
      icon: m.icon || 'Menu',
      children: m.children?.map((c: any) => ({ ...c, icon: c.icon || 'Document' }))
    }))
  } catch (e) {
    // 默认菜单
    menuList.value = [
      { id: 1, title: '仪表盘', path: '/dashboard', icon: 'Odometer' },
      { id: 2, title: '项目管理', path: '/projects', icon: 'Folder' },
      { id: 3, title: '用例管理', path: '/testcases', icon: 'Document' },
      { id: 4, title: '测试报告', path: '/reports', icon: 'DataLine' },
      { id: 5, title: '环境配置', path: '/envs', icon: 'Setting' },
    ]
  }
}

const fetchEnvs = async () => {
  try {
    const res = await axios.get('/envs/')
    envList.value = res.data
  } catch(e) {}
}

const userInitial = computed(() => userStore.username ? userStore.username.charAt(0).toUpperCase() : 'U')
const currentPageTitle = computed(() => {
   const map: any = { '/dashboard': '仪表盘', '/testcases': '用例库', '/reports': '测试报告' }
   const match = Object.keys(map).find(k => route.path.includes(k))
   return match ? map[match] : '控制台'
})

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
  } catch (e) { ElMessage.error('修改失败') }
  finally { pwdLoading.value = false }
}

onMounted(() => { fetchUserMenus(); fetchEnvs() })
</script>

<style scoped>
.layout-container { height: 100vh; background: #f8fafc; }

/* 侧边栏优化 */
.aside-container {
  background: #ffffff;
  border-right: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  z-index: 20;
}

.logo-box {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  /* border-bottom: 1px solid #f8fafc; */
}
.logo-img { width: 32px; height: 32px; margin-right: 12px; }
.logo-text { font-size: 20px; font-weight: 700; color: #1e293b; letter-spacing: -0.5px; }

.el-menu-vertical { border: none; padding: 12px; }
:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 48px;
  line-height: 48px;
}
:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) { background-color: #f8fafc; }
:deep(.el-menu-item.is-active) {
  background-color: #eef2ff;
  color: #4f46e5;
  font-weight: 600;
}
:deep(.el-menu-item .el-icon) { font-size: 18px; margin-right: 12px; }

.aside-footer { padding: 24px; margin-top: auto; text-align: center; }
.version-badge { 
  background: #f1f5f9; color: #64748b; 
  font-size: 12px; padding: 4px 12px; 
  border-radius: 12px; display: inline-block; 
}

/* 顶部 Header */
.header-container {
  height: 64px;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title { font-size: 18px; font-weight: 600; color: #1e293b; }

.header-right { display: flex; align-items: center; gap: 16px; }

.env-selector { 
  display: flex; align-items: center; 
  background: #fff; border: 1px solid #e2e8f0;
  padding: 2px 2px 2px 10px; border-radius: 6px; 
}
.env-selector .label { font-size: 12px; color: #64748b; margin-right: 6px; }
:deep(.env-select .el-input__wrapper) { box-shadow: none !important; padding: 0 8px !important; }

.divider { height: 20px; width: 1px; background: #e2e8f0; margin: 0 8px; }

.user-profile {
  display: flex; align-items: center; cursor: pointer;
  padding: 6px; border-radius: 8px; transition: all 0.2s;
}
.user-profile:hover { background: #f1f5f9; }
.user-avatar { background: #4f46e5; font-size: 14px; margin-right: 10px; }
.user-meta { display: flex; flex-direction: column; margin-right: 8px; }
.username { font-size: 14px; font-weight: 500; color: #334155; line-height: 1.2; }
.role { font-size: 11px; color: #94a3b8; }
.arrow-icon { font-size: 12px; color: #94a3b8; }

/* 主内容区 */
.main-container { padding: 32px; overflow-x: hidden; }

/* 路由动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.25s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(8px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>