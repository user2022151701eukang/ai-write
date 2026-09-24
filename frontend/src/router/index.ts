import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/papers',
    name: 'PaperList',
    component: () => import('@/views/PaperList.vue'),
    meta: { title: '我的论文', requiresAuth: true }
  },
  {
    path: '/papers/create',
    name: 'PaperCreate',
    component: () => import('@/views/PaperCreate.vue'),
    meta: { title: '创建论文', requiresAuth: true }
  },
  {
    path: '/papers/:id/edit',
    name: 'PaperEdit',
    component: () => import('@/views/PaperEdit.vue'),
    meta: { title: '论文工作台', requiresAuth: true }
  },
  {
    path: '/references',
    name: 'ReferenceManage',
    component: () => import('@/views/ReferenceManage.vue'),
    meta: { title: '文献管理', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/** 全局前置守卫：标题与登录校验 */
router.beforeEach((to, _from, next) => {
  const title = (to.meta.title as string) || 'AI 论文写作系统'
  document.title = `${title} | AI 论文写作系统`

  const token = localStorage.getItem('ai_paper_token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }
  next()
})

export default router