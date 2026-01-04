import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus' // 1. 引入组件库
import 'element-plus/dist/index.css'   // 2. 引入关键样式文件！
import * as ElementPlusIconsVue from '@element-plus/icons-vue' // 引入图标

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus) // 3. 全局安装

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
