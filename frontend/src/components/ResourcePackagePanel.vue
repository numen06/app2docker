<template>
  <div class="resource-package-panel min-w-0">
    <PageToolbar title="资源包管理" icon="fa-archive">
      <template #actions>
        <Button size="sm" @click="showUploadModal = true">
          <i class="fas fa-upload"></i>
          上传资源包
        </Button>
      </template>
    </PageToolbar>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState
      v-else-if="packages.length === 0"
      message='暂无资源包，请点击「上传资源包」添加'
      icon="fa-archive"
    />

    <template v-else>
      <div class="space-y-3 md:hidden">
        <div
          v-for="pkg in packages"
          :key="`mobile-${pkg.package_id}`"
          class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
        >
          <div class="min-w-0">
            <div class="font-medium text-slate-900">
              {{ pkg.name }}
              <i
                v-if="pkg.extracted"
                class="fas fa-folder-open ml-1 text-sky-600"
                title="已解压"
              ></i>
            </div>
            <p class="mt-1 text-xs text-slate-600">{{ pkg.description || "无描述" }}</p>
            <dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-slate-600">
              <dt>大小</dt>
              <dd>{{ formatBytes(pkg.size) }}</dd>
              <dt>上传</dt>
              <dd>{{ formatTime(pkg.created_at) }}</dd>
            </dl>
          </div>
          <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3">
            <Button
              v-if="isTextFile(pkg.name)"
              variant="outline"
              size="sm"
              title="编辑"
              @click="editPackage(pkg)"
            >
              <i class="fas fa-edit"></i>
            </Button>
            <Button variant="destructive" size="sm" title="删除" @click="deletePackage(pkg)">
              <i class="fas fa-trash"></i>
            </Button>
          </div>
        </div>
      </div>

      <div class="hidden md:block">
        <Table min-width-class="min-w-[44rem]">
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>文件大小</TableHead>
              <TableHead>上传时间</TableHead>
              <TableHead class="text-end">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="pkg in packages" :key="pkg.package_id">
              <TableCell class="font-medium text-slate-900">
                {{ pkg.name }}
                <i
                  v-if="pkg.extracted"
                  class="fas fa-folder-open ml-1 text-sky-600"
                  title="已解压"
                ></i>
              </TableCell>
              <TableCell class="text-slate-600">{{ pkg.description || "无描述" }}</TableCell>
              <TableCell>{{ formatBytes(pkg.size) }}</TableCell>
              <TableCell class="text-slate-600">{{ formatTime(pkg.created_at) }}</TableCell>
              <TableCell class="text-end">
                <div class="flex justify-end gap-1">
                  <Button
                    v-if="isTextFile(pkg.name)"
                    variant="outline"
                    size="sm"
                    title="编辑"
                    @click="editPackage(pkg)"
                  >
                    <i class="fas fa-edit"></i>
                  </Button>
                  <Button variant="destructive" size="sm" title="删除" @click="deletePackage(pkg)">
                    <i class="fas fa-trash"></i>
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </template>

    <FormDialog v-model="showUploadModal" title="上传资源包" icon="fa-upload">
      <form class="space-y-4" @submit.prevent="uploadPackage">
        <div class="space-y-2">
          <Label>选择文件</Label>
          <input
            ref="fileInput"
            type="file"
            class="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
            required
            @change="handleFileSelect"
          />
          <p class="text-xs text-slate-500">支持任意类型的文件（配置文件、密钥、证书等）</p>
        </div>
        <div class="space-y-2">
          <Label>描述（可选）</Label>
          <textarea
            v-model="uploadForm.description"
            rows="3"
            class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="请输入资源包的描述信息…"
          ></textarea>
        </div>
        <label v-if="isArchiveFile" class="flex cursor-pointer items-center gap-2 text-sm">
          <input v-model="uploadForm.extract" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
          自动解压（检测到压缩包格式）
        </label>
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="showUploadModal = false">取消</Button>
        <Button type="button" :disabled="uploading || !selectedFile" @click="uploadPackage">
          <i v-if="uploading" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-upload"></i>
          {{ uploading ? "上传中…" : "上传" }}
        </Button>
      </template>
    </FormDialog>

    <FormDialog
      v-model="showEditModal"
      :title="`编辑资源包: ${editingPackage?.name || ''}`"
      icon="fa-edit"
      size="xl"
    >
      <div v-if="loadingContent" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
        <i class="fas fa-spinner fa-spin"></i>
        加载文件内容…
      </div>
      <div v-else class="resource-package-editor space-y-2">
        <Label>文件内容</Label>
        <Codemirror
          v-model="editContent"
          :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
          :autofocus="true"
          :indent-with-tab="false"
          :tab-size="2"
          :extensions="editorExtensions"
        />
        <p class="text-xs text-slate-500">支持编辑文本文件，文件大小限制为 1MB</p>
      </div>
      <template #footer>
        <Button variant="outline" type="button" @click="showEditModal = false">取消</Button>
        <Button type="button" :disabled="saving || loadingContent" @click="savePackageContent">
          <i v-if="saving" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-save"></i>
          {{ saving ? "保存中…" : "保存" }}
        </Button>
      </template>
    </FormDialog>
  </div>
</template>

<script>
import axios from "axios";
import { Codemirror } from "vue-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { StreamLanguage } from "@codemirror/language";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { yaml as yamlLang } from "@codemirror/lang-yaml";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Label from "@/components/ui/label/Label.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";

