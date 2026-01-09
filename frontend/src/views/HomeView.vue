<template>
  <el-container class="layout-container">
    <!-- 左侧侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon class="logo-icon"><Platform /></el-icon>
        <span>UI自动化平台</span>
      </div>

      <!-- 动态菜单 -->
      <el-menu
        :default-active="$route.path"
        router
        class="el-menu-vertical"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
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
    </el-aside>

    <!-- 右侧主体区域 -->
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="left-panel">
          <!-- 面包屑预留 -->
        </div>

        <div class="right-panel">
          <!-- === 新增：全局环境选择器 === -->
          <div class="env-wrapper">
            <span class="env-label">运行环境:</span>
            <el-select
              v-model="envStore.currentEnvId"
              placeholder="默认环境 (无变量)"
              clearable
              style="width: 180px"
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
          <!-- ========================== -->

          <el-dropdown @command="handleCommand" trigger="click">
            <span class="el-dropdown-link">
              <el-avatar :size="32" class="avatar">{{ userInitial }}</el-avatar>
              <span class="username">{{ userStore.username }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password"><el-icon><Lock /></el-icon>修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主要内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px" destroy-on-close>
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
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useEnvStore } from '@/stores/env' // 引入 Env Store
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { ArrowDown, Platform, Lock, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const envStore = useEnvStore()

// --- 1. 环境列表逻辑 ---
const envList = ref<any[]>([])
const fetchEnvs = async () => {
  try {
    const res = await axios.get('/envs/')
    envList.value = res.data
  } catch(e) { console.error(e) }
}

// --- 2. 菜单逻辑 ---
const menuList = ref<any[]>([])
const fetchUserMenus = async () => {
  try {
    const res = await axios.get('/menus/')
    menuList.value = res.data
  } catch (e) { console.error(e) }
}

// --- 3. 用户逻辑 ---
const userInitial = computed(() => userStore.username ? userStore.username.charAt(0).toUpperCase() : 'U')

const handleCommand = (command: string) => {
  if (command === 'logout') handleLogout()
  else if (command === 'password') pwdDialogVisible.value = true
}

const handleLogout = () => {
  userStore.clearUser()
  router.push('/login')
  ElMessage.success('已退出登录')
}

// --- 4. 修改密码 ---
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
  } finally { pwdLoading.value = false }
}

onMounted(() => {
  fetchUserMenus()
  fetchEnvs() // 加载环境
})
</script>

<style scoped>
.layout-container { height: 100vh; width: 100%; }
.aside { background-color: #304156; color: #fff; display: flex; flex-direction: column; }
.logo { height: 60px; line-height: 60px; background-color: #2b3649; text-align: center; font-weight: bold; font-size: 18px; color: #fff; display: flex; align-items: center; justify-content: center; gap: 10px; }
.logo-icon { font-size: 22px; color: #409EFF; }
.el-menu-vertical { border-right: none; width: 100%; }

.header { background: #fff; border-bottom: 1px solid #e6e6e6; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; height: 60px; box-shadow: 0 1px 4px rgba(0,21,41,.08); }
.right-panel { display: flex; align-items: center; }

/* 环境选择器样式 */
.env-wrapper { margin-right: 20px; display: flex; align-items: center; }
.env-label { font-size: 14px; color: #606266; margin-right: 8px; font-weight: 500; }

.el-dropdown-link { cursor: pointer; display: flex; align-items: center; color: #606266; padding: 5px; border-radius: 4px; }
.el-dropdown-link:hover { background: #f5f7fa; }
.avatar { background: #409EFF; margin-right: 8px; font-size: 14px; }
.username { font-weight: 500; font-size: 14px; margin-right: 4px; }

.main-content { background-color: #f0f2f5; padding: 20px; position: relative; overflow-y: auto; }
.fade-transform-enter-active, .fade-transform-leave-active { transition: all 0.3s; }
.fade-transform-enter-from { opacity: 0; transform: translateX(-10px); }
.fade-transform-leave-to { opacity: 0; transform: translateX(10px); }
</style>
