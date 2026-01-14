<template>
  <div class="login-wrapper">
    <div class="login-box">
      <div class="header">
        <img src="@/assets/logo.svg" alt="Logo" class="logo" />
        <h2 class="title">MidScene Admin</h2>
        <p class="subtitle">新一代 UI 自动化测试平台</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        class="login-form"
        size="large"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-button
          type="primary"
          :loading="loading"
          class="submit-btn"
          @click="handleLogin"
        >
          登 录
        </el-button>

        <div class="footer-tips">
          <span>默认账号: admin / 123456</span>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const handleLogin = async () => {
  if (!form.username || !form.password) return ElMessage.warning('请输入账号密码')

  loading.value = true
  const formData = new FormData()
  formData.append('username', form.username)
  formData.append('password', form.password)

  try {
    const res = await axios.post('/auth/token', formData)
    localStorage.setItem('token', res.data.access_token)
    userStore.setUsername(form.username)
    ElMessage.success('登录成功，欢迎回来')
    router.push('/')
  } catch(e) {
    ElMessage.error('登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-size: cover;
}

.login-box {
  width: 420px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  text-align: center;
  transition: transform 0.3s;
}
.login-box:hover { transform: translateY(-5px); }

.logo { width: 64px; height: 64px; margin-bottom: 16px; }
.title { font-size: 24px; font-weight: 700; color: #1f2937; margin: 0 0 8px; }
.subtitle { font-size: 14px; color: #6b7280; margin: 0 0 32px; }

.login-form { margin-top: 24px; }
.submit-btn { width: 100%; font-weight: 600; letter-spacing: 1px; height: 44px; font-size: 16px; background: linear-gradient(to right, #6366f1, #8b5cf6); border: none; }
.submit-btn:hover { opacity: 0.9; }

.footer-tips { margin-top: 20px; font-size: 12px; color: #9ca3af; }
</style>