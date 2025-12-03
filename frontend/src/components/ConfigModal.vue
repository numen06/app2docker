<template>
  <div 
    class="modal fade" 
    :class="{ show: modelValue, 'd-block': modelValue }"
    tabindex="-1"
    @click.self="close"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header bg-primary text-white">
          <h5 class="modal-title">
            <i class="fas fa-cog"></i> Docker 配置
          </h5>
          <button type="button" class="btn-close btn-close-white" @click="close"></button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="save">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Registry 地址</label>
                <input 
                  v-model="config.registry" 
                  type="text" 
                  class="form-control" 
                  placeholder="docker.io"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label">镜像前缀（可选）</label>
                <input 
                  v-model="config.registry_prefix" 
                  type="text" 
                  class="form-control" 
                  placeholder="your-namespace"
                />
              </div>
              <div class="col-md-4">
                <label class="form-label">账号</label>
                <input v-model="config.username" type="text" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">密码</label>
                <input v-model="config.password" type="password" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">暴露端口</label>
                <input v-model.number="config.expose_port" type="number" class="form-control" />
              </div>
              <div class="col-md-6 d-flex align-items-end">
                <div class="form-check">
                  <input 
                    v-model="config.default_push" 
                    type="checkbox" 
                    class="form-check-input" 
                    id="defaultPush"
                  />
                  <label class="form-check-label" for="defaultPush">
                    默认推送镜像
                  </label>
                </div>
              </div>
              <div class="col-md-6 d-flex align-items-end justify-content-end">
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  <i class="fas fa-save"></i> 
                  {{ saving ? '保存中...' : '保存配置' }}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
  
  <div v-if="modelValue" class="modal-backdrop fade show"></div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const config = ref({
  registry: 'docker.io',
  registry_prefix: '',
  username: '',
  password: '',
  expose_port: 8080,
  default_push: false  // 默认不推送
})

const saving = ref(false)

async function loadConfig() {
  try {
    console.log('📥 正在加载配置...')
    const res = await axios.get('/api/get-config')
    console.log('📋 配置响应:', res.data)
    
    const docker = res.data.docker || {}
    config.value = {
      registry: docker.registry || 'docker.io',
      registry_prefix: docker.registry_prefix || '',
      username: docker.username || '',
      password: docker.password || '',
      expose_port: docker.expose_port || 8080,
      default_push: docker.default_push === true  // 布尔值必须严格判断
    }
    console.log('✅ 配置已加载:', config.value)
  } catch (error) {
    console.error('❌ 加载配置失败:', error)
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message
    alert(`加载配置失败: ${errorMsg}`)
  }
}

async function save() {
  saving.value = true
  try {
    const formData = new FormData()
    Object.keys(config.value).forEach(key => {
      // 确保布尔值正确转换
      const value = config.value[key]
      formData.append(key, value === true || value === false ? String(value) : value)
    })
    
    console.log('📤 发送配置:', Object.fromEntries(formData))
    
    const res = await axios.post('/api/save-config', formData)
    console.log('✅ 保存响应:', res.data)
    
    // 保存成功后重新加载配置以验证
    await loadConfig()
    
    alert(res.data.message || '配置保存成功')
    close()
  } catch (error) {
    console.error('❌ 保存配置失败:', error)
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || '保存配置失败'
    alert(errorMsg)
  } finally {
    saving.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}

// ESC键关闭
function handleEscape(e) {
  if (e.key === 'Escape' && props.modelValue) {
    console.log('✅ ConfigModal: ESC键关闭')
    close()
  }
}

watch(
  () => props.modelValue,
  (val) => {
  if (val) {
      console.log('🔔 ConfigModal: 模态框打开，开始加载配置')
    loadConfig()
  }
  },
  { immediate: true }  // 立即执行一次，确保首次打开时也会加载
)

onMounted(() => {
  console.log('📌 ConfigModal: 挂载，添加ESC监听器')
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  console.log('🗑️ ConfigModal: 卸载，移除ESC监听器')
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}
</style>

