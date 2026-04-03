<template>
  <div class="user-management">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-users"></i> 用户管理
      </h5>
      <div class="btn-group">
        <button class="btn btn-outline-secondary btn-sm" @click="loadUsers" title="刷新">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
        <button class="btn btn-primary btn-sm" @click="showCreateModal = true">
          <i class="fas fa-plus"></i> 创建用户
        </button>
      </div>
    </div>

    <!-- 用户列表 -->
    <div class="table-responsive">
      <table class="table table-hover">
        <thead>
          <tr>
            <th>用户名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.user_id">
            <td>{{ user.username }}</td>
            <td>{{ user.email || '-' }}</td>
            <td>
              <span 
                v-for="role in user.roles" 
                :key="role" 
                class="badge bg-secondary me-1"
              >
                {{ role }}
              </span>
            </td>
            <td>
              <span :class="user.enabled ? 'badge bg-success' : 'badge bg-danger'">
                {{ user.enabled ? '启用' : '禁用' }}
              </span>
            </td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td>
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-primary" 
                  @click="editUser(user)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-warning" 
                  @click="changePassword(user)"
                  title="修改密码"
                  :disabled="user.username === 'admin'"
                >
                  <i class="fas fa-key"></i>
                </button>
                <button 
                  class="btn btn-outline-info" 
                  @click="openAppKeysModal(user)"
                  title="管理该用户的 API 密钥"
                >
                  <i class="fas fa-fingerprint"></i>
                </button>
                <button 
                  class="btn btn-outline-secondary" 
                  @click="toggleEnable(user)"
                  :title="user.enabled ? '禁用' : '启用'"
                  :disabled="user.username === 'admin'"
                >
                  <i class="fas" :class="user.enabled ? 'fa-ban' : 'fa-check'"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="deleteUser(user)"
                  title="删除"
                  :disabled="user.username === currentUsername"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建/编辑用户模态框 -->
    <div v-if="showCreateModal || showEditModal" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ showCreateModal ? '创建用户' : '编辑用户' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveUser">
              <div class="mb-3">
                <label class="form-label">用户名 <span class="text-danger">*</span></label>
                <input 
                  v-model="form.username" 
                  type="text" 
                  class="form-control" 
                  required
                  :disabled="showEditModal"
                />
              </div>
              
              <div v-if="showCreateModal" class="mb-3">
                <label class="form-label">密码 <span class="text-danger">*</span></label>
                <input 
                  v-model="form.password" 
                  type="password" 
                  class="form-control" 
                  required
                  minlength="6"
                />
                <div class="form-text">密码长度至少6位</div>
              </div>
              
              <div class="mb-3">
                <label class="form-label">邮箱</label>
                <input 
                  v-model="form.email" 
                  type="email" 
                  class="form-control" 
                />
              </div>
              
              <div class="mb-3">
                <label class="form-label">角色 <span class="text-danger">*</span></label>
                <div v-for="role in availableRoles" :key="role.role_id" class="form-check">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    :value="role.name"
                    v-model="form.roles"
                    :id="`role-${role.role_id}`"
                  />
                  <label class="form-check-label" :for="`role-${role.role_id}`">
                    {{ role.name }}
                    <small class="text-muted">({{ role.description }})</small>
                  </label>
                </div>
              </div>
              
              <div v-if="showEditModal" class="mb-3">
                <div class="form-check form-switch">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    v-model="form.enabled"
                    id="userEnabled"
                  />
                  <label class="form-check-label" for="userEnabled">
                    启用用户
                  </label>
                </div>
              </div>
              
              <div v-if="error" class="alert alert-danger mb-0">
                {{ error }}
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeModal">取消</button>
            <button type="button" class="btn btn-primary" @click="saveUser">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 修改密码模态框 -->
    <div v-if="showPasswordModal" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">修改密码 - {{ passwordForm.username }}</h5>
            <button type="button" class="btn-close" @click="showPasswordModal = false"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="savePassword">
              <div class="mb-3">
                <label class="form-label">新密码 <span class="text-danger">*</span></label>
                <input 
                  v-model="passwordForm.newPassword" 
                  type="password" 
                  class="form-control" 
                  required
                  minlength="6"
                />
                <div class="form-text">密码长度至少6位</div>
              </div>
              
              <div v-if="passwordError" class="alert alert-danger mb-0">
                {{ passwordError }}
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showPasswordModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="savePassword">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理员：管理指定用户的 API 密钥 -->
    <div
      v-if="showAppKeysModal && appKeysTargetUser"
      class="modal fade show d-block"
      tabindex="-1"
      style="background-color: rgba(0, 0, 0, 0.5)"
    >
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-fingerprint me-1"></i>
              API 密钥 — {{ appKeysTargetUser.username }}
            </h5>
            <button
              type="button"
              class="btn-close"
              @click="closeAppKeysModal"
            ></button>
          </div>
          <div class="modal-body">
            <p class="text-muted small mb-3">
              以下密钥归属该用户，请求头可使用
              <code>X-API-Key</code> 携带完整密钥。新建密钥仅显示一次明文，请通知用户妥善保存。
            </p>
            <div class="d-flex align-items-center justify-content-between mb-3">
              <span class="fw-semibold">密钥列表</span>
              <button
                class="btn btn-sm btn-primary"
                type="button"
                :disabled="adminAppKeysLoading"
                @click="adminShowCreateForm = !adminShowCreateForm"
              >
                <i class="fas fa-plus me-1"></i>创建密钥
              </button>
            </div>
            <div v-if="adminShowCreateForm" class="card bg-light mb-3">
              <div class="card-body">
                <div class="mb-2">
                  <label class="form-label mb-1">名称</label>
                  <input
                    v-model="adminNewAppKey.name"
                    class="form-control"
                    placeholder="例如：CI 调用密钥"
                    maxlength="255"
                  />
                </div>
                <div class="mb-2">
                  <label class="form-label mb-1">过期时间（可选）</label>
                  <input
                    v-model="adminNewAppKey.expiresAt"
                    type="datetime-local"
                    class="form-control"
                  />
                </div>
                <button
                  class="btn btn-success btn-sm"
                  type="button"
                  :disabled="adminCreatingAppKey || !adminNewAppKey.name.trim()"
                  @click="createAdminAppKey"
                >
                  <span
                    v-if="adminCreatingAppKey"
                    class="spinner-border spinner-border-sm me-1"
                  ></span>
                  生成密钥
                </button>
              </div>
            </div>
            <div v-if="adminCreatedAppKey" class="alert alert-warning py-2">
              <div class="fw-bold mb-1">请立即复制并交给该用户，该密钥仅展示一次：</div>
              <code>{{ adminCreatedAppKey }}</code>
            </div>
            <div v-if="adminAppKeysError" class="alert alert-danger py-2">
              {{ adminAppKeysError }}
            </div>
            <div v-if="adminAppKeysLoading" class="text-muted">加载中...</div>
            <div v-else-if="adminAppKeys.length === 0" class="text-muted">
              该用户暂无 API 密钥
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>前缀</th>
                    <th>状态</th>
                    <th>最后使用</th>
                    <th>过期时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in adminAppKeys" :key="item.key_id">
                    <td>{{ item.name }}</td>
                    <td><code>{{ item.key_prefix }}</code></td>
                    <td>
                      <span
                        class="badge"
                        :class="item.enabled ? 'text-bg-success' : 'text-bg-secondary'"
                      >
                        {{ item.enabled ? "启用" : "禁用" }}
                      </span>
                    </td>
                    <td>{{ formatAppKeyTime(item.last_used_at) }}</td>
                    <td>{{ formatAppKeyTime(item.expires_at) }}</td>
                    <td>
                      <button
                        class="btn btn-outline-secondary btn-sm me-1"
                        type="button"
                        @click="toggleAdminAppKey(item.key_id)"
                      >
                        {{ item.enabled ? "禁用" : "启用" }}
                      </button>
                      <button
                        class="btn btn-outline-danger btn-sm"
                        type="button"
                        @click="removeAdminAppKey(item.key_id)"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeAppKeysModal">
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { getUsername } from '../utils/auth'

