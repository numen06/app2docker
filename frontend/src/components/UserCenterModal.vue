<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="fas fa-user-circle"></i> 用户中心
          </h5>
          <button type="button" class="btn-close" @click="close"></button>
        </div>
        <div class="modal-body">
          <!-- 需要修改密码的提示 -->
          <div v-if="requirePasswordChange" class="alert alert-warning mb-3">
            <i class="fas fa-info-circle"></i> 
            检测到您使用的是默认密码，为了安全起见，请先修改密码。
          </div>

          <!-- 用户信息 -->
          <div v-if="!requirePasswordChange" class="mb-4">
            <h6 class="mb-3">
              <i class="fas fa-user"></i> 用户信息
            </h6>
            <div class="card bg-light">
              <div class="card-body">
                <div class="d-flex align-items-center">
                  <i class="fas fa-user-circle fa-2x text-primary me-3"></i>
                  <div>
                    <div class="fw-bold">{{ username }}</div>
                    <small class="text-muted">管理员</small>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <ul v-if="!requirePasswordChange" class="nav nav-tabs mb-3">
            <li class="nav-item">
              <button class="nav-link" :class="{ active: activeTab === 'password' }" @click="activeTab = 'password'" type="button">
                修改密码
              </button>
            </li>
            <li class="nav-item">
              <button class="nav-link" :class="{ active: activeTab === 'appkeys' }" @click="switchToAppKeys" type="button">
                API 密钥
              </button>
            </li>
          </ul>

          <div v-if="activeTab === 'password'">
            <h6 v-if="!requirePasswordChange" class="mb-3">
              <i class="fas fa-key"></i> 修改密码
            </h6>
            <form @submit.prevent="handleChangePassword">
              <div class="mb-3">
                <label class="form-label">当前密码 <span class="text-danger">*</span></label>
                <input v-model="form.oldPassword" type="password" class="form-control" placeholder="请输入当前密码" required autocomplete="current-password" />
              </div>

              <div class="mb-3">
                <label class="form-label">新密码 <span class="text-danger">*</span></label>
                <input v-model="form.newPassword" type="password" class="form-control" placeholder="请输入新密码（至少6位）" required minlength="6" autocomplete="new-password" />
                <div class="form-text">密码长度至少6位</div>
              </div>

              <div class="mb-3">
                <label class="form-label">确认新密码 <span class="text-danger">*</span></label>
                <input v-model="form.confirmPassword" type="password" class="form-control" placeholder="请再次输入新密码" required minlength="6" autocomplete="new-password" />
              </div>
            </form>
          </div>

          <div v-else>
            <div class="d-flex align-items-center justify-content-between mb-3">
              <h6 class="mb-0"><i class="fas fa-key"></i> API 密钥</h6>
              <button class="btn btn-sm btn-primary" @click="showCreateForm = !showCreateForm" :disabled="appKeysLoading">
                <i class="fas fa-plus me-1"></i>创建密钥
              </button>
            </div>

            <div v-if="showCreateForm" class="card bg-light mb-3">
              <div class="card-body">
                <div class="mb-2">
                  <label class="form-label mb-1">名称</label>
                  <input v-model="newAppKey.name" class="form-control" placeholder="例如：CI 调用密钥" maxlength="255" />
                </div>
                <div class="mb-2">
                  <label class="form-label mb-1">过期时间（可选）</label>
                  <input v-model="newAppKey.expiresAt" type="datetime-local" class="form-control" />
                </div>
                <button class="btn btn-success btn-sm" @click="createAppKey" :disabled="creatingAppKey || !newAppKey.name.trim()">
                  <span v-if="creatingAppKey" class="spinner-border spinner-border-sm me-1"></span>
                  生成密钥
                </button>
              </div>
            </div>

            <div v-if="createdAppKey" class="alert alert-warning py-2">
              <div class="fw-bold mb-1">请立即复制，该密钥仅展示一次：</div>
              <code>{{ createdAppKey }}</code>
            </div>

            <div v-if="appKeysLoading" class="text-muted">加载中...</div>
            <div v-else-if="appKeys.length === 0" class="text-muted">暂无 API 密钥</div>
            <div v-else class="table-responsive">
              <table class="table table-sm align-middle">
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
                  <tr v-for="item in appKeys" :key="item.key_id">
                    <td>{{ item.name }}</td>
                    <td><code>{{ item.key_prefix }}</code></td>
                    <td>
                      <span class="badge" :class="item.enabled ? 'text-bg-success' : 'text-bg-secondary'">
                        {{ item.enabled ? '启用' : '禁用' }}
                      </span>
                    </td>
                    <td>{{ formatTime(item.last_used_at) }}</td>
                    <td>{{ formatTime(item.expires_at) }}</td>
                    <td>
                      <button class="btn btn-outline-secondary btn-sm me-1" @click="toggleAppKey(item.key_id)">
                        {{ item.enabled ? '禁用' : '启用' }}
                      </button>
                      <button class="btn btn-outline-danger btn-sm" @click="removeAppKey(item.key_id)">删除</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger mb-0 mt-3">
            <i class="fas fa-exclamation-circle"></i> {{ error }}
          </div>

          <div v-if="success" class="alert alert-success mb-0 mt-3">
            <i class="fas fa-check-circle"></i> {{ success }}
          </div>
        </div>
        <div class="modal-footer">
          <button 
            v-if="!requirePasswordChange"
            type="button" 
            class="btn btn-secondary" 
            @click="close"
          >
            关闭
          </button>
          <button 
            type="button" 
            class="btn btn-primary" 
            @click="handlePrimaryAction"
            :disabled="(activeTab === 'password' || requirePasswordChange) ? (loading || !canSubmit) : false"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ (activeTab === 'password' || requirePasswordChange) ? (loading ? '修改中...' : '修改密码') : '确定' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  username: {
    type: String,
    default: ''
  },
  requirePasswordChange: {
    type: Boolean,
    default: false
  },
  initialTab: {
    type: String,
    default: 'password'
  }
})

