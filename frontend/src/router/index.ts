import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login
    },
    // --- 1. 核心布局路由 (带侧边栏) ---
    {
      path: '/',
      component: HomeView,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
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
        {
          path: 'projects',
          name: 'ProjectList',
          component: () => import('../views/ProjectList.vue')
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
          path: 'notifications',
          name: 'NotificationManage',
          component: () => import('../views/NotificationManage.vue')
        },
        // --- 测试用例管理 ---
        {
          path: 'testcases',
          name: 'TestCaseList',
          component: () => import('../views/TestCaseList.vue')
        },
        {
          path: 'testcases/create',
          name: 'TestCaseCreate',
          component: () => import('../views/TestCaseEdit.vue')
        },
        {
          path: 'testcases/edit/:id',
          name: 'TestCaseEdit',
          component: () => import('../views/TestCaseEdit.vue')
        },
        {
          path: 'testcase/result/:id',
          name: 'TestCaseResult',
          component: () => import('../views/TestCaseResult.vue'),
          meta: { title: '生成结果详情' }
        },
        // --- 报告列表 (内嵌版) ---
        {
          path: 'reports',
          name: 'ReportList',
          component: () => import('../views/ReportList.vue')
        },
        {
          path: 'reports/:id',
          name: 'ReportDetailEmbedded',
          component: () => import('../views/ReportDetail.vue')
        },
        // --- 知识库 ---
        {
          path: '/knowledge',
          name: 'KnowledgeBase',
          component: () => import('../views/KnowledgeBase.vue'),
          meta: { title: '知识库管理'}
        },
        // --- AI 工具组 ---
        {
          path: '/generator',
          name: 'CaseGenerator',
          component: () => import('../views/CaseGenerator.vue'),
          meta: { title: '用例生成' }
        },
        {
          path: '/skills',
          name: 'SkillManage',
          component: () => import('../views/SkillManage.vue'),
          meta: { title: '技能管理' }
        },
        {
          path: '/tools/ai-diff',
          name: 'AiDiff',
          component: () => import('../views/AiDiff.vue'), // 动态加载
          meta: { title: 'AI 视觉找茬' }
        },
        // --- 素材管理 ---
        {
          path: '/materials',
          name: 'MaterialUpload',
          component: () => import('../views/MaterialUpload.vue'),
          meta: { title: '素材管理' }
        },
        // --- 执行器管理 ---
        {
          path: 'executors',
          name: 'ExecutorManage',
          component: () => import('../views/ExecutorManage.vue'),
          meta: { title: '执行器管理' }
        }
      ]
    },
    // --- 2. 独立页面路由 (全屏显示，无侧边栏) ---
    {
      path: '/report-view/:id',
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