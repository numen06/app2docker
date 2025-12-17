/**
 * Axios 拦截器配置
 */
import axios from 'axios'
import { clearAuth, getToken } from './auth'

/**
 * 设置 axios 拦截器
 */
export function setupAxiosInterceptors() {
  // 请求拦截器：自动添加 token
  axios.interceptors.request.use(
    (config) => {
      const token = getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  // 响应拦截器：处理认证失败
  axios.interceptors.response.use(
    (response) => {
      return response
    },
    (error) => {
      if (error.response?.status === 401) {
        // 如果是登录接口，不处理（让页面自己处理错误）
        const url = error.config?.url || ''
        const isLoginRequest = url.includes('/api/login')
        
        if (!isLoginRequest) {
          // Token 过期或无效，清除认证信息
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Token已过期，请重新登录'
          
          // 检查是否是token过期
          if (errorMessage.includes('过期') || errorMessage.includes('expired')) {
            console.warn('⚠️ Token已过期，正在退出登录...')
          } else {
            console.warn('⚠️ 认证失败，正在退出登录...')
          }
          
          // 清除认证信息
          clearAuth()
          
          // 重新加载页面，跳转到登录页
          window.location.reload()
        }
      }
      return Promise.reject(error)
    }
  )
}

