import request from './request'

/** 用户信息 */
export interface User {
  id: number
  username: string
  email: string
  created_at?: string
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

/** 注册参数 */
export interface RegisterData {
  username: string
  email: string
  password: string
}

/** 登录 */
export function login(username: string, password: string) {
  return request.post<any, LoginResponse>('/auth/login', { username, password })
}

/** 注册 */
export function register(data: RegisterData) {
  return request.post<any, User>('/auth/register', data)
}

/** 获取当前登录用户信息 */
export function getCurrentUser() {
  return request.get<any, User>('/auth/me')
}