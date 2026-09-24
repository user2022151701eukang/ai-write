import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

/** 接口基础地址（默认走 vite 代理 /api） */
export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

/** 后端服务地址（去掉 /api 后缀，用于 /health 等非 API 路径） */
export const SERVER_BASE = API_BASE.replace(/\/api\/?$/, '')

const TOKEN_KEY = 'ai_paper_token'

/** 读取本地保存的 token */
export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/** 保存 token */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 清除 token */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

const service: AxiosInstance = axios.create({
  baseURL: API_BASE,
  // 流式生成接口耗时可能几分钟，超时设置为 10 分钟
  timeout: 600000
})

// 请求拦截器：自动注入 Authorization
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：统一错误处理
service.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    const response = error.response
    if (response?.status === 401) {
      clearToken()
      ElMessage.error('登录已过期，请重新登录')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    } else {
      ElMessage.error(response?.data?.detail || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default service