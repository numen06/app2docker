"""One-off script to generate usePipelineEditor.js from PipelinePanel extract."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
chunk_path = ROOT / "src/components/pipeline/_script_chunk.js"
out_path = ROOT / "src/composables/usePipelineEditor.js"

content = chunk_path.read_text(encoding="utf-8")
content = re.sub(r"^<script setup>\s*", "", content)
content = re.sub(r"</script>\s*$", "", content)

content = content.replace(
    'import Button from "@/components/ui/button/Button.vue";\n'
    'import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";\n',
    "",
)
content = content.replace("from '../utils/", "from '@/utils/")
content = content.replace(
    "import { copyToClipboard } from '../utils/clipboard.js';",
    "",
)

content = re.sub(
    r"const permissionDialogOpen = ref\(false\);\s*"
    r"const permissionTarget = ref\(null\);\s*"
    r"function openResourcePermission\(pipeline\) \{[^}]+\}\s*",
    "",
    content,
    count=1,
)

# Drop list / modal-only state (minimal pipelines kept for duplicate check)
drops = [
    r"const running = ref\(null\);.*?const isVerifyingServices = ref\(false\);\s*",
    r"const showModal = ref\(false\);\s*",
    r"const showWebhookModal = ref\(false\);\s*"
    r"const showHistoryModal = ref\(false\);\s*"
    r"const showMultiServiceConfigModal = ref\(false\);\s*"
    r"const showManualRunModal = ref\(false\);.*?global_tag: \"latest\",\s*\}\);\s*",
    r"const webhookUrl = ref\(\"\"\);.*?const showResourcePackageModal = ref\(false\);\s*",
    r"const showJsonCreateModal = ref\(false\);.*?git_url: \"\",\s*\}\);\s*",
]
for pat in drops:
    content = re.sub(pat, "", content, flags=re.DOTALL)

content = re.sub(
    r"onMounted\(\(\) => \{.*?\}\);\s*",
    """onMounted(() => {
  loadProjectTypes();
  loadTemplates();
  loadRegistries();
  loadGitSources();
  loadResourcePackages();
  loadDeployTasks();
});

""",
    content,
    count=1,
    flags=re.DOTALL,
)

content = content.replace("function showCreateModal()", "function initCreateForm()")
content = re.sub(r"\s*showModal\.value = true;\s*", "\n", content)
content = content.replace(
    "function editPipeline(pipeline)", "function applyPipelineToForm(pipeline)"
)

content = content.replace(
    "    closeModal();\n    loadPipelines();",
    "    if (onSaved) onSaved();\n    return true;",
)

content = re.sub(
    r"function closeModal\(\) \{.*?\n\}\s*",
    """function resetFormState() {
  editingPipeline.value = null;
  services.value = [];
  loadingServices.value = false;
  servicesError.value = "";
  branchesAndTags.value = { branches: [], tags: [], default_branch: null };
  availableDockerfiles.value = [];
  refreshingBranches.value = false;
  scanningDockerfiles.value = false;
  dockerfilesError.value = "";
  repoVerified.value = false;
}

""",
    content,
    count=1,
    flags=re.DOTALL,
)

for fn in [
    "openJsonCreateModal",
    "updateJsonFromForm",
    "closeJsonCreateModal",
    "createPipelineFromJson",
]:
    content = re.sub(rf"function {fn}\(\) \{{.*?\n\}}\s*", "", content, flags=re.DOTALL)
    content = re.sub(rf"async function {fn}\(\) \{{.*?\n\}}\s*", "", content, flags=re.DOTALL)

content = re.sub(
    r"async function loadPipelines\(\) \{.*?\n\}\s*",
    """async function fetchPipelineNames() {
  try {
    const res = await axios.get("/api/pipelines");
    pipelines.value = res.data.pipelines || [];
  } catch (error) {
    console.error("加载流水线列表失败:", error);
    pipelines.value = [];
  }
}

