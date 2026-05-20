import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'
import { useAuthStore } from '@/stores/auth'
import { useTeamStore } from '@/stores/team'
import LoginPage from '@/components/LoginPage.vue'

const LandingPage = () => import('@/components/LandingPage.vue')
const RegisterPage = () => import('@/components/RegisterPage.vue')
const CreateTeamOnboarding = () => import('@/components/CreateTeamOnboarding.vue')
const AdminLayout = () => import('@/layouts/AdminLayout.vue')

function isTeamAdmin(teamStore, teamId) {
  const m = teamStore.memberships.find((x) => x.team?.team_id === teamId)
  if (!m) return false
  const r = m.role
  return r === 'owner' || r === 'admin'
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterPage,
    },
    {
      path: '/onboarding',
      name: 'onboarding',
      component: CreateTeamOnboarding,
      meta: { requiresAuth: true },
    },
    {
      path: '/app',
      redirect: (to) => ({
        path: '/app/dashboard',
        query: { ...to.query },
      }),
    },
    {
      path: '/app/pipeline/new',
      name: 'pipeline-create',
      component: AdminLayout,
      meta: { requiresAuth: true },
    },
    {
      path: '/app/pipeline/:pipelineId/edit',
      name: 'pipeline-edit',
      component: AdminLayout,
      meta: { requiresAuth: true },
    },
    {
      path: '/app/:tab',
      name: 'admin',
      component: AdminLayout,
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

async function resolveAuthed() {
  const authStore = useAuthStore()
  if (getToken()) {
    authStore.syncFromStorage()
  }
  try {
    await authStore.fetchMe()
    return authStore.isAuthenticated
  } catch {
    authStore.clearSession()
    return false
  }
}

async function ensureAuthContext(authStore, teamStore) {
  try {
    await authStore.fetchMe()
  } catch {
    authStore.clearSession()
    return false
  }
  await teamStore.fetchTeams()
  return true
}

async function defaultAuthedPath(authStore, teamStore) {
  await ensureAuthContext(authStore, teamStore)
  const firstId = teamStore.memberships[0]?.team?.team_id
  if (firstId && !teamStore.activeTeamId) {
    await teamStore.setCurrentTeam(firstId)
  }
  if (teamStore.hasTeams || authStore.isGlobalAdmin) {
    return '/app/dashboard'
  }
  return '/onboarding'
}

function needsTeamMembership(authStore, teamStore) {
  return !teamStore.hasTeams && !authStore.isGlobalAdmin
}

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const teamStore = useTeamStore()
  const needsAuthCheck =
    to.meta.requiresAuth ||
    to.path === '/' ||
    to.path === '/login' ||
    to.path === '/register' ||
    to.path === '/onboarding'
  const authed = needsAuthCheck ? await resolveAuthed() : authStore.isAuthenticated

  if (to.meta.requiresAuth && !authed) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (authed) {
    const ctxOk = await ensureAuthContext(authStore, teamStore)
    if (!ctxOk) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  if (authed && to.path === '/') {
    next(await defaultAuthedPath(authStore, teamStore))
    return
  }

  const legacyTeamMatch = to.path.match(/^\/teams\/([^/]+)/)
  if (authed && legacyTeamMatch) {
    const tid = legacyTeamMatch[1]
    const allowed = teamStore.memberships.some((m) => m.team?.team_id === tid)
    if (!allowed) {
      if (needsTeamMembership(authStore, teamStore)) {
        next('/onboarding')
        return
      }
      next('/app/dashboard')
      return
    }
    await teamStore.setCurrentTeam(tid)
    next({ path: '/app/team', replace: true })
    return
  }

  if (to.meta.requiresAdmin && authed) {
    const tid = String(to.params.teamId || teamStore.activeTeamId || '')
    if (!tid || !isTeamAdmin(teamStore, tid)) {
      next(tid ? '/app/team' : await defaultAuthedPath(authStore, teamStore))
      return
    }
  }

  if (authed && to.path === '/onboarding' && teamStore.hasTeams) {
    next(await defaultAuthedPath(authStore, teamStore))
    return
  }

  if (
    authed &&
    to.meta.requiresAuth &&
    to.path !== '/onboarding' &&
    !to.params.teamId &&
    to.path.startsWith('/app') &&
    needsTeamMembership(authStore, teamStore)
  ) {
    next('/onboarding')
    return
  }

  if (authed && (to.path === '/login' || to.path === '/register')) {
    next(await defaultAuthedPath(authStore, teamStore))
    return
  }

  next()
})

export default router
