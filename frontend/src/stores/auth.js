import { defineStore } from 'pinia'
import axios from 'axios'
import {
  clearAuth,
  getToken,
  getUsername,
  isUserNotFoundResponse,
  logout as logoutRequest,
  saveAuth,
} from '@/utils/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    username: getUsername() || '',
    /** 已通过 /api/auth/me 校验：适用于仅有 httpOnly Cookie、localStorage 无 token 时 */
    cookieSessionOk: false,
    isGlobalAdmin: false,
  }),
  getters: {
    isAuthenticated(state) {
      return !!getToken() || state.cookieSessionOk
    },
  },
  actions: {
    /** 登录/注册后与 localStorage 对齐，并刷新 axios 默认 Authorization */
    syncFromStorage() {
      this.syncUsernameFromStorage()
      this.applyAxiosAuthHeader()
    },
    syncUsernameFromStorage() {
      this.username = getUsername() || ''
    },
    applyAxiosAuthHeader() {
      const token = getToken()
      if (token) {
        axios.defaults.headers.common.Authorization = `Bearer ${token}`
      } else {
        delete axios.defaults.headers.common.Authorization
      }
    },
    setSession({ token, username, remember = true }) {
      saveAuth(token, username, remember)
      this.username = username || ''
      this.applyAxiosAuthHeader()
      this.cookieSessionOk = !!getToken()
    },
    async login({ username, password, remember = true }) {
      const { data } = await axios.post('/api/login', { username, password })
      if (data.token != null && data.username != null) {
        this.setSession({ token: data.token, username: data.username, remember })
      }
      return data
    },
    async register({ username, password, email, remember = true }) {
      const body = { username, password }
      if (email !== undefined && email !== '') {
        body.email = email
      }
      const { data } = await axios.post('/api/register', body)
      if (data.token != null && data.username != null) {
        this.setSession({ token: data.token, username: data.username, remember })
      }
      return data
    },
    async fetchMe() {
      try {
        const { data } = await axios.get('/api/auth/me')
        if (data?.username) {
          this.username = data.username
          this.cookieSessionOk = true
        }
        this.isGlobalAdmin = !!data?.is_global_admin
        return data
      } catch (e) {
        this.cookieSessionOk = false
        this.isGlobalAdmin = false
        if (!getToken() || isUserNotFoundResponse(e)) {
          this.clearSession()
        }
        throw e
      }
    },
    async logout() {
      try {
        await logoutRequest()
      } finally {
        this.clearSession()
      }
    },
    clearSession() {
      clearAuth()
      this.username = ''
      this.cookieSessionOk = false
      this.isGlobalAdmin = false
      delete axios.defaults.headers.common.Authorization
    },
  },
})