""",
    content,
    count=1,
    flags=re.DOTALL,
)

content = re.sub(r"^import .*?\n", "", content, count=25)
content = content.replace("const teamStore = useTeamStore();\n\n", "")

content = content.replace(
    "    const duplicatePipeline = pipelines.value.find",
    "    await fetchPipelineNames();\n    const duplicatePipeline = pipelines.value.find",
)

content = content.replace(
    "        saving.value = false;\n        return;\n",
    "        saving.value = false;\n        return false;\n",
)

if "function formatGitUrl" not in content:
    content += '''
function formatGitUrl(url) {
  if (!url) return "";
  return url.replace(/^https?:\\/\\//, "").replace(/\\.git$/, "");
}

'''

if "async function loadProjectTypes" not in content:
    content += '''
async function loadProjectTypes() {
  projectTypesList.value = await getProjectTypes();
}

'''

if "function copyBuildConfigJson" not in content:
    content += '''
async function copyBuildConfigJson() {
  const text = buildConfigJson.value;
  const success = await copyToClipboard(text);
  if (success) {
    alert("构建配置JSON已复制到剪贴板");
  } else {
    alert("自动复制失败，请手动选择并复制文本");
  }
}

'''

header = '''import { useTeamStore } from "@/stores/team";
import { StreamLanguage } from "@codemirror/language";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import axios from "axios";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { copyToClipboard } from "@/utils/clipboard.js";
import { getDockerfilesWithCache } from "@/utils/dockerfileCache.js";
import {
  getGitCache,
  getGitInfoWithCache,
  setGitCache,
} from "@/utils/gitCache.js";
import { getServiceAnalysisWithCache } from "@/utils/serviceAnalysisCache.js";
import {
  getProjectTypes,
  getProjectTypesSync,
} from "@/utils/projectTypes.js";

export function usePipelineEditor({ onSaved } = {}) {
  const teamStore = useTeamStore();

'''

footer = '''
  async function loadPipelineForEdit(pipelineId) {
    try {
      const res = await axios.get(`/api/pipelines/${pipelineId}`);
      const pipeline = res.data?.pipeline ?? res.data;
      if (!pipeline || !pipeline.pipeline_id) {
        alert("流水线不存在");
        return false;
      }
      await fetchPipelineNames();
      activeTab.value = "basic";
      applyPipelineToForm(pipeline);
      return true;
    } catch (error) {
      console.error("加载流水线失败:", error);
      alert(error.response?.data?.detail || "加载流水线失败");
      return false;
    }
  }

  return {
    teamStore,
    projectTypesList,
    pipelines,
    templates,
    registries,
    gitSources,
    saving,
    editingPipeline,
    deployTaskList,
    services,
    loadingServices,
    servicesError,
    branchesAndTags,
    refreshingBranches,
    availableDockerfiles,
    scanningDockerfiles,
    dockerfilesError,
    repoVerified,
    activeTab,
    showBuildConfigJsonModal,
    buildConfigJsonText,
    buildConfigJsonError,
    dockerfileContentText,
    loadingDockerfile,
    jsonEditorExtensions,
    dockerfileEditorExtensions,
    formData,
    resourcePackages,
    filteredTemplates,
    buildConfigJson,
    isAllBranchesSelected,
    initCreateForm,
    applyPipelineToForm,
    loadPipelineForEdit,
    savePipeline,
    resetFormState,
    loadGitSources,
    onSourceSelected,
    normalizeAsciiCommaSeparators,
    onPostBuildWebhookBranchesInput,
    closeBuildConfigJsonModal,
    resetBuildConfigJson,
    applyBuildConfigJson,
    loadDockerfileFromRepo,
    applyDockerfileContent,
    addBranchTagMapping,
    addPostBuildWebhook,
    removePostBuildWebhook,
    removeBranchTagMapping,
    toggleAllBranches,
    refreshBranches,
    scanDockerfiles,
    onBranchChanged,
    loadServices,
    onPushModeChange,
    toggleService,
    onServiceSelectionChange,
    selectAllServices,
    deselectAllServices,
    removeService,
    getServiceConfig,
    getServiceDefaultImageName,
    onServiceImageNameBlur,
    resetServiceImageName,
    toggleResourcePackage,
    isResourcePackageSelected,
    getResourcePackageName,
    removeResourcePackage,
    getResourcePackageConfig,
    updateResourcePackagePath,
    onDockerfileSourceChange,
    onTemplateChange,
    getDeployWebhookUrl,
    onDeployTaskSelected,
    formatGitUrl,
    regenerateWebhookToken,
    regenerateWebhookSecret,
    generateUUID,
    copyBuildConfigJson,
  };
}
'''

out_path.write_text(header + content + footer, encoding="utf-8")
print("Wrote", out_path, "bytes", out_path.stat().st_size)
