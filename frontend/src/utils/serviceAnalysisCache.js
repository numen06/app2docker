/**
 * Dockerfile 服务分析结果缓存工具
 * 缓存有效期：1小时（因为服务分析结果变化不频繁）
 */

const CACHE_PREFIX = 'service_analysis_cache_'
const CACHE_EXPIRY = 60 * 60 * 1000 // 1小时（毫秒）

/**
 * 生成缓存键
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string} dockerfileName Dockerfile名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @returns {string} 缓存键
 */
function getCacheKey(gitUrl, branch, dockerfileName, sourceId = null) {
  // 规范化URL（去除尾随斜杠等）
  const normalizedUrl = gitUrl.trim().replace(/\/$/, '').replace(/\.git$/, '')
  const branchKey = branch || 'main'
  const dockerfileKey = dockerfileName || 'Dockerfile'
  
  if (sourceId) {
    return `${CACHE_PREFIX}${sourceId}_${branchKey}_${dockerfileKey}`
  }
  return `${CACHE_PREFIX}${normalizedUrl}_${branchKey}_${dockerfileKey}`
}

/**
 * 获取缓存的服务分析结果
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string} dockerfileName Dockerfile名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @returns {Object|null} 缓存的服务列表，如果已过期或不存在则返回null
 */
export function getServiceAnalysisCache(gitUrl, branch, dockerfileName, sourceId = null) {
  try {
    const key = getCacheKey(gitUrl, branch, dockerfileName, sourceId)
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
    return data.services || []
  } catch (error) {
    console.error('读取服务分析缓存失败:', error)
    return null
  }
}

/**
 * 保存服务分析结果到缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string} dockerfileName Dockerfile名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @param {Array} services 服务列表
 */
export function setServiceAnalysisCache(gitUrl, branch, dockerfileName, sourceId = null, services) {
  try {
    const key = getCacheKey(gitUrl, branch, dockerfileName, sourceId)
    const cacheData = {
      services: services || [],
      timestamp: Date.now()
    }
    localStorage.setItem(key, JSON.stringify(cacheData))
  } catch (error) {
    console.error('保存服务分析缓存失败:', error)
    // localStorage可能已满，尝试清理旧的缓存
    try {
      clearExpiredServiceAnalysisCache()
      localStorage.setItem(key, JSON.stringify(cacheData))
    } catch (e) {
      console.error('清理过期缓存后仍然保存失败:', e)
    }
  }
}

/**
 * 清除指定Git仓库、分支和Dockerfile的服务分析缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string} dockerfileName Dockerfile名称
 * @param {string|null} sourceId 数据源ID（可选）
 */
export function clearServiceAnalysisCache(gitUrl, branch, dockerfileName, sourceId = null) {
  try {
    const key = getCacheKey(gitUrl, branch, dockerfileName, sourceId)
    localStorage.removeItem(key)
  } catch (error) {
    console.error('清除服务分析缓存失败:', error)
  }
}

/**
 * 清除指定Git仓库所有分支和Dockerfile的服务分析缓存
 * @param {string} gitUrl Git仓库地址
 * @param {string|null} sourceId 数据源ID（可选）
 */
export function clearAllServiceAnalysisCacheForRepo(gitUrl, sourceId = null) {
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
    console.error('清除仓库所有服务分析缓存失败:', error)
  }
}

/**
 * 清除所有过期的服务分析缓存
 */
function clearExpiredServiceAnalysisCache() {
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
    console.error('清理过期服务分析缓存失败:', error)
  }
}

/**
 * 获取缓存的服务分析结果或从API获取（带自动缓存）
 * @param {Function} fetchFn 获取数据的异步函数，应该返回 { services: [...] }
 * @param {string} gitUrl Git仓库地址
 * @param {string} branch 分支名称
 * @param {string} dockerfileName Dockerfile名称
 * @param {string|null} sourceId 数据源ID（可选）
 * @param {boolean} forceRefresh 是否强制刷新（忽略缓存）
 * @returns {Promise<Array>} 服务列表
 */
export async function getServiceAnalysisWithCache(fetchFn, gitUrl, branch, dockerfileName, sourceId = null, forceRefresh = false) {
  // 如果不需要强制刷新，先尝试从缓存获取
  if (!forceRefresh) {
    const cached = getServiceAnalysisCache(gitUrl, branch, dockerfileName, sourceId)
    if (cached) {
      console.log('使用缓存的服务分析结果:', gitUrl, branch, dockerfileName)
      return cached
    }
  }
  
  // 从API获取
  console.log('从API获取服务分析结果:', gitUrl, branch, dockerfileName, forceRefresh ? '(强制刷新)' : '')
  const response = await fetchFn()
  
  // 提取services列表
  const services = response?.data?.services || []
  
  // 保存到缓存
  if (services && Array.isArray(services)) {
    setServiceAnalysisCache(gitUrl, branch, dockerfileName, sourceId, services)
  }
  
  return services
}

// 在模块加载时清理过期缓存
if (typeof window !== 'undefined') {
  clearExpiredServiceAnalysisCache()
}

