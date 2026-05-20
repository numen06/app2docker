import { defineStore } from 'pinia'
import axios from 'axios'

const STORAGE_KEY = 'app2docker-active-team-id'
const DEFAULT_TEAM_NAME = '默认团队'

/** 合并重复的「默认团队」成员记录（迁移前后端可能各有一条） */
function dedupeDefaultTeamMemberships(raw) {
  if (!Array.isArray(raw) || raw.length < 2) return raw
  const defaults = raw.filter((m) => m.team?.name === DEFAULT_TEAM_NAME)
  if (defaults.length < 2) return raw
  const canonical =
    defaults.find((m) => m.team?.slug === 'default') || defaults[0]
  const keepId = canonical?.team?.team_id
  if (!keepId) return raw
  const dropIds = new Set(
    defaults
      .map((m) => m.team?.team_id)
      .filter((id) => id && id !== keepId)
  )
  if (!dropIds.size) return raw
  return raw.filter((m) => !dropIds.has(m.team?.team_id))
}

function membershipRole(state) {
  const m =
    state.memberships.find((x) => x.team?.team_id === state.activeTeamId) ||
    state.memberships[0]
  return (m?.role || state.activeTeamRole || '').toLowerCase()
}

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
    teamCapabilities: {
      canManageTeam: null,
      canAssignAdmin: null,
      canDissolveTeam: null,
    },
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
      const fromApi = state.teamCapabilities.canManageTeam
      if (fromApi !== null) return fromApi
      const r = membershipRole(state)
      return r === 'owner' || r === 'admin'
    },
    isTeamOwner(state) {
      const fromApi = state.teamCapabilities.canDissolveTeam
      if (fromApi !== null) return fromApi
      return membershipRole(state) === 'owner'
    },
    canAssignTeamAdmin(state) {
      const fromApi = state.teamCapabilities.canAssignAdmin
      if (fromApi !== null) return fromApi
      return membershipRole(state) === 'owner'
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
    _clearCapabilities() {
      this.teamCapabilities = {
        canManageTeam: null,
        canAssignAdmin: null,
        canDissolveTeam: null,
      }
    },
    _applyCapabilities(data) {
      if (data && typeof data.can_manage_team === 'boolean') {
        this.teamCapabilities = {
          canManageTeam: data.can_manage_team,
          canAssignAdmin: !!data.can_assign_admin,
          canDissolveTeam: !!data.can_dissolve_team,
        }
      } else {
        this._clearCapabilities()
      }
    },
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
    _normalizeActiveTeamId(id) {
      const next = (id || '').trim()
      if (!next) return ''
      if (
        this.memberships.length &&
        !this.memberships.some((m) => m.team?.team_id === next)
      ) {
        return this.memberships[0]?.team?.team_id || ''
      }
      return next
    },
    async persistActiveTeam(id) {
      const normalized = this._normalizeActiveTeamId(id)
      this.activeTeamId = normalized
      try {
        if (normalized) sessionStorage.setItem(STORAGE_KEY, normalized)
        else sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        /* ignore */
      }
      if (normalized) {
        await this.fetchMenuPermissions(normalized)
      } else {
        this.menuPermissions = []
        this.activeTeamRole = ''
        this._clearCapabilities()
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
        this.memberships = dedupeDefaultTeamMemberships(raw)
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
        if (this.activeTeamId) {
          this.activeTeamId = ''
          try {
            sessionStorage.removeItem(STORAGE_KEY)
          } catch {
            /* ignore */
          }
        }
      } finally {
        this.loading = false
      }
    },
    async fetchMenuPermissions(teamId) {
      const id = teamId || this.activeTeamId
      if (!id) {
        this.menuPermissions = []
        this.activeTeamRole = ''
        this._clearCapabilities()
        return []
      }
      this.menuPermissionsLoading = true
      try {
        const res = await axios.get(`/api/teams/${id}/menu-permissions`)
        const perms = res.data?.permissions || []
        this.menuPermissions = Array.isArray(perms) ? perms : []
        this.activeTeamRole = res.data?.role || ''
        this._applyCapabilities(res.data)
        return this.menuPermissions
      } catch {
        this.menuPermissions = []
        this.activeTeamRole = ''
        this._clearCapabilities()
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
      this._clearCapabilities()
      try {
        sessionStorage.removeItem(STORAGE_KEY)
      } catch {
        /* ignore */
      }
    },
  },
})
