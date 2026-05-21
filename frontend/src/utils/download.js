/**
 * 通过浏览器原生下载（流式，不经过 Blob 缓冲）
 */
import { getToken } from '@/utils/auth'
import { useTeamStore } from '@/stores/team'

/**
 * 为需认证的 GET 下载链接附加 team_id、access_token（供 <a href> 使用）
 * @param {string} path 如 /api/export-tasks/{id}/download
 * @param {Record<string, string>} [extraParams]
 */
export function buildAuthenticatedApiUrl(path, extraParams = {}) {
  const url = new URL(path, window.location.origin)
  const params = url.searchParams

  try {
    const teamStore = useTeamStore()
    const teamId = teamStore.activeTeamIdForApi
    if (teamId && !params.has('team_id')) {
      params.set('team_id', teamId)
    }
  } catch {
    /* pinia 未就绪 */
  }

  const token = getToken()
  if (token && !params.has('access_token')) {
    params.set('access_token', token)
  }

  for (const [key, value] of Object.entries(extraParams)) {
    if (value != null && value !== '') {
      params.set(key, String(value))
    }
  }

  const qs = params.toString()
  return qs ? `${url.pathname}?${qs}` : url.pathname
}

/**
 * @param {string} apiPath
 * @param {string} [filename]
 * @param {Record<string, string>} [extraParams]
 */
export function triggerBrowserDownload(apiPath, filename, extraParams) {
  const a = document.createElement('a')
  a.href = buildAuthenticatedApiUrl(apiPath, extraParams)
  if (filename) a.download = filename
  a.style.display = 'none'
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

/** 镜像导出任务归档文件名 */
export function exportImageArchiveFilename(task) {
  const image = (task.image || 'image').replace(/\//g, '_')
  const tag = task.tag || 'latest'
  const isCompressed =
    task.compress &&
    ['gzip', 'gz', 'tgz', '1', 'true', 'yes'].includes(
      String(task.compress).toLowerCase()
    )
  return `${image}-${tag}${isCompressed ? '.tar.gz' : '.tar'}`
}
