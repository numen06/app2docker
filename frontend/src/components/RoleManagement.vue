<template>
  <div class="role-management">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-user-shield"></i> 角色管理
      </h5>
      <div class="btn-group">
        <button class="btn btn-outline-secondary btn-sm" @click="loadRoles" title="刷新">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
        <button class="btn btn-primary btn-sm" @click="showCreateModal = true">
          <i class="fas fa-plus"></i> 创建角色
        </button>
      </div>
    </div>

    <!-- 角色列表 -->
    <div class="table-responsive">
      <table class="table table-hover">
        <thead>
          <tr>
            <th>角色名称</th>
            <th>描述</th>
            <th>权限数量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in roles" :key="role.role_id">
            <td>
              <strong>{{ role.name }}</strong>
              <span v-if="isSystemRole(role.name)" class="badge bg-info ms-2">系统角色</span>
            </td>
            <td>{{ role.description || '-' }}</td>
            <td>
              <span class="badge bg-secondary">{{ role.permissions?.length || 0 }}</span>
            </td>
            <td>
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-primary" 
                  @click="editRole(role)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-info" 
                  @click="viewPermissions(role)"
                  title="查看权限"
                >
                  <i class="fas fa-eye"></i>
                </button>
                <button 
                  v-if="!isSystemRole(role.name)"
                  class="btn btn-outline-danger" 
                  @click="deleteRole(role)"
                  title="删除"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建/编辑角色模态框 -->
    <div v-if="showCreateModal || showEditModal" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ showCreateModal ? '创建角色' : '编辑角色' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveRole">
              <div class="mb-3">
                <label class="form-label">角色名称 <span class="text-danger">*</span></label>
                <input 
                  v-model="form.name" 
                  type="text" 
                  class="form-control" 
                  required
                  :disabled="showEditModal && isSystemRole(form.name)"
                  placeholder="例如: developer, tester"
                />
                <div v-if="showEditModal && isSystemRole(form.name)" class="form-text text-warning">
                  系统默认角色不能修改名称
                </div>
              </div>
              
              <div class="mb-3">
                <label class="form-label">描述</label>
                <textarea 
                  v-model="form.description" 
                  class="form-control" 
                  rows="2"
                  placeholder="角色描述"
                ></textarea>
              </div>
              
              <div class="mb-3">
                <label class="form-label">权限配置 <span class="text-danger">*</span></label>
                <div class="border rounded p-3" style="max-height: 400px; overflow-y: auto;">
                  <div v-for="permission in availablePermissions" :key="permission.permission_id" class="form-check mb-2">
                    <input 
                      class="form-check-input" 
                      type="checkbox" 
                      :value="permission.code"
                      v-model="form.permissions"
                      :id="`perm-${permission.permission_id}`"
                    />
                    <label class="form-check-label" :for="`perm-${permission.permission_id}`">
                      <strong>{{ permission.name }}</strong>
                      <small class="text-muted ms-2">({{ permission.code }})</small>
                    </label>
                  </div>
                  <div v-if="availablePermissions.length === 0" class="text-muted text-center py-3">
                    暂无权限数据
                  </div>
                </div>
                <div class="form-text">
                  已选择 <strong>{{ form.permissions.length }}</strong> 个权限
                </div>
              </div>
              
              <div v-if="error" class="alert alert-danger mb-0">
                {{ error }}
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeModal">取消</button>
            <button type="button" class="btn btn-primary" @click="saveRole">保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 查看权限模态框 -->
    <div v-if="showViewModal" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">角色权限 - {{ viewRole.name }}</h5>
            <button type="button" class="btn-close" @click="showViewModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="viewRole.permissions && viewRole.permissions.length > 0">
              <ul class="list-group">
                <li 
                  v-for="permCode in viewRole.permissions" 
                  :key="permCode"
                  class="list-group-item"
                >
                  <strong>{{ getPermissionName(permCode) }}</strong>
                  <small class="text-muted ms-2">({{ permCode }})</small>
                </li>
              </ul>
            </div>
            <div v-else class="text-muted text-center py-3">
              该角色暂无权限
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showViewModal = false">关闭</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref } from 'vue'

const roles = ref([])
const availablePermissions = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showViewModal = ref(false)
const viewRole = ref({})
const error = ref('')

const form = ref({
  role_id: '',
  name: '',
  description: '',
  permissions: []
})

onMounted(async () => {
  await loadRoles()
  await loadPermissions()
})

async function loadRoles() {
  try {
    const res = await axios.get('/api/roles')
    roles.value = res.data.roles || []
  } catch (error) {
    console.error('加载角色列表失败:', error)
    alert('加载角色列表失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function loadPermissions() {
  try {
    const res = await axios.get('/api/permissions')
    availablePermissions.value = res.data.permissions || []
  } catch (error) {
    console.error('加载权限列表失败:', error)
  }
}

function isSystemRole(roleName) {
  return ['admin', 'user', 'readonly'].includes(roleName)
}

function editRole(role) {
  form.value = {
    role_id: role.role_id,
    name: role.name,
    description: role.description || '',
    permissions: [...(role.permissions || [])]
  }
  showEditModal.value = true
  error.value = ''
}

function viewPermissions(role) {
  viewRole.value = role
  showViewModal.value = true
}

function getPermissionName(permCode) {
  const perm = availablePermissions.value.find(p => p.code === permCode)
  return perm ? perm.name : permCode
}

async function saveRole() {
  error.value = ''
  
  try {
    if (showCreateModal.value) {
      // 创建角色
      await axios.post('/api/roles', {
        name: form.value.name,
        description: form.value.description || null,
        permissions: form.value.permissions
      })
      alert('角色创建成功')
    } else {
      // 更新角色
      await axios.put(`/api/roles/${form.value.role_id}`, {
        description: form.value.description || null,
        permissions: form.value.permissions
      })
      alert('角色更新成功')
    }
    
    closeModal()
    await loadRoles()
  } catch (err) {
    console.error('保存角色失败:', err)
    error.value = err.response?.data?.detail || err.message || '操作失败'
  }
}

async function deleteRole(role) {
  if (!confirm(`确定要删除角色 "${role.name}" 吗？此操作不可恢复！`)) {
    return
  }
  
  try {
    await axios.delete(`/api/roles/${role.role_id}`)
    alert('角色删除成功')
    await loadRoles()
  } catch (error) {
    console.error('删除角色失败:', error)
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

function closeModal() {
  showCreateModal.value = false
  showEditModal.value = false
  form.value = {
    role_id: '',
    name: '',
    description: '',
    permissions: []
  }
  error.value = ''
}
</script>

<style scoped>
.role-management {
  padding: 1rem;
}
</style>
