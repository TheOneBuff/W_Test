import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEnvStore = defineStore('env', () => {
  // 从 localStorage 初始化，刷新页面不丢失
  const currentEnvId = ref<number | null>(
    localStorage.getItem('globalEnvId') ? Number(localStorage.getItem('globalEnvId')) : null
  )

  const setEnvId = (id: number | null) => {
    currentEnvId.value = id
    if (id) {
      localStorage.setItem('globalEnvId', String(id))
    } else {
      localStorage.removeItem('globalEnvId')
    }
  }

  return { currentEnvId, setEnvId }
})
