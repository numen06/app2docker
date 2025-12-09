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
            <!-- Docker 构建配置 -->
            <h6 class="mb-3 text-primary">
              <i class="fas fa-server"></i> Docker 构建配置
            </h6>
            
            <!-- 编译模式选择 -->
            <div class="mb-4">
              <label class="form-label fw-bold">
                <i class="fas fa-cogs"></i> 编译模式 <span class="text-danger">*</span>
              </label>
              <div class="alert alert-info alert-sm mb-3">
                <i class="fas fa-info-circle"></i> 
                <strong>全局设置：</strong>选择的编译模式将应用于所有构建任务
              </div>
              <div class="row g-2">
                <div class="col-md-4">
                  <div class="card h-100" :class="{ 'border-primary': buildMode === 'local' }" style="cursor: pointer;" @click="buildMode = 'local'">
                    <div class="card-body">
                      <div class="form-check">
                        <input 
                          v-model="buildMode" 
                          type="radio" 
                          value="local"
                          class="form-check-input" 
                          id="buildModeLocal"
                        />
                        <label class="form-check-label fw-bold" for="buildModeLocal">
                          <i class="fas fa-cube text-success"></i> 容器内编译
                        </label>
                      </div>
                      <small class="text-muted d-block mt-2">
                        通过挂载的 docker.sock 连接本地 Docker<br/>
                        <span class="text-warning"><i class="fas fa-exclamation-triangle"></i> 支持复杂编译流程</span>
                      </small>
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="card h-100" :class="{ 'border-primary': buildMode === 'tcp2375' }" style="cursor: pointer;" @click="buildMode = 'tcp2375'">
                    <div class="card-body">
                      <div class="form-check">
                        <input 
                          v-model="buildMode" 
                          type="radio" 
                          value="tcp2375"
                          class="form-check-input" 
                          id="buildModeTcp2375"
                        />
                        <label class="form-check-label fw-bold" for="buildModeTcp2375">
                          <i class="fas fa-network-wired text-warning"></i> 远程 Docker (TCP)
                        </label>
                      </div>
                      <small class="text-muted d-block mt-2">
                        通过 TCP 端口连接远程 Docker<br/>
                        <span class="text-danger"><i class="fas fa-shield-alt"></i> 明文传输，不安全</span>
                      </small>
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="card h-100" :class="{ 'border-primary': buildMode === 'tls' }" style="cursor: pointer;" @click="buildMode = 'tls'">
                    <div class="card-body">
                      <div class="form-check">
                        <input 
                          v-model="buildMode" 
                          type="radio" 
                          value="tls"
                          class="form-check-input" 
                          id="buildModeTls"
                        />
                        <label class="form-check-label fw-bold" for="buildModeTls">
                          <i class="fas fa-lock text-success"></i> 远程 Docker (TLS)
                        </label>
                      </div>
                      <small class="text-muted d-block mt-2">
                        通过 TLS 加密连接远程 Docker<br/>
                        <span class="text-success"><i class="fas fa-shield-alt"></i> 安全，推荐生产环境</span>
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="row g-3 mb-4">
              
              <!-- 远程 Docker 配置（仅在选择远程模式时显示） -->
              <template v-if="buildMode === 'tcp2375' || buildMode === 'tls'">
                <div class="col-12">
                  <div class="alert alert-info mb-3">
                    <i class="fas fa-info-circle"></i> 
                    远程 Docker 配置需要确保远程主机的 Docker 守护进程已开启 TCP 访问
                  </div>
                </div>
                <div class="col-md-8">
                  <label class="form-label">远程主机地址 *</label>
                  <input 
                    v-model="config.remote.host" 
                    type="text" 
                    class="form-control" 
                    placeholder="192.168.1.100"
                    :required="config.use_remote"
                  />
                </div>
                <div class="col-md-4">
                  <label class="form-label">端口</label>
                  <input 
                    v-model.number="config.remote.port" 
                    type="number" 
                    class="form-control" 
                    :placeholder="buildMode === 'tls' ? '2376' : '2375'"
                  />
                  <small class="text-muted">
                    默认端口：{{ buildMode === 'tls' ? '2376 (TLS)' : '2375 (TCP)' }}
                  </small>
                </div>
                <div class="col-md-6" v-if="buildMode === 'tls'">
                  <div class="alert alert-success alert-sm mb-0">
                    <i class="fas fa-check-circle"></i> TLS 加密连接已启用
                  </div>
                </div>
                <div class="col-md-6" v-if="buildMode === 'tls'">
                  <div class="form-check">
                    <input 
                      v-model="config.remote.verify_tls" 
                      type="checkbox" 
                      class="form-check-input" 
                      id="remoteVerifyTls"
                    />
                    <label class="form-check-label" for="remoteVerifyTls">
                      验证 TLS 证书
                    </label>
                  </div>
                </div>
                <div class="col-md-12" v-if="buildMode === 'tls'">
                  <label class="form-label">证书路径</label>
                  <input 
                    v-model="config.remote.cert_path" 
                    type="text" 
                    class="form-control" 
                    placeholder="/path/to/certs"
                  />
                  <small class="text-muted">
                    证书目录应包含 ca.pem, cert.pem, key.pem
                  </small>
                </div>
              </template>
            </div>

            <!-- 镜像仓库配置已移至数据源配置页面 -->
            <div class="alert alert-info mb-4">
              <i class="fas fa-info-circle"></i> 
              <strong>提示：</strong>镜像仓库配置已移至<strong>数据源配置页面</strong>的"镜像仓库"标签页，请前往该页面进行配置。
            </div>

            <!-- 其他配置 -->
            <div class="row g-3 mb-4">
              <div class="col-md-6">
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
              <div class="col-md-12 d-flex justify-content-end">
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
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const config = ref({
  expose_port: 8080,
  default_push: false,  // 默认不推送
  use_remote: false,  // 是否使用远程 Docker
  remote: {
    host: '',
    port: 2375,
    use_tls: false,
    cert_path: '',
    verify_tls: true
  }
})

