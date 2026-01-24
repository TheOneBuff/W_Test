<template>
  <div class="login-container">
    <div class="background-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
    </div>

    <div class="login-content">
      <div class="brand-section">
        <div class="logo-circle">
          <img src="@/assets/logo.svg" alt="Logo" />
        </div>
        <h1>MidScene</h1>
        <p>新一代智能自动化测试平台</p>
      </div>

      <div class="form-section">
        <div class="form-header">
          <h3>欢迎回来</h3>
          <span class="subtitle">请登录您的账号</span>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          size="large"
          class="login-form"
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
            class="submit-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>

          <div class="tips">
            默认账号: <span>admin</span> / <span>123456</span>
          </div>
        </el-form>
      </div>
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
    ElMessage.success('登录成功')
    router.push('/')
  } catch(e) {
    ElMessage.error('登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f3f4f6;
  position: relative;
  overflow: hidden;
}

/* 动态背景图形 */
.background-shapes .shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.6;
}
.shape-1 {
  top: -100px;
  right: -100px;
  width: 500px;
  height: 500px;
  background: #c7d2fe; /* Indigo-200 */
}
.shape-2 {
  bottom: -50px;
  left: -50px;
  width: 400px;
  height: 400px;
  background: #bae6fd; /* Sky-200 */
}

.login-content {
  display: flex;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-radius: 24px;
  box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 10;
  width: 800px;
  max-width: 90%;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.brand-section {
  flex: 1;
  background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
  padding: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
  text-align: center;
}

.logo-circle {
  width: 72px;
  height: 72px;
  background: white;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 10px 20px rgba(0,0,0,0.15);
}
.logo-circle img { width: 40px; }

.brand-section h1 { font-size: 26px; margin-bottom: 12px; font-weight: 700; }
.brand-section p { opacity: 0.85; font-size: 14px; }

.form-section {
  flex: 1.2;
  padding: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #fff;
}

.form-header { margin-bottom: 32px; }
.form-header h3 { font-size: 22px; color: #111827; margin-bottom: 8px; font-weight: 600; }
.subtitle { color: #6b7280; font-size: 14px; }

.submit-btn { width: 100%; height: 44px; font-size: 16px; margin-top: 10px; }

.tips {
  margin-top: 24px;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  background: #f9fafb;
  padding: 10px;
  border-radius: 8px;
}
.tips span { color: #4f46e5; font-weight: 600; font-family: monospace; }

@media (max-width: 768px) {
  .login-content { flex-direction: column; width: 400px; }
  .brand-section { padding: 30px; }
  .form-section { padding: 30px; }
}
</style>