const emit = defineEmits(['update:show', 'password-changed'])

const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const loading = ref(false)
const error = ref('')
const success = ref('')
const activeTab = ref('password')
const appKeys = ref([])
const appKeysLoading = ref(false)
const showCreateForm = ref(false)
const creatingAppKey = ref(false)
const createdAppKey = ref('')
const newAppKey = ref({
  name: '',
  expiresAt: ''
})

const canSubmit = computed(() => {
  return form.value.oldPassword && 
         form.value.newPassword && 
         form.value.confirmPassword &&
         form.value.newPassword.length >= 6 &&
         form.value.newPassword === form.value.confirmPassword
})

function close() {
  emit('update:show', false)
  resetState()
}

function resetState() {
  form.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  activeTab.value = props.initialTab === 'appkeys' ? 'appkeys' : 'password'
  appKeys.value = []
  showCreateForm.value = false
  createdAppKey.value = ''
  newAppKey.value = { name: '', expiresAt: '' }
  error.value = ''
  success.value = ''
}

function handlePrimaryAction() {
  if (activeTab.value === 'password' || props.requirePasswordChange) {
    handleChangePassword()
  } else {
    close()
  }
}

async function switchToAppKeys() {
  activeTab.value = 'appkeys'
  await loadAppKeys()
}

function formatTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

async function loadAppKeys() {
  appKeysLoading.value = true
  error.value = ''
  try {
    const res = await axios.get('/api/user/app-keys')
    appKeys.value = res.data?.app_keys || []
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '加载 API 密钥失败'
  } finally {
    appKeysLoading.value = false
  }
}

async function createAppKey() {
  if (!newAppKey.value.name.trim()) return
  creatingAppKey.value = true
  error.value = ''
  success.value = ''
  try {
    const payload = { name: newAppKey.value.name.trim() }
    if (newAppKey.value.expiresAt) {
      payload.expires_at = new Date(newAppKey.value.expiresAt).toISOString()
    }
    const res = await axios.post('/api/user/app-keys', payload)
    createdAppKey.value = res.data?.app_key || ''
    success.value = 'API 密钥创建成功'
    newAppKey.value = { name: '', expiresAt: '' }
    showCreateForm.value = false
    await loadAppKeys()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '创建 API 密钥失败'
  } finally {
    creatingAppKey.value = false
  }
}

async function toggleAppKey(keyId) {
  error.value = ''
  success.value = ''
  try {
    await axios.put(`/api/user/app-keys/${keyId}/toggle`)
    success.value = 'API 密钥状态已更新'
    await loadAppKeys()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '更新 API 密钥状态失败'
  }
}

async function removeAppKey(keyId) {
  if (!window.confirm('确定删除该 API 密钥吗？删除后不可恢复。')) return
  error.value = ''
  success.value = ''
  try {
    await axios.delete(`/api/user/app-keys/${keyId}`)
    success.value = 'API 密钥已删除'
    await loadAppKeys()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '删除 API 密钥失败'
  }
}

async function handleChangePassword() {
  if (!canSubmit.value) {
    error.value = '请填写完整信息，且新密码长度至少6位，两次输入需一致'
    return
  }
  
  if (form.value.newPassword !== form.value.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  
  if (form.value.newPassword.length < 6) {
    error.value = '新密码长度至少6位'
    return
  }
  
  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    const res = await axios.post('/api/change-password', {
      old_password: form.value.oldPassword,
      new_password: form.value.newPassword
    })
    
    if (res.data.success) {
      success.value = '密码修改成功！'
      // 清空表单
      form.value = {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
      
      // 如果是必须修改密码模式，修改成功后触发事件并关闭
      if (props.requirePasswordChange) {
        // 延迟一下，让用户看到成功消息
        setTimeout(() => {
          emit('password-changed')
          emit('update:show', false)
        }, 1000)
      } else {
        // 普通模式，只显示成功消息
        // 3秒后自动关闭成功消息
        setTimeout(() => {
          success.value = ''
        }, 3000)
      }
    } else {
      error.value = res.data.error || '修改密码失败'
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message || '修改密码失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      activeTab.value = props.initialTab === 'appkeys' ? 'appkeys' : 'password'
      if (activeTab.value === 'appkeys') {
        loadAppKeys()
      }
    } else {
      resetState()
    }
  }
)
</script>

<style scoped>
.modal.show {
  display: block;
}
</style>
