import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import HomeView from '../views/HomeView.vue' // 布局组件
import TestCaseList from '../views/TestCaseList.vue'
import TestCaseEdit from '../views/TestCaseEdit.vue'
import ReportDetail from '../views/ReportDetail.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'
import CaseGenerator from '../views/CaseGenerator.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', component: Login },
    // --- 1. 核心布局路由 ---
    {
      path: '/',
      component: HomeView, // 父路由：加载侧边栏和顶部
      meta: { requiresAuth: true },
      // 子路由：内容会渲染在 HomeView 的 <router-view> 中
      children: [
        {
          path: '', // 空路径表示默认子路由 (即 Dashboard)
          name: 'Dashboard',
          component: () => import('../views/Dashboard.vue')
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('../views/UserManage.vue')
        },
        {
          path: 'llm',
          name: 'LLMConfig',
          component: () => import('../views/LLMConfig.vue')
        },
        {
          path: 'menus',
          name: 'MenuManage',
          component: () => import('../views/MenuManage.vue')
        },
        { path: 'testcases', component: TestCaseList },
        { path: 'testcases/create', component: TestCaseEdit },
        { path: 'testcases/edit/:id', component: TestCaseEdit },
        { path: 'reports/:id', component: ReportDetail }, // 报告页
        {
          path: 'projects',
          name: 'ProjectList',
          component: () => import('../views/ProjectList.vue')
        },
        {
          path: 'reports',
          name: 'ReportList',
          component: () => import('../views/ReportList.vue')
        },
        {
          path: 'envs',
          name: 'EnvManage',
          component: () => import('../views/EnvManage.vue')
        },
        {
          path: 'periodic',
          name: 'ScheduledTasks',
          component: () => import('../views/ScheduledTasks.vue')
        },
        {
          path: '/knowledge',
          name: 'KnowledgeBase',
          component: KnowledgeBase,
          meta: { title: '知识库管理'}
        },
        {
          path: '/generator',
          name: 'CaseGenerator',
          component: CaseGenerator,
          meta: { title: '用例生成' }
        },
          {
          path: 'testcase/result/:id',
          name: 'TestCaseResult',
          component: () => import('../views/TestCaseResult.vue'),
          meta: { title: '生成结果详情' }
        },

      ]
    },
    // --- 2. 独立页面路由 (移到这里) ---
    {
      path: '/report-view/:id', // 绝对路径
      name: 'ReportDetail',
      component: () => import('../views/ReportDetail.vue'),
      meta: { requiresAuth: true }
    },
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
