import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getCurrentUser, login as loginApi, register as registerApi } from '@/api/auth'
import type { RegisterData, User } from '@/api/auth'
import { clearToken, getToken, setToken } from '@/api/request'

/** 用户状态管理 */
export const useUserStore = defineStore('user', () => {
  // localStorage 持久化 token
  const token = ref<string>(getToken())
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')

  /** 保存 token 到内存与本地存储 */
  function saveToken(value: string) {
    token.value = value
    setToken(value)
  }

  /** 登录并拉取用户信息 */
  async function login(name: string, password: string) {
    const res = await loginApi(name, password)
    saveToken(res.access_token)
    user.value = res.user
    await fetchCurrentUser()
    return res
  }

  /** 注册（注册接口返回用户对象，需再登录一次获取 token） */
  async function register(data: RegisterData) {
    const created = await registerApi(data)
    await login(data.username, data.password)
    return created
  }

  /** 拉取当前用户信息 */
  async function fetchCurrentUser() {
    if (!token.value) {
      user.value = null
      return null
    }
    try {
      user.value = await getCurrentUser()
      return user.value
    } catch (e) {
      user.value = null
      return null
    }
  }

  /** 退出登录 */
  function logout() {
    token.value = ''
    user.value = null
    clearToken()
  }

  return {
    token,
    user,
    isLoggedIn,
    username,
    login,
    register,
    logout,
    fetchCurrentUser
  }
})