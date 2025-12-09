<template>
  <div class="resource-package-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h6 class="mb-0">
        <i class="fas fa-archive"></i> 资源包管理
      </h6>
      <button class="btn btn-primary btn-sm" @click="showUploadModal = true">
        <i class="fas fa-upload"></i> 上传资源包
      </button>
    </div>

    <!-- 资源包列表 -->
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>名称</th>
            <th>描述</th>
            <th>文件大小</th>
            <th>上传时间</th>
            <th class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </td>
          </tr>
          <tr v-else-if="packages.length === 0">
            <td colspan="5" class="text-center text-muted py-4">
              <i class="fas fa-archive fa-2x mb-2 d-block"></i>
              暂无资源包，请点击"上传资源包"添加
            </td>
          </tr>
          <tr v-for="pkg in packages" :key="pkg.package_id">
            <td>
              <strong>{{ pkg.name }}</strong>
              <i v-if="pkg.extracted" class="fas fa-folder-open text-info ms-1" title="已解压"></i>
            </td>
            <td>
              <span class="text-muted small">{{ pkg.description || '无描述' }}</span>
            </td>
            <td>{{ formatBytes(pkg.size) }}</td>
            <td>{{ formatTime(pkg.created_at) }}</td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <button 
                  v-if="isTextFile(pkg.name)"
                  class="btn btn-outline-primary" 
                  @click="editPackage(pkg)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="deletePackage(pkg)"
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

    <!-- 上传模态框 -->
    <div v-if="showUploadModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showUploadModal = false">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-upload"></i> 上传资源包
            </h5>
            <button type="button" class="btn-close" @click="showUploadModal = false"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="uploadPackage">
              <div class="mb-3">
                <label class="form-label">选择文件</label>
                <input 
                  type="file" 
                  class="form-control" 
                  ref="fileInput"
                  @change="handleFileSelect"
                  required
                />
                <small class="text-muted">支持任意类型的文件（配置文件、密钥、证书等）</small>
              </div>
              <div class="mb-3">
                <label class="form-label">描述（可选）</label>
                <textarea 
                  class="form-control" 
                  v-model="uploadForm.description"
                  rows="3"
                  placeholder="请输入资源包的描述信息..."
                ></textarea>
              </div>
              <div class="mb-3" v-if="isArchiveFile">
                <div class="form-check">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    v-model="uploadForm.extract"
                    id="extractCheck"
                  />
                  <label class="form-check-label" for="extractCheck">
                    自动解压（检测到压缩包格式）
                  </label>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showUploadModal = false">
              取消
            </button>
            <button 
              type="button" 
              class="btn btn-primary" 
              @click="uploadPackage"
              :disabled="uploading || !selectedFile"
            >
              <span v-if="uploading" class="spinner-border spinner-border-sm me-2"></span>
              <i v-else class="fas fa-upload me-2"></i>
              {{ uploading ? '上传中...' : '上传' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑模态框 -->
    <div v-if="showEditModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showEditModal = false">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-edit"></i> 编辑资源包: {{ editingPackage?.name }}
            </h5>
            <button type="button" class="btn-close" @click="showEditModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="loadingContent" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载文件内容...
            </div>
            <div v-else>
              <div class="mb-3">
                <label class="form-label">文件内容</label>
                <codemirror
                  v-model="editContent"
                  :style="{ height: '500px', fontSize: '13px' }"
                  :autofocus="true"
                  :indent-with-tab="false"
                  :tab-size="2"
                  :extensions="editorExtensions"
                />
                <small class="text-muted">支持编辑文本文件，文件大小限制为 1MB</small>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showEditModal = false">
              取消
            </button>
            <button 
              type="button" 
              class="btn btn-primary" 
              @click="savePackageContent"
              :disabled="saving || loadingContent"
            >
              <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
              <i v-else class="fas fa-save me-2"></i>
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'
import { javascript } from '@codemirror/legacy-modes/mode/javascript'
import { yaml as yamlLang } from '@codemirror/lang-yaml'

export default {
  name: 'ResourcePackagePanel',
  components: {
    Codemirror
  },
  data() {
    return {
      packages: [],
      loading: false,
      showUploadModal: false,
      uploading: false,
      selectedFile: null,
      uploadForm: {
        description: '',
        extract: true
      },
      showEditModal: false,
      editingPackage: null,
      editContent: '',
      loadingContent: false,
      saving: false
    }
  },
  computed: {
    isArchiveFile() {
      if (!this.selectedFile) return false
      const fileName = this.selectedFile.name.toLowerCase()
      return fileName.endsWith('.zip') || 
             fileName.endsWith('.tar') || 
             fileName.endsWith('.tar.gz') || 
             fileName.endsWith('.tgz')
    },
    editorExtensions() {
      if (!this.editingPackage) {
        return [oneDark]
      }
      
      const filename = this.editingPackage.name.toLowerCase()
      const extensions = [oneDark]
      
      // 根据文件扩展名选择语言模式
      if (filename.endsWith('.json')) {
        // JSON 使用 JavaScript 模式
        extensions.push(StreamLanguage.define(javascript))
      } else if (filename.endsWith('.yaml') || filename.endsWith('.yml')) {
        extensions.push(yamlLang())
      } else if (filename.endsWith('.js') || filename.endsWith('.jsx') || filename.endsWith('.mjs') || 
                 filename.endsWith('.ts') || filename.endsWith('.tsx')) {
        extensions.push(StreamLanguage.define(javascript))
      } else if (filename.endsWith('.sh') || filename.endsWith('.bash') || filename.endsWith('.dockerfile')) {
        extensions.push(StreamLanguage.define(shell))
      } else {
        // 默认使用 shell 模式（适合配置文件）
        extensions.push(StreamLanguage.define(shell))
      }
      
      return extensions
    }
  },
  mounted() {
    this.loadPackages()
  },
  methods: {
    async loadPackages() {
      this.loading = true
      try {
        const res = await axios.get('/api/resource-packages')
        if (res.data.success) {
          this.packages = res.data.packages || []
        }
      } catch (error) {
        console.error('加载资源包列表失败:', error)
        alert('加载资源包列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
      }
    },
    handleFileSelect(event) {
      this.selectedFile = event.target.files[0]
    },
    async uploadPackage() {
      if (!this.selectedFile) {
        alert('请选择文件')
        return
      }

      this.uploading = true
      try {
        const formData = new FormData()
        formData.append('package_file', this.selectedFile)
        formData.append('description', this.uploadForm.description)
        formData.append('extract', this.uploadForm.extract)

        const res = await axios.post('/api/resource-packages/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        if (res.data.success) {
          alert('资源包上传成功')
          this.showUploadModal = false
          this.selectedFile = null
          this.uploadForm = { description: '', extract: true }
          if (this.$refs.fileInput) {
            this.$refs.fileInput.value = ''
          }
          this.loadPackages()
        }
      } catch (error) {
        console.error('上传资源包失败:', error)
        alert('上传资源包失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.uploading = false
      }
    },
    async deletePackage(pkg) {
      if (!confirm(`确定要删除资源包 "${pkg.name}" 吗？`)) {
        return
      }

      try {
        const res = await axios.delete(`/api/resource-packages/${pkg.package_id}`)
        if (res.data.success) {
          alert('资源包已删除')
          this.loadPackages()
        }
      } catch (error) {
        console.error('删除资源包失败:', error)
        alert('删除资源包失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    formatBytes(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    },
    formatTime(timeStr) {
      if (!timeStr) return '-'
      const date = new Date(timeStr)
      return date.toLocaleString('zh-CN')
    },
    isTextFile(filename) {
      if (!filename) return false
      const textExtensions = ['.txt', '.json', '.yaml', '.yml', '.xml', '.properties', 
                              '.conf', '.config', '.ini', '.env', '.sh', '.bash', 
                              '.py', '.js', '.ts', '.java', '.go', '.rs', '.md', 
                              '.log', '.sql', '.csv', '.html', '.css', '.scss', 
                              '.less', '.vue', '.tsx', '.jsx', '.dockerfile', 
                              '.gitignore', '.gitattributes', '.editorconfig']
      const filenameLower = filename.toLowerCase()
      return textExtensions.some(ext => filenameLower.endsWith(ext))
    },
    async editPackage(pkg) {
      this.editingPackage = pkg
      this.showEditModal = true
      this.loadingContent = true
      this.editContent = ''
      
      try {
        const res = await axios.get(`/api/resource-packages/${pkg.package_id}/content`)
        if (res.data.success) {
          this.editContent = res.data.content || ''
        }
      } catch (error) {
        console.error('加载资源包内容失败:', error)
        alert('加载资源包内容失败: ' + (error.response?.data?.detail || error.message))
        this.showEditModal = false
      } finally {
        this.loadingContent = false
      }
    },
    async savePackageContent() {
      if (!this.editingPackage) return
      
      this.saving = true
      try {
        const res = await axios.put(`/api/resource-packages/${this.editingPackage.package_id}/content`, {
          content: this.editContent
        })
        
        if (res.data.success) {
          alert('文件已保存')
          this.showEditModal = false
          this.editingPackage = null
          this.editContent = ''
          // 重新加载资源包列表以更新文件大小
          this.loadPackages()
        }
      } catch (error) {
        console.error('保存资源包内容失败:', error)
        alert('保存资源包内容失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style scoped>
.resource-package-panel {
  padding: 0;
}

.modal.show {
  display: block;
}
</style>

