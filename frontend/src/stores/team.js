import { defineStore } from 'pinia'
import axios from 'axios'

const STORAGE_KEY = 'app2docker-active-team-id'

export const useTeamStore = defineStore('team', {
  state: () => ({
    memberships: [],
    members: [],
    loading: false,
    activeTeamId:
      typeof sessionStorage !== 'undefined'
        ? sessionStorage.getItem(STORAGE_KEY) || ''
        : '',
    error: '',
    menuPermissions: [],
    activeTeamRole: '',
    menuPermissionsLoading: false,
  }),
  getters: {
    currentTeamId(state) {
      return state.activeTeamId || null
    },
    teams(state) {
      return state.memberships
        .map((m) => ({
          id: m.team?.team_id,
          name: m.team?.name ?? '',
          role: m.role ?? '',
        }))
        .filter((t) => t.id)
    },
    activeMembership(state) {
      return (
        state.memberships.find(
          (m) => m.team?.team_id === state.activeTeamId
        ) || state.memberships[0]
      )
    },
    activeTeam(state) {
      const m =
        state.memberships.find(
          (x) => x.team?.team_id === state.activeTeamId
        ) || state.memberships[0]
      return m?.team || null
    },
    canManageTeam(state) {
      const m =
        state.memberships.find(
          (x) => x.team?.team_id === state.activeTeamId
        ) || state.memberships[0]
      const r = m?.role
      return r === 'owner' || r === 'admin'
    },
    activeTeamIdForApi(state) {
      return state.activeTeamId || null
    },
    menuPermissionsSet(state) {
      return new Set(state.menuPermissions || [])
    },
    hasTeams(state) {
      return state.memberships.length > 0
    },
  },
  actions: {
    canManageResource(permission, minLevel = 'edit') {
      const order = { view: 0, run: 1, edit: 2, admin: 3 }
      const eff = order[(permission || '').toLowerCase()]
      const need = order[minLevel] ?? 2
      if (eff === undefined) return false
      return eff >= need
    },
    setCurrentTeam(id) {
      this.persistActiveTeam(id || '')
    },
    async persistActiveTeam(id) {
      this.activeTeamId = id || ''
      try {
        if (id) sessionStorage.setItem(STORAGE_KEY, id)
        else sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        /* ignore */
      }
      if (id) {
        await this.fetchMenuPermissions(id)
      } else {
        this.menuPermissions = []
        this.activeTeamRole = ''
      }
    },
    async fetchTeams() {
      await this.fetchMyTeams()
      return this.teams
    },
    async fetchMyTeams() {
      this.loading = true
      this.error = ''
      try {
        const res = await axios.get('/api/teams/me')
        const raw = Array.isArray(res.data) ? res.data : []
        this.memberships = raw
        if (
          this.activeTeamId &&
          !this.memberships.some((m) => m.team?.team_id === this.activeTeamId)
        ) {
          this.activeTeamId = ''
          try {
            sessionStorage.removeItem(STORAGE_KEY)
          } catch {
            /* ignore */
          }
        }
        if (!this.activeTeamId && this.memberships.length) {
          const tid = this.memberships[0]?.team?.team_id
          if (tid) {
            this.activeTeamId = tid
            try {
              sessionStorage.setItem(STORAGE_KEY, tid)
            } catch {
              /* ignore */
            }
          }
        }
        if (this.activeTeamId) {
          await this.fetchMenuPermissions(this.activeTeamId)
        }
      } catch (e) {
        const msg =
          e?.response?.data?.detail ||
          e?.message ||
          '加载团队失败（若后端未挂载 /api/teams 将无法使用团队功能）'
        this.error = typeof msg === 'string' ? msg : '加载团队失败'
        this.memberships = []
      } finally {
        this.loading = false
      }
    },
    async fetchMenuPermissions(teamId) {
      const id = teamId || this.activeTeamId
      if (!id) {
        this.menuPermissions = []
        this.activeTeamRole = ''
        return []
      }
      this.menuPermissionsLoading = true
      try {
        const res = await axios.get(`/api/teams/${id}/menu-permissions`)
        const perms = res.data?.permissions || []
        this.menuPermissions = Array.isArray(perms) ? perms : []
        this.activeTeamRole = res.data?.role || ''
        return this.menuPermissions
      } catch {
        this.menuPermissions = []
        this.activeTeamRole = ''
        return []
      } finally {
        this.menuPermissionsLoading = false
      }
    },
    permissionAtLeast(have, need) {
      const rank = { view: 0, run: 1, edit: 2, admin: 3 }
      const h = rank[have] ?? -1
      const n = rank[need] ?? 0
      return h >= n
    },
    async fetchMembers(teamId) {
      const id = teamId || this.activeTeamId
      if (!id) {
        this.members = []
        return []
      }
      try {
        const res = await axios.get(`/api/teams/${id}/members`)
        const raw = res.data?.members ?? res.data?.data ?? res.data ?? []
        const list = Array.isArray(raw) ? raw : []
        this.members = list
        return list
      } catch {
        this.members = []
        return []
      }
    },
    reset() {
      this.memberships = []
      this.members = []
      this.activeTeamId = ''
      this.menuPermissions = []
      this.activeTeamRole = ''
      this.error = ''
      try {
        sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        /* ignore */
      }
    },
  },
})
