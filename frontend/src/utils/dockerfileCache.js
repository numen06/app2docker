/**
 * Dockerfile 列表缓存工具
 * 缓存有效期：1小时（因为Dockerfile列表变化不频繁）
 */

const CACHE_PREFIX = 'dockerfile_cache_'
const CACHE_EXPIRY = 60 * 60 * 1000 // 1小时（毫秒）

/**
 * 生成缓存键
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @returns {string} 缓存键
 */
function getCacheKey(gitUrl, branch, sourceId = null) {
  // 规范化URL（去除尾随斜杠等）
  const normalizedUrl = gitUrl.trim().replace(/\/$/, '').replace(/\.git$/, '')
  const branchKey = branch || 'main'
  if (sourceId) {
    return `${CACHE_PREFIX}${sourceId}_${branchKey}`
  }
  return `${CACHE_PREFIX}${normalizedUrl}_${branchKey}`
}

/**
 * 获取缓存的Dockerfile列表
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @returns {Array|null} 缓存的Dockerfile列表，如果已过期或不存在则返回null
 */
export function getDockerfileCache(gitUrl, branch, sourceId = null) {
  try {
    const key = getCacheKey(gitUrl, branch, sourceId)
    const cached = localStorage.getItem(key)
    
    if (!cached) {
      return null
    }
    
    const data = JSON.parse(cached)
    const now = Date.now()
    
    // 检查是否过期
    if (now - data.timestamp > CACHE_EXPIRY) {
      // 过期了，删除缓存
      localStorage.removeItem(key)
      return null
    }
    
    // 返回缓存数据（不包含timestamp）
    return data.dockerfiles || []
  } catch (error) {
    console.error('读取Dockerfile缓存失败:', error)
    return null
  }
}

/**
 * 保存Dockerfile列表到缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @param {Array} dockerfiles Dockerfile列表
 */
export function setDockerfileCache(gitUrl, branch, sourceId = null, dockerfiles) {
  try {
    const key = getCacheKey(gitUrl, branch, sourceId)
    const cacheData = {
      dockerfiles: dockerfiles || [],
      timestamp: Date.now()
    }
    localStorage.setItem(key, JSON.stringify(cacheData))
  } catch (error) {
    console.error('保存Dockerfile缓存失败:', error)
    // localStorage可能已满，尝试清理旧的缓存
    try {
      clearExpiredDockerfileCache()
      localStorage.setItem(key, JSON.stringify(cacheData))
    } catch (e) {
      console.error('清理过期缓存后仍然保存失败:', e)
    }
  }
}

/**
 * 清除指定Git仓库和分支的Dockerfile缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string|null} sourceId 数据源ID（可选）
 */
export function clearDockerfileCache(gitUrl, branch, sourceId = null) {
  try {
    const key = getCacheKey(gitUrl, branch, sourceId)
    localStorage.removeItem(key)
  } catch (error) {
    console.error('清除Dockerfile缓存失败:', error)
  }
}

/**
 * 清除指定Git仓库所有分支的Dockerfile缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string|null} sourceId 数据源ID（可选）
 */
export function clearAllDockerfileCacheForRepo(gitUrl, sourceId = null) {
  try {
    const normalizedUrl = gitUrl.trim().replace(/\/$/, '').replace(/\.git$/, '')
    const keys = Object.keys(localStorage)
    const prefix = sourceId 
      ? `${CACHE_PREFIX}${sourceId}_` 
      : `${CACHE_PREFIX}${normalizedUrl}_`
    
    keys.forEach(key => {
      if (key.startsWith(prefix)) {
        localStorage.removeItem(key)
      }
    })
  } catch (error) {
    console.error('清除仓库所有Dockerfile缓存失败:', error)
  }
}

/**
 * 清除所有过期的Dockerfile缓存
 */
function clearExpiredDockerfileCache() {
  try {
    const keys = Object.keys(localStorage)
    const now = Date.now()
    
    keys.forEach(key => {
      if (key.startsWith(CACHE_PREFIX)) {
        try {
          const cached = localStorage.getItem(key)
          if (cached) {
            const data = JSON.parse(cached)
            if (now - data.timestamp > CACHE_EXPIRY) {
              localStorage.removeItem(key)
            }
          }
        } catch (e) {
          // 解析失败，删除无效的缓存项
          localStorage.removeItem(key)
        }
      }
    })
  } catch (error) {
    console.error('清理过期Dockerfile缓存失败:', error)
  }
}

/**
 * 获取缓存的Dockerfile列表或从API获取（带自动缓存）
 * @param {Function} fetchFn 获取数据的异步函数，应该返回 { dockerfiles: [...] }
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @param {boolean} forceRefresh 是否强制刷新（忽略缓存）
 * @returns {Promise<Array>} Dockerfile列表
 */
export async function getDockerfilesWithCache(fetchFn, gitUrl, branch, sourceId = null, forceRefresh = false) {
  // 如果不需要强制刷新，先尝试从缓存获取
  if (!forceRefresh) {
    const cached = getDockerfileCache(gitUrl, branch, sourceId)
    if (cached) {
      console.log('使用缓存的Dockerfile列表:', gitUrl, branch)
      return cached
    }
  }
  
  // 从API获取
  console.log('从API获取Dockerfile列表:', gitUrl, branch, forceRefresh ? '(强制刷新)' : '')
  const response = await fetchFn()
  
  // 提取dockerfiles列表
  const dockerfiles = response?.data?.dockerfiles || response?.dockerfiles || []
  
  // 保存到缓存
  if (dockerfiles && Array.isArray(dockerfiles)) {
    setDockerfileCache(gitUrl, branch, sourceId, dockerfiles)
  }
  
  return dockerfiles
}

// 在模块加载时清理过期缓存
if (typeof window !== 'undefined') {
  clearExpiredDockerfileCache()
}