// 编译模式：'local' | 'tcp2375' | 'tls'
const buildMode = ref('local')

const saving = ref(false)

async function loadConfig() {
  try {
    console.log('📥 正在加载配置...')
    const res = await axios.get('/api/get-config')
    console.log('📋 配置响应:', res.data)
    
    const docker = res.data.docker || {}
    const remote = docker.remote || {}
    
    config.value = {
      expose_port: docker.expose_port || 8080,
      default_push: docker.default_push === true,  // 布尔值必须严格判断
      use_remote: docker.use_remote === true,
      remote: {
        host: remote.host || '',
        port: remote.port || 2375,
        use_tls: remote.use_tls === true,
        cert_path: remote.cert_path || '',
        verify_tls: remote.verify_tls !== false  // 默认为 true
      }
    }
    
    // 根据配置确定编译模式
    if (!config.value.use_remote) {
      buildMode.value = 'local'
    } else if (config.value.remote.use_tls) {
      buildMode.value = 'tls'
    } else {
      buildMode.value = 'tcp2375'
    }
    
    console.log('✅ 配置已加载:', config.value)
    console.log('✅ 编译模式:', buildMode.value)
  } catch (error) {
    console.error('❌ 加载配置失败:', error)
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message
    alert(`加载配置失败: ${errorMsg}`)
  }
}

async function save() {
  saving.value = true
  try {
    // 根据选择的编译模式更新配置
    if (buildMode.value === 'local') {
      config.value.use_remote = false
    } else {
      config.value.use_remote = true
      if (buildMode.value === 'tls') {
        config.value.remote.use_tls = true
        // TLS 模式默认端口 2376
        if (!config.value.remote.port || config.value.remote.port === 2375) {
          config.value.remote.port = 2376
        }
      } else if (buildMode.value === 'tcp2375') {
        config.value.remote.use_tls = false
        // TCP 2375 模式默认端口 2375
        if (!config.value.remote.port || config.value.remote.port === 2376) {
          config.value.remote.port = 2375
        }
      }
    }
    
    // 保存配置
    const formData = new FormData()
    
    formData.append('expose_port', String(config.value.expose_port))
    formData.append('default_push', config.value.default_push ? 'on' : 'off')
    
    // 添加远程 Docker 配置
    formData.append('use_remote', config.value.use_remote ? 'on' : 'off')
    formData.append('remote_host', config.value.remote.host)
    formData.append('remote_port', String(config.value.remote.port))
    formData.append('remote_use_tls', config.value.remote.use_tls ? 'on' : 'off')
    formData.append('remote_cert_path', config.value.remote.cert_path)
    formData.append('remote_verify_tls', config.value.remote.verify_tls ? 'on' : 'off')
    
    console.log('📤 发送配置:', Object.fromEntries(formData))
    
    const res = await axios.post('/api/save-config', formData)
    console.log('✅ 其他配置保存成功:', res.data)
    
    // 保存成功后重新加载配置以验证
    await loadConfig()
    
    alert('配置保存成功')
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

// 监听编译模式变化，自动更新端口
watch(buildMode, (newMode) => {
  if (newMode === 'tls') {
    // TLS 模式默认端口 2376
    if (!config.value.remote.port || config.value.remote.port === 2375) {
      config.value.remote.port = 2376
    }
  } else if (newMode === 'tcp2375') {
    // TCP 2375 模式默认端口 2375
    if (!config.value.remote.port || config.value.remote.port === 2376) {
      config.value.remote.port = 2375
    }
  }
})

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
</script>

<style scoped>
.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}

.alert-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  margin-bottom: 0;
}

.alert-sm ul {
  margin-top: 0.25rem;
}
</style>

