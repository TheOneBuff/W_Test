<template>
  <div class="login-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <h2>Midscene Admin</h2>
        </div>
      </template>
      <el-form label-position="top">
        <el-form-item label="Username">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="form.password" type="password" placeholder="123456" show-password @keyup.enter="handleLogin"/>
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="handleLogin" style="width:100%">
          Login
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/request'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const userStore = useUserStore() // 2. 初始化

const handleLogin = async () => {
  loading.value = true
  const formData = new FormData()
  formData.append('username', form.username)
  formData.append('password', form.password)

  try {
    const res = await axios.post('/auth/token', formData)
    localStorage.setItem('token', res.data.access_token)
    // 保存用户名 (这里简单直接用填写的用户名，严谨做法是解析Token或调用/me接口)
    userStore.setUsername(form.username)
    ElMessage.success('Login Successfully')
    router.push('/')
  } catch(e) {
    ElMessage.error('Login Failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f2f5;
}
.box-card {
  width: 400px;
}
h2 {
  text-align: center;
  margin: 0;
}
</style>
