/**
 * 项目类型统一管理工具
 * 使用浏览器缓存，避免重复加载
 */
import axios from 'axios'

const CACHE_KEY = 'app_project_types'
const CACHE_EXPIRY_KEY = 'app_project_types_expiry'
const CACHE_DURATION = 24 * 60 * 60 * 1000 // 24小时缓存

// 默认项目类型（作为后备）
const DEFAULT_PROJECT_TYPES = [
  { value: "jar", label: "Java 应用（JAR）", icon: "fab fa-java", badgeClass: "bg-danger", order: 1 },
  { value: "nodejs", label: "Node.js 应用", icon: "fab fa-node-js", badgeClass: "bg-success", order: 2 },
  { value: "python", label: "Python 应用", icon: "fab fa-python", badgeClass: "bg-info", order: 3 },
  { value: "go", label: "Go 应用", icon: "fas fa-code", badgeClass: "bg-primary", order: 4 },
  { value: "web", label: "静态网站", icon: "fas fa-globe", badgeClass: "bg-secondary", order: 5 },
]

/**
 * 从缓存获取项目类型列表
 */
function getCachedProjectTypes() {
  try {
    const cached = localStorage.getItem(CACHE_KEY)
    const expiry = localStorage.getItem(CACHE_EXPIRY_KEY)
    
    if (cached && expiry) {
      const now = Date.now()
      if (now < parseInt(expiry)) {
        return JSON.parse(cached)
      } else {
        // 缓存已过期，清除
        localStorage.removeItem(CACHE_KEY)
        localStorage.removeItem(CACHE_EXPIRY_KEY)
      }
    }
  } catch (error) {
    console.error('读取项目类型缓存失败:', error)
  }
  return null
}

/**
 * 保存项目类型到缓存
 */
function setCachedProjectTypes(projectTypes) {
  try {
    const expiry = Date.now() + CACHE_DURATION
    localStorage.setItem(CACHE_KEY, JSON.stringify(projectTypes))
    localStorage.setItem(CACHE_EXPIRY_KEY, expiry.toString())
  } catch (error) {
    console.error('保存项目类型缓存失败:', error)
  }
}

/**
 * 从API加载项目类型
 */
async function loadProjectTypesFromAPI() {
  try {
    const res = await axios.get('/api/project-types')
    const projectTypes = res.data.project_types || DEFAULT_PROJECT_TYPES
    setCachedProjectTypes(projectTypes)
    return projectTypes
  } catch (error) {
    console.error('从API加载项目类型失败:', error)
    // API加载失败时，使用默认值并缓存
    setCachedProjectTypes(DEFAULT_PROJECT_TYPES)
    return DEFAULT_PROJECT_TYPES
  }
}

/**
 * 获取项目类型列表（统一入口）
 * 优先使用缓存，缓存不存在或过期时从API加载
 */
export async function getProjectTypes() {
  // 先尝试从缓存获取
  const cached = getCachedProjectTypes()
  if (cached) {
    return cached
  }
  
  // 缓存不存在或已过期，从API加载
  return await loadProjectTypesFromAPI()
}

/**
 * 同步获取项目类型列表（如果缓存存在）
 * 如果缓存不存在，返回默认值
 */
export function getProjectTypesSync() {
  const cached = getCachedProjectTypes()
  return cached || DEFAULT_PROJECT_TYPES
}

/**
 * 根据项目类型值获取项目类型信息
 */
export function getProjectTypeInfo(type) {
  const types = getProjectTypesSync()
  return types.find(p => p.value === type) || null
}

/**
 * 获取项目类型标签
 */
export function getProjectTypeLabel(type) {
  const info = getProjectTypeInfo(type)
  return info?.label || type
}

/**
 * 获取项目类型图标
 */
export function getProjectTypeIcon(type) {
  const info = getProjectTypeInfo(type)
  return info?.icon || 'fas fa-cube'
}

/**
 * 获取项目类型徽章样式类
 */
export function getProjectTypeBadgeClass(type) {
  const info = getProjectTypeInfo(type)
  return info?.badgeClass || 'bg-secondary'
}

/**
 * 清除项目类型缓存（强制重新加载）
 */
export function clearProjectTypesCache() {
  localStorage.removeItem(CACHE_KEY)
  localStorage.removeItem(CACHE_EXPIRY_KEY)
}

/**
 * 刷新项目类型（清除缓存并从API重新加载）
 */
export async function refreshProjectTypes() {
  clearProjectTypesCache()
  return await loadProjectTypesFromAPI()
}