const users = ref([])
const availableRoles = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showPasswordModal = ref(false)
const currentUsername = ref('')
const error = ref('')
const passwordError = ref('')

const form = ref({
  user_id: '',
  username: '',
  password: '',
  email: '',
  roles: [],
  enabled: true
})

const passwordForm = ref({
  user_id: '',
  username: '',
  newPassword: ''
})

const showAppKeysModal = ref(false)
const appKeysTargetUser = ref(null)
const adminAppKeys = ref([])
const adminAppKeysLoading = ref(false)
const adminAppKeysError = ref('')
const adminShowCreateForm = ref(false)
const adminCreatingAppKey = ref(false)
const adminCreatedAppKey = ref('')
const adminNewAppKey = ref({ name: '', expiresAt: '' })

onMounted(async () => {
  currentUsername.value = getUsername() || ''
  await loadUsers()
  await loadRoles()
})

async function loadUsers() {
  try {
    const res = await axios.get('/api/users')
    users.value = res.data.users || []
  } catch (error) {
    console.error('加载用户列表失败:', error)
    alert('加载用户列表失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function loadRoles() {
  try {
    const res = await axios.get('/api/roles')
    availableRoles.value = res.data.roles || []
  } catch (error) {
    console.error('加载角色列表失败:', error)
  }
}

function editUser(user) {
  form.value = {
    user_id: user.user_id,
    username: user.username,
    password: '',
    email: user.email || '',
    roles: [...user.roles],
    enabled: user.enabled
  }
  showEditModal.value = true
}

function changePassword(user) {
  // 不能修改超级管理员的密码
  if (user.username === 'admin') {
    alert('不能修改超级管理员的密码')
    return
  }
  
  passwordForm.value = {
    user_id: user.user_id,
    username: user.username,
    newPassword: ''
  }
  showPasswordModal.value = true
  passwordError.value = ''
}

async function saveUser() {
  error.value = ''
  
  try {
    if (showCreateModal.value) {
      // 创建用户
      await axios.post('/api/users', {
        username: form.value.username,
        password: form.value.password,
        email: form.value.email || null,
        roles: form.value.roles
      })
      alert('用户创建成功')
    } else {
      // 更新用户
      await axios.put(`/api/users/${form.value.user_id}`, {
        email: form.value.email || null,
        enabled: form.value.enabled,
        roles: form.value.roles
      })
      alert('用户更新成功')
    }
    
    closeModal()
    await loadUsers()
  } catch (err) {
    console.error('保存用户失败:', err)
    error.value = err.response?.data?.detail || err.message || '操作失败'
  }
}

async function savePassword() {
  passwordError.value = ''
  
  try {
    await axios.put(`/api/users/${passwordForm.value.user_id}/password`, {
      new_password: passwordForm.value.newPassword
    })
    alert('密码修改成功')
    showPasswordModal.value = false
  } catch (error) {
    console.error('修改密码失败:', error)
    passwordError.value = error.response?.data?.detail || error.message || '操作失败'
  }
}

async function toggleEnable(user) {
  // 不能修改超级管理员的状态
  if (user.username === 'admin') {
    alert('不能修改超级管理员的状态')
    return
  }
  
  if (!confirm(`确定要${user.enabled ? '禁用' : '启用'}用户 ${user.username} 吗？`)) {
    return
  }
  
  try {
    const newEnabled = !user.enabled
    await axios.put(`/api/users/${user.user_id}/enable`, {
      enabled: newEnabled
    })
    alert(`用户已${newEnabled ? '启用' : '禁用'}`)
    await loadUsers()
  } catch (error) {
    console.error('操作失败:', error)
    alert('操作失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function deleteUser(user) {
  if (!confirm(`确定要删除用户 ${user.username} 吗？此操作不可恢复！`)) {
    return
  }
  
  try {
    await axios.delete(`/api/users/${user.user_id}`)
    alert('用户删除成功')
    await loadUsers()
  } catch (error) {
    console.error('删除用户失败:', error)
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

function closeModal() {
  showCreateModal.value = false
  showEditModal.value = false
  form.value = {
    user_id: '',
    username: '',
    password: '',
    email: '',
    roles: [],
    enabled: true
  }
  error.value = ''
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

function formatAppKeyTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return value
  }
}

function openAppKeysModal(user) {
  appKeysTargetUser.value = {
    user_id: user.user_id,
    username: user.username,
  }
  adminAppKeysError.value = ''
  adminCreatedAppKey.value = ''
  adminShowCreateForm.value = false
  adminNewAppKey.value = { name: '', expiresAt: '' }
  showAppKeysModal.value = true
  loadAdminAppKeys()
}

function closeAppKeysModal() {
  showAppKeysModal.value = false
  appKeysTargetUser.value = null
  adminAppKeys.value = []
  adminAppKeysError.value = ''
  adminCreatedAppKey.value = ''
  adminShowCreateForm.value = false
  adminNewAppKey.value = { name: '', expiresAt: '' }
}

async function loadAdminAppKeys() {
  const uid = appKeysTargetUser.value?.user_id
  if (!uid) return
  adminAppKeysLoading.value = true
  adminAppKeysError.value = ''
  try {
    const res = await axios.get(`/api/users/${uid}/app-keys`)
    adminAppKeys.value = res.data?.app_keys || []
  } catch (err) {
    console.error('加载用户 API 密钥失败:', err)
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || '加载失败'
    adminAppKeys.value = []
  } finally {
    adminAppKeysLoading.value = false
  }
}

async function createAdminAppKey() {
  const uid = appKeysTargetUser.value?.user_id
  if (!uid || !adminNewAppKey.value.name.trim()) return
  adminCreatingAppKey.value = true
  adminAppKeysError.value = ''
  try {
    const payload = { name: adminNewAppKey.value.name.trim() }
    if (adminNewAppKey.value.expiresAt) {
      payload.expires_at = new Date(adminNewAppKey.value.expiresAt).toISOString()
    }
    const res = await axios.post(`/api/users/${uid}/app-keys`, payload)
    adminCreatedAppKey.value = res.data?.app_key || ''
    adminNewAppKey.value = { name: '', expiresAt: '' }
    adminShowCreateForm.value = false
    await loadAdminAppKeys()
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || '创建失败'
  } finally {
    adminCreatingAppKey.value = false
  }
}

async function toggleAdminAppKey(keyId) {
  const uid = appKeysTargetUser.value?.user_id
  if (!uid) return
  adminAppKeysError.value = ''
  try {
    await axios.put(`/api/users/${uid}/app-keys/${keyId}/toggle`)
    await loadAdminAppKeys()
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || '操作失败'
  }
}

async function removeAdminAppKey(keyId) {
  if (!confirm('确定删除该 API 密钥吗？此操作不可恢复。')) return
  const uid = appKeysTargetUser.value?.user_id
  if (!uid) return
  adminAppKeysError.value = ''
  try {
    await axios.delete(`/api/users/${uid}/app-keys/${keyId}`)
    await loadAdminAppKeys()
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || '删除失败'
  }
}
</script>

<style scoped>
.user-management {
  padding: 1rem;
}
</style>
