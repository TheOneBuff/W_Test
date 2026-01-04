import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 从 localStorage 初始化，防止刷新页面后名字消失
  const username = ref(localStorage.getItem('username') || '')

  function setUsername(name: string) {
    username.value = name
    localStorage.setItem('username', name)
  }

  function clearUser() {
    username.value = ''
    localStorage.removeItem('username')
    localStorage.removeItem('token')
  }

  return { username, setUsername, clearUser }
})
