/**
 * 认证工具函数
 *
 * usesCookie: 后端同时通过 Set-Cookie 写入 httpOnly 的 app2docker_token，
 * 与 Bearer 并行；浏览器无法读取该 Cookie，需 axios.defaults.withCredentials=true。
 *
 * localStorage/sessionStorage 仍保留 token，供 Authorization 头向后兼容。
 */

/**
 * 获取存储的 token
 */
export function getToken() {
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
}

/**
 * 获取当前用户名
 */
export function getUsername() {
  return localStorage.getItem('username') || sessionStorage.getItem('username')
}

/**
 * 保存认证信息
 */
export function saveAuth(token, username, remember = true) {
  const storage = remember ? localStorage : sessionStorage
  storage.setItem('auth_token', token)
  storage.setItem('username', username)
}

/**
 * 清除认证信息
 */
export function clearAuth() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('username')
  sessionStorage.removeItem('auth_token')
  sessionStorage.removeItem('username')
}

/**
 * 检查是否已登录
 */
export function isAuthenticated() {
  return !!getToken()
}

/** 响应表示 JWT 有效但数据库中已无对应用户 */
export function isUserNotFoundResponse(error) {
  const status = error?.response?.status
  const detail = error?.response?.data?.detail
  if (typeof detail !== 'string' || !detail.includes('用户不存在')) {
    return false
  }
  return status === 401 || status === 404
}

/** 解析登录页 redirect 参数（支持 encodeURIComponent 编码的完整路径含 query） */
export function parseLoginRedirect(raw) {
  if (typeof raw !== 'string' || !raw.trim()) return ''
  let path = raw.trim()
  try {
    path = decodeURIComponent(path)
  } catch {
    /* 保持原值 */
  }
  return path.startsWith('/') ? path : ''
}

/** 清除本地会话并跳转登录页 */
export function redirectToLoginAfterStaleSession() {
  const { pathname, search } = window.location
  clearAuth()
  const redirect = encodeURIComponent(`${pathname}${search}`)
  const base = import.meta.env.BASE_URL || '/'
  const loginPath = `${base.replace(/\/$/, '')}/login`
  if (pathname.endsWith('/login') || pathname.endsWith('/register')) {
    window.location.reload()
    return
  }
  window.location.href = `${loginPath}?redirect=${redirect}`
}

/**
 * 登出
 */
export async function logout() {
  try {
    const axios = (await import('axios')).default
    await axios.post('/api/logout')
  } catch (error) {
    console.error('登出请求失败:', error)
  } finally {
    clearAuth()
  }
}

