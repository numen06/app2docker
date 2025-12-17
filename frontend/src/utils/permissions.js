/**
 * 权限检查工具函数
 */
import axios from 'axios'

let userPermissions = null
let permissionsPromise = null

/**
 * 获取用户权限列表
 */
export async function getUserPermissions() {
  // 如果正在请求中，返回同一个Promise
  if (permissionsPromise) {
    return permissionsPromise
  }

  // 如果已缓存，直接返回
  if (userPermissions !== null) {
    return userPermissions
  }

  // 发起请求
  permissionsPromise = axios.get('/api/user/permissions')
    .then(res => {
      userPermissions = new Set(res.data.permissions || [])
      permissionsPromise = null
      return userPermissions
    })
    .catch(error => {
      permissionsPromise = null
      console.error('获取用户权限失败:', error)
      // 返回空集合，避免权限检查失败
      userPermissions = new Set()
      return userPermissions
    })

  return permissionsPromise
}

/**
 * 检查是否有指定权限
 */
export async function hasPermission(permissionCode) {
  const permissions = await getUserPermissions()
  return permissions.has(permissionCode)
}

/**
 * 检查是否有任一权限
 */
export async function hasAnyPermission(permissionCodes) {
  if (!Array.isArray(permissionCodes) || permissionCodes.length === 0) {
    return false
  }
  const permissions = await getUserPermissions()
  return permissionCodes.some(code => permissions.has(code))
}

/**
 * 检查是否有所有权限
 */
export async function hasAllPermissions(permissionCodes) {
  if (!Array.isArray(permissionCodes) || permissionCodes.length === 0) {
    return true
  }
  const permissions = await getUserPermissions()
  return permissionCodes.every(code => permissions.has(code))
}

/**
 * 清除权限缓存（登录/登出时调用）
 */
export function clearPermissionsCache() {
  userPermissions = null
  permissionsPromise = null
}

/**
 * 同步版本的权限检查（需要先调用getUserPermissions）
 */
export function hasPermissionSync(permissionCode) {
  if (userPermissions === null) {
    console.warn('权限缓存未初始化，请先调用getUserPermissions')
    return false
  }
  return userPermissions.has(permissionCode)
}

/**
 * 同步版本的任一权限检查
 */
export function hasAnyPermissionSync(permissionCodes) {
  if (!Array.isArray(permissionCodes) || permissionCodes.length === 0) {
    return false
  }
  if (userPermissions === null) {
    console.warn('权限缓存未初始化，请先调用getUserPermissions')
    return false
  }
  return permissionCodes.some(code => userPermissions.has(code))
}
