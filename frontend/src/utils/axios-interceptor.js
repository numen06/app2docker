/**
 * Axios 拦截器配置
 */
import axios from 'axios'
import {
  clearAuth,
  getToken,
  isUserNotFoundResponse,
  redirectToLoginAfterStaleSession,
} from './auth'
import { useTeamStore } from '@/stores/team'

const TEAM_SCOPED_API_PREFIXES = [
  '/api/pipelines',
  '/api/agent-hosts',
  '/api/deploy-configs',
  '/api/deploy-tasks',
  '/api/git-sources',
  '/api/pipeline-groups',
  '/api/host-groups',
  '/api/dashboard',
  '/api/tasks',
  '/api/build-tasks',
  '/api/export-image',
  '/api/export-tasks',
  '/api/hosts',
  '/api/resource-packages',
  '/api/registries',
  '/api/templates',
  '/api/list-templates',
  '/api/template-params',
  '/api/operation-logs',
  '/api/build-from-source',
  '/api/upload',
]

/** 管理员/全局接口，不自动附加 team_id */
const TEAM_SCOPED_EXCLUDE_PREFIXES = [
  '/api/users',
  '/api/roles',
  '/api/permissions',
  '/api/system-settings',
  '/api/agent-secrets',
  '/api/teams',
  '/api/login',
  '/api/register',
  '/api/auth/',
  '/api/public/',
]

function urlNeedsTeamScope(url) {
  if (!url) return false
  if (TEAM_SCOPED_EXCLUDE_PREFIXES.some((p) => url.includes(p))) return false
  return TEAM_SCOPED_API_PREFIXES.some((p) => url.includes(p))
}

function attachTeamId(config, teamId) {
  const method = (config.method || 'get').toLowerCase()
  const existingParams = config.params || {}
  const hasTeamInParams = existingParams.team_id != null && existingParams.team_id !== ''

  if (method === 'get' || method === 'delete') {
    if (!hasTeamInParams) {
      config.params = { ...existingParams, team_id: teamId }
    }
    return
  }

  if (['post', 'put', 'patch'].includes(method)) {
    const data = config.data
    if (data instanceof FormData) {
      if (!hasTeamInParams) {
        config.params = { ...existingParams, team_id: teamId }
      }
      return
    }
    if (data && typeof data === 'object') {
      if (!data.team_id) {
        config.data = { ...data, team_id: teamId }
      }
    } else if (!hasTeamInParams) {
      config.params = { ...existingParams, team_id: teamId }
    }
  }
}

axios.defaults.withCredentials = true

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
      try {
        const teamStore = useTeamStore()
        const teamId = teamStore.activeTeamIdForApi
        const url = config.url || ''
        if (teamId && urlNeedsTeamScope(url)) {
          attachTeamId(config, teamId)
        }
      } catch {
        /* pinia 未就绪时忽略 */
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
      const url = error.config?.url || ''
      const isAuthPublicRequest =
        url.includes('/api/login') ||
        url.includes('/api/register') ||
        url.includes('/api/auth/me')

      if (
        isUserNotFoundResponse(error) &&
        getToken() &&
        !url.includes('/api/auth/me')
      ) {
        console.warn('⚠️ 登录用户已失效，正在跳转登录页...')
        redirectToLoginAfterStaleSession()
        return Promise.reject(error)
      }

      const teamAccessDenied =
        error.response?.status === 403 &&
        (error.response?.data?.detail === '无权访问该团队' ||
          String(error.response?.data?.detail || '').includes('无权访问该团队'))

      if (teamAccessDenied) {
        try {
          const teamStore = useTeamStore()
          if (teamStore.activeTeamId) {
            teamStore.activeTeamId = ''
            try {
              sessionStorage.removeItem('app2docker-active-team-id')
            } catch {
              /* ignore */
            }
            teamStore.fetchMyTeams().catch(() => {})
          }
        } catch {
          /* pinia 未就绪时忽略 */
        }
      }

      if (error.response?.status === 401) {
        if (!isAuthPublicRequest && getToken()) {
          const errorMessage =
            error.response?.data?.detail ||
            error.response?.data?.message ||
            'Token已过期，请重新登录'

          if (errorMessage.includes('过期') || errorMessage.includes('expired')) {
            console.warn('⚠️ Token已过期，正在退出登录...')
          } else {
            console.warn('⚠️ 认证失败，正在退出登录...')
          }

          clearAuth()
          window.location.reload()
        }
      }
      return Promise.reject(error)
    }
  )
}