export default {
  name: "ResourcePackagePanel",
  components: {
    Codemirror,
    PageToolbar,
    EmptyState,
    FormDialog,
    Button,
    Label,
    Table,
    TableHeader,
    TableBody,
    TableRow,
    TableHead,
    TableCell,
  },
  data() {
    return {
      packages: [],
      loading: false,
      showUploadModal: false,
      uploading: false,
      selectedFile: null,
      uploadForm: {
        description: "",
        extract: true,
      },
      showEditModal: false,
      editingPackage: null,
      editContent: "",
      loadingContent: false,
      saving: false,
    };
  },
  computed: {
    isArchiveFile() {
      if (!this.selectedFile) return false;
      const fileName = this.selectedFile.name.toLowerCase();
      return (
        fileName.endsWith(".zip") ||
        fileName.endsWith(".tar") ||
        fileName.endsWith(".tar.gz") ||
        fileName.endsWith(".tgz")
      );
    },
    editorExtensions() {
      if (!this.editingPackage) {
        return [oneDark];
      }

      const filename = this.editingPackage.name.toLowerCase();
      const extensions = [oneDark];

      if (filename.endsWith(".json")) {
        extensions.push(StreamLanguage.define(javascript));
      } else if (filename.endsWith(".yaml") || filename.endsWith(".yml")) {
        extensions.push(yamlLang());
      } else if (
        filename.endsWith(".js") ||
        filename.endsWith(".jsx") ||
        filename.endsWith(".mjs") ||
        filename.endsWith(".ts") ||
        filename.endsWith(".tsx")
      ) {
        extensions.push(StreamLanguage.define(javascript));
      } else if (
        filename.endsWith(".sh") ||
        filename.endsWith(".bash") ||
        filename.endsWith(".dockerfile")
      ) {
        extensions.push(StreamLanguage.define(shell));
      } else {
        extensions.push(StreamLanguage.define(shell));
      }

      return extensions;
    },
  },
  mounted() {
    this.loadPackages();
  },
  methods: {
    async loadPackages() {
      this.loading = true;
      try {
        const res = await axios.get("/api/resource-packages");
        if (res.data.success) {
          this.packages = res.data.packages || [];
        }
      } catch (error) {
        console.error("加载资源包列表失败:", error);
        alert("加载资源包列表失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },
    handleFileSelect(event) {
      this.selectedFile = event.target.files[0];
    },
    async uploadPackage() {
      if (!this.selectedFile) {
        alert("请选择文件");
        return;
      }

      this.uploading = true;
      try {
        const formData = new FormData();
        formData.append("package_file", this.selectedFile);
        formData.append("description", this.uploadForm.description);
        formData.append("extract", this.uploadForm.extract);

        const res = await axios.post("/api/resource-packages/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        if (res.data.success) {
          alert("资源包上传成功");
          this.showUploadModal = false;
          this.selectedFile = null;
          this.uploadForm = { description: "", extract: true };
          if (this.$refs.fileInput) {
            this.$refs.fileInput.value = "";
          }
          this.loadPackages();
        }
      } catch (error) {
        console.error("上传资源包失败:", error);
        alert("上传资源包失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.uploading = false;
      }
    },
    async deletePackage(pkg) {
      if (!confirm(`确定要删除资源包 "${pkg.name}" 吗？`)) {
        return;
      }

      try {
        const res = await axios.delete(`/api/resource-packages/${pkg.package_id}`);
        if (res.data.success) {
          alert("资源包已删除");
          this.loadPackages();
        }
      } catch (error) {
        console.error("删除资源包失败:", error);
        alert("删除资源包失败: " + (error.response?.data?.detail || error.message));
      }
    },
    formatBytes(bytes) {
      if (!bytes) return "0 B";
      const k = 1024;
      const sizes = ["B", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
    },
    formatTime(timeStr) {
      if (!timeStr) return "-";
      const date = new Date(timeStr);
      return date.toLocaleString("zh-CN");
    },
    isTextFile(filename) {
      if (!filename) return false;
      const textExtensions = [
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
        ".properties",
        ".conf",
        ".config",
        ".ini",
        ".env",
        ".sh",
        ".bash",
        ".py",
        ".js",
        ".ts",
        ".java",
        ".go",
        ".rs",
        ".md",
        ".log",
        ".sql",
        ".csv",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".vue",
        ".tsx",
        ".jsx",
        ".dockerfile",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
      ];
      const filenameLower = filename.toLowerCase();
      return textExtensions.some((ext) => filenameLower.endsWith(ext));
    },
    async editPackage(pkg) {
      this.editingPackage = pkg;
      this.showEditModal = true;
      this.loadingContent = true;
      this.editContent = "";

      try {
        const res = await axios.get(`/api/resource-packages/${pkg.package_id}/content`);
        if (res.data.success) {
          this.editContent = res.data.content || "";
        }
      } catch (error) {
        console.error("加载资源包内容失败:", error);
        alert("加载资源包内容失败: " + (error.response?.data?.detail || error.message));
        this.showEditModal = false;
      } finally {
        this.loadingContent = false;
      }
    },
    async savePackageContent() {
      if (!this.editingPackage) return;

      this.saving = true;
      try {
        const res = await axios.put(
          `/api/resource-packages/${this.editingPackage.package_id}/content`,
          { content: this.editContent }
        );

        if (res.data.success) {
          alert("文件已保存");
          this.showEditModal = false;
          this.editingPackage = null;
          this.editContent = "";
          this.loadPackages();
        }
      } catch (error) {
        console.error("保存资源包内容失败:", error);
        alert("保存资源包内容失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>

<style scoped>
@media (max-width: 767px) {
  .resource-package-editor :deep(.cm-editor) {
    height: min(50vh, 360px) !important;
  }
}
</style>
