import { useTeamStore } from "@/stores/team";
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";
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

/** 分隔列表时仅使用半角逗号：输入中的全角逗号自动转为半角 */
function normalizeAsciiCommaSeparators(s) {
  return String(s ?? "").replace(/\uFF0C/g, ",");
}

function onPostBuildWebhookBranchesInput(webhook, e) {
  const raw = normalizeAsciiCommaSeparators(e.target.value);
  webhook.branches = raw.split(",").map((b) => b.trim()).filter(Boolean);
}

// 项目类型相关
const projectTypesList = ref(getProjectTypesSync()); // 从缓存获取项目类型列表

const pipelines = ref([]);
const templates = ref([]);
const registries = ref([]);
const gitSources = ref([]);
const deployTaskList = ref([]);
const editingPipeline = ref(null);
const saving = ref(false); // 正在保存流水线
// 是否正在验证服务列表（编辑模式下防止重复验证）
// 临时存储多服务模式下的服务数据（用于单服务/多服务切换时恢复）
const multiServiceBackup = ref({
  selected_services: [],
  service_push_config: {},
});
const resourcePackages = ref([]); // 资源包列表
// 多服务相关
const services = ref([]); // 服务列表
const loadingServices = ref(false); // 加载服务中
const servicesError = ref(""); // 服务加载错误

// 分支和 Dockerfile 相关
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null,
});
const refreshingBranches = ref(false); // 正在刷新分支
const availableDockerfiles = ref([]); // 可用的 Dockerfile 列表
const scanningDockerfiles = ref(false); // 正在扫描 Dockerfile
const dockerfilesError = ref(""); // Dockerfile 扫描错误
const repoVerified = ref(false); // 仓库是否已验证

/** 创建向导：用户强制单应用（忽略 Dockerfile 多服务解析） */
const wizardForceSingleMode = ref(false);
/** 创建向导：是否已完成 Dockerfile 服务分析 */
const wizardServiceAnalysisDone = ref(false);

const activeTab = ref("basic"); // 当前激活的Tab
const showResourcePackageModal = ref(false);
const showBuildConfigJsonModal = ref(false); // 显示构建配置JSON模态框
const buildConfigJsonText = ref(""); // JSON文本内容（用于CodeMirror）
const buildConfigJsonError = ref(""); // JSON验证错误
const dockerfileContentText = ref(""); // Dockerfile文本内容（用于CodeMirror）
const loadingDockerfile = ref(false); // 正在从仓库加载Dockerfile

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [StreamLanguage.define(javascript), oneDark];

// CodeMirror 扩展配置（Dockerfile模式，使用JavaScript模式）
const dockerfileEditorExtensions = [StreamLanguage.define(javascript), oneDark];

const formData = ref({
  name: "",
  description: "",
  git_url: "",
  branch: "",
  sub_path: "",
  project_type: "jar",
  template: "",
  image_name: "",
  tag: "latest",
  push: false,
  webhook_token: "", // Webhook Token（用于 URL）
  webhook_secret: "", // Webhook 密钥
  webhook_branch_strategy: "use_push", // Webhook分支策略
  webhook_allowed_branches: [], // 允许触发的分支列表（用于选择分支触发策略）
  branch_tag_mapping: [], // 分支标签映射
  post_build_webhooks: [], // 构建完成后触发的webhook列表
  enabled: true,
  trigger_schedule: false, // 是否启用定时触发
  cron_expression: "", // Cron 表达式
  dockerfile_name: "Dockerfile", // Dockerfile文件名，默认Dockerfile
  use_project_dockerfile: true, // 是否使用项目中的 Dockerfile
  dockerfile_content: "", // Dockerfile内容（用于直接编辑）
  source_id: "", // 数据源ID
  // 多服务配置
  push_mode: "multi", // 推送模式：'single' 或 'multi'
  selected_service: "", // 单服务模式选中的服务
  selected_services: [], // 多服务模式选中的服务列表
  service_push_config: {}, // 服务推送配置 {服务名: {imageName, tag, push}}
  service_template_params: {}, // 服务模板参数
  resource_package_configs: [], // 资源包配置
});

onMounted(() => {
  loadProjectTypes();
  loadTemplates();
  loadRegistries();
  loadGitSources();
  loadResourcePackages();
  loadDeployTasks();
});

async function loadGitSources() {
  try {
    const res = await axios.get("/api/git-sources");
    gitSources.value = res.data.sources || [];
  } catch (error) {
    console.error("加载数据源列表失败:", error);
  }
}

async function onSourceSelected() {
  const sourceId = formData.value.source_id;
  if (!sourceId) {
    // 如果清空数据源选择，重置分支
    formData.value.source_id = "";
    formData.value.branch = "";
    repoVerified.value = false;
    branchesAndTags.value = { branches: [], tags: [], default_branch: null };
    availableDockerfiles.value = [];
    return;
  }

  const source = gitSources.value.find((s) => s.source_id === sourceId);
  if (source) {
    formData.value.git_url = source.git_url;
    formData.value.source_id = source.source_id;

    // 先尝试从缓存获取
    const cached = getGitCache(source.git_url, sourceId);
    if (cached) {
      branchesAndTags.value = cached;
      repoVerified.value = true;

      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (
        !formData.value.branch ||
        !cached.branches.includes(formData.value.branch)
      ) {
        formData.value.branch =
          cached.default_branch || cached.branches[0] || "";
      }

      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
        loadServices();
      }
      return;
    }

    // 如果数据源有分支信息，使用数据源的分支列表和默认分支
    if (source.branches && source.branches.length > 0) {
      branchesAndTags.value = {
        branches: source.branches || [],
        tags: source.tags || [],
        default_branch: source.default_branch || null,
      };
      repoVerified.value = true;

      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (
        !formData.value.branch ||
        !source.branches.includes(formData.value.branch)
      ) {
        formData.value.branch =
          source.default_branch || source.branches[0] || "";
      }

      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
        loadServices();
      }
    } else if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch;
      // 尝试从缓存获取（如果API数据源没有缓存，尝试从URL缓存获取）
      const urlCached = getGitCache(source.git_url, null);
      if (urlCached) {
        branchesAndTags.value = urlCached;
        repoVerified.value = true;
      }
    }
  }
}

// 监听 Git URL 变化，自动匹配数据源
watch(
  () => formData.value.git_url,
  () => {
    if (!formData.value.git_url) {
      return;
    }

    // 查找匹配的数据源
    const source = gitSources.value.find(
      (s) => s.git_url === formData.value.git_url
    );
    if (source) {
      // 如果还没有设置 source_id，自动设置
      if (!formData.value.source_id) {
        formData.value.source_id = source.source_id;
      }

      // 先尝试从缓存获取
      const cached = getGitCache(source.git_url, source.source_id);
      if (cached) {
        branchesAndTags.value = cached;
        repoVerified.value = true;

        // 如果数据源有默认分支且当前没有选择分支，设置默认分支
        if (
          !formData.value.branch ||
          !cached.branches.includes(formData.value.branch)
        ) {
          formData.value.branch =
            cached.default_branch || cached.branches[0] || "";
        }

        // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
        if (formData.value.use_project_dockerfile && formData.value.branch) {
          scanDockerfiles();
        }
      } else if (source.branches && source.branches.length > 0) {
        // 如果数据源有分支信息，加载分支列表
        branchesAndTags.value = {
          branches: source.branches || [],
          tags: source.tags || [],
          default_branch: source.default_branch || null,
        };
        repoVerified.value = true;

        // 如果数据源有默认分支且当前没有选择分支，设置默认分支
        if (source.default_branch && !formData.value.branch) {
          formData.value.branch = source.default_branch;
        }

        // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
        if (formData.value.use_project_dockerfile && formData.value.branch) {
          scanDockerfiles();
        }
      } else if (source.default_branch && !formData.value.branch) {
        formData.value.branch = source.default_branch;
      }

      // 如果使用项目 Dockerfile 且有分支，重新加载服务（数据源变化不是切换 Dockerfile）
      // 注意：这里不立即调用 loadServices，因为 scanDockerfiles 完成后会自动调用
      // 避免重复触发
    }
  }
);

// 监听分支变化（onBranchChanged 已处理 Dockerfile 扫描）

// 监听 Dockerfile 名称变化，如果使用项目 Dockerfile，重新加载服务
watch(
  () => formData.value.dockerfile_name,
  (newName, oldName) => {
    // 只有当 Dockerfile 名称真正改变且使用项目 Dockerfile 时才重新加载服务
    if (
      newName !== oldName &&
      formData.value.use_project_dockerfile &&
      formData.value.git_url &&
      formData.value.branch &&
      newName && // 确保新名称不为空
      oldName
    ) {
      // 确保是真正的变化（不是初始化）
      // #region agent log (disabled - causes connection errors)
      // fetch(
      //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({
      //       location: "PipelinePanel.vue:1834",
      //       message: "Dockerfile name changed, reloading services",
      //       data: { old: oldName, newValue: newName },
      //       timestamp: Date.now(),
      //       sessionId: "debug-session",
      //       runId: "run1",
      //       hypothesisId: "D",
      //     }),
      //   }
      // ).catch(() => {});
      // #endregion
      // Dockerfile 名称变化是用户主动切换，需要重新识别服务
      loadServices(true);
    }
  }
);

// 监听模态框显示，确保内容同步（只在显示时更新，避免递归）
watch(showBuildConfigJsonModal, (isVisible) => {
  if (isVisible) {
    // 使用 nextTick 确保在模态框完全显示后再更新
    nextTick(() => {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    });
  }
});

// 监听activeTab变化，当切换到build Tab时（新建或编辑模式），更新JSON内容
// 当切换到service Tab时，自动加载服务列表（如果还没有加载）
watch(activeTab, (newTab) => {
  if (newTab === "build") {
    nextTick(() => {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    });
  }
  // 编辑模式下不自动加载服务列表，需要用户手动点击加载按钮
  // 这样可以避免编辑时卡死的问题
  // 移除了切换到 service tab 时的自动加载逻辑
});

// 监听JSON文本变化，实时验证（新建和编辑模式下）
watch(buildConfigJsonText, (newText) => {
  if (activeTab.value !== "build") return;

  buildConfigJsonError.value = "";
  if (!newText || !newText.trim()) {
    buildConfigJsonError.value = "JSON不能为空";
    return;
  }

  try {
    const parsed = JSON.parse(newText);
    // 基本验证：确保是对象
    if (typeof parsed !== "object" || Array.isArray(parsed)) {
      buildConfigJsonError.value = "JSON必须是对象格式";
      return;
    }
  } catch (e) {
    buildConfigJsonError.value = `JSON格式错误: ${e.message}`;
  }
});

// 关闭构建配置JSON模态框
function closeBuildConfigJsonModal() {
  showBuildConfigJsonModal.value = false;
  buildConfigJsonError.value = "";
}

function saveBuildConfigJson() {
  applyBuildConfigJson();
  closeBuildConfigJsonModal();
}

// 重置构建配置JSON（恢复到原始值）
async function resetBuildConfigJson() {
  if (await showConfirm({ message: "确定要重置构建配置JSON吗？未保存的修改将丢失。" })) {
    buildConfigJsonText.value = buildConfigJson.value;
    buildConfigJsonError.value = "";
  }
}

// 应用构建配置JSON到formData（不保存到后端）
function applyBuildConfigJson() {
  if (buildConfigJsonError.value) {
    toastError("请先修复JSON错误");
    return;
  }

  try {
    const config = JSON.parse(buildConfigJsonText.value);

    // 更新formData中的相关字段
    if (config.git_url !== undefined) formData.value.git_url = config.git_url;
    if (config.image_name !== undefined)
      formData.value.image_name = config.image_name;
    if (config.tag !== undefined) formData.value.tag = config.tag;
    if (config.branch !== undefined && config.branch !== null)
      formData.value.branch = config.branch;
    if (config.project_type !== undefined)
      formData.value.project_type = config.project_type;
    if (config.template !== undefined)
      formData.value.template = config.template;
    if (config.template_params !== undefined)
      formData.value.template_params = config.template_params;
    if (config.should_push !== undefined)
      formData.value.push = config.should_push;
    if (config.sub_path !== undefined && config.sub_path !== null)
      formData.value.sub_path = config.sub_path;
    if (config.use_project_dockerfile !== undefined)
      formData.value.use_project_dockerfile = config.use_project_dockerfile;
    if (config.dockerfile_name !== undefined)
      formData.value.dockerfile_name = config.dockerfile_name;
    if (
      config.dockerfile_content !== undefined &&
      config.dockerfile_content !== null
    ) {
      formData.value.dockerfile_content = config.dockerfile_content;
      dockerfileContentText.value = config.dockerfile_content;
    }
    if (config.source_id !== undefined && config.source_id !== null)
      formData.value.source_id = config.source_id;
    if (config.selected_services !== undefined)
      formData.value.selected_services = config.selected_services || [];
    if (config.service_push_config !== undefined)
      formData.value.service_push_config = config.service_push_config || {};
    if (config.service_template_params !== undefined)
      formData.value.service_template_params =
        config.service_template_params || {};
    if (config.push_mode !== undefined)
      formData.value.push_mode = config.push_mode || "multi";
    if (config.resource_package_configs !== undefined) {
      // 直接使用resource_package_configs配置（包含package_id和target_path）
      formData.value.resource_package_configs =
        config.resource_package_configs || [];
    } else if (config.resource_package_ids !== undefined) {
      // 兼容旧格式：如果只有resource_package_ids数组，转换为resource_package_configs格式
      formData.value.resource_package_configs = (
        config.resource_package_ids || []
      ).map((pkgId) => ({
        package_id: pkgId,
        target_path: "", // 旧格式没有target_path，留空
      }));
    }

    // 如果push_mode是single，设置selected_service
    if (
      config.push_mode === "single" &&
      config.selected_services &&
      config.selected_services.length > 0
    ) {
      formData.value.selected_service = config.selected_services[0];
    }

    // 更新JSON文本以反映formData的变化
    buildConfigJsonText.value = buildConfigJson.value;
    buildConfigJsonError.value = "";

    // 不显示alert，静默应用，用户需要点击外部保存按钮才能真正保存
  } catch (e) {
    toastError(`应用失败: ${e.message}`);
  }
}

// 从仓库加载Dockerfile内容
async function loadDockerfileFromRepo() {
  if (!formData.value.source_id) {
    toastError("请先选择数据源");
    return;
  }

  if (!formData.value.dockerfile_name) {
    toastError("请先选择或输入Dockerfile文件名");
    return;
  }

  if (!formData.value.branch) {
    toastError("请先选择分支");
    return;
  }

  loadingDockerfile.value = true;
  try {
    const response = await axios.get(
      `/api/git-sources/${
        formData.value.source_id
      }/dockerfiles/${encodeURIComponent(formData.value.dockerfile_name)}`
    );

    if (response.data && response.data.content) {
      dockerfileContentText.value = response.data.content;
      toastInfo("Dockerfile已从仓库加载");
    } else {
      toastError("未找到Dockerfile内容");
    }
  } catch (error) {
    console.error("加载Dockerfile失败:", error);
    toastApiError(error, "加载Dockerfile失败");
  } finally {
    loadingDockerfile.value = false;
  }
}

// 应用Dockerfile内容到formData
function applyDockerfileContent() {
  if (!dockerfileContentText.value.trim()) {
    toastError("Dockerfile内容不能为空");
    return;
  }

  formData.value.dockerfile_content = dockerfileContentText.value;
  toastInfo("Dockerfile内容已应用");
}

// 监听项目类型变化，如果当前选择的模板不再匹配新的项目类型，则清除模板选择
watch(
  () => formData.value.project_type,
  (newType, oldType) => {
    if (newType !== oldType && formData.value.template) {
      // 检查当前选择的模板是否匹配新的项目类型
      const currentTemplate = templates.value.find(
        (t) => t.name === formData.value.template
      );
      if (!currentTemplate || currentTemplate.project_type !== newType) {
        // 模板不匹配新的项目类型，清除模板选择并重新加载服务（项目类型变化不是切换 Dockerfile）
        formData.value.template = "";
        if (
          formData.value.use_project_dockerfile &&
          formData.value.git_url &&
          formData.value.branch
        ) {
          loadServices(false);
        }
      }
    }
  }
);

async function fetchPipelineNames() {
  try {
    const res = await axios.get("/api/pipelines");
    pipelines.value = res.data.pipelines || [];
  } catch (error) {
    console.error("加载流水线列表失败:", error);
    pipelines.value = [];
  }
}

async function loadTemplates() {
  try {
    const res = await axios.get("/api/list-templates");
    templates.value = res.data || [];
  } catch (error) {
    console.error("加载模板列表失败:", error);
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
  } catch (error) {
    console.error("加载仓库列表失败:", error);
  }
}

async function loadDeployTasks() {
  try {
    const res = await axios.get("/api/deploy-tasks");
    deployTaskList.value = res.data.tasks || [];
  } catch (error) {
    console.error("加载部署任务列表失败:", error);
  }
}

function getDeployWebhookUrl(token) {
  const baseUrl = window.location.origin
    .replace(":3000", ":8000")
    .replace(":5173", ":8000");
  return `${baseUrl}/api/webhook/deploy/${token}`;
}

function onDeployTaskSelected(webhook, configId) {
  const task = deployTaskList.value.find((t) => t.task_id === configId);
  if (!task) return;
  let token = task.webhook_token;
  if (!token) {
    // 部署配置没有 webhook_token，自动生成一个
    token = crypto.randomUUID();
    task.webhook_token = token;
    // 异步回写到后端，确保下次也能使用
    axios.put(`/api/deploy-tasks/${configId}`, {
      config_content: task.config_content,
      webhook_token: token,
    }).catch(() => {});
  }
  webhook.url = getDeployWebhookUrl(token);
  webhook.method = "POST";
}

function initCreateForm() {
  activeTab.value = "basic";
  editingPipeline.value = null;
  formData.value = {
    name: "",
    description: "",
    git_url: "",
    branch: "",
    sub_path: "",
    project_type: "jar",
    template: "",
    image_name: "",
    tag: "latest",
    push: false,
    webhook_secret: "",
    webhook_branch_strategy: "use_push",
    webhook_allowed_branches: [],
    branch_tag_mapping: [],
    post_build_webhooks: [],
    enabled: true,
    trigger_schedule: false,
    cron_expression: "",
    dockerfile_name: "Dockerfile",
    dockerfile_content: "", // Dockerfile内容
    source_id: "",
    use_project_dockerfile: true,
    push_mode: "multi",
    selected_service: "",
    selected_services: [],
    service_push_config: {},
    service_template_params: {},
    resource_package_configs: [],
  };
  services.value = [];
  loadingServices.value = false;
  servicesError.value = "";
  // 初始化Dockerfile编辑器内容
  dockerfileContentText.value = "";
  wizardForceSingleMode.value = false;
  wizardServiceAnalysisDone.value = false;
// 初始化JSON编辑器内容（新建模式）
  nextTick(() => {
    if (activeTab.value === "build") {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    }
  });
}

function applyPipelineToForm(pipeline) {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1918",
  //     message: "editPipeline started",
  //     data: {
  //       pipeline_id: pipeline.id,
  //       pipeline_name: pipeline.name,
  //       dockerfile_name: pipeline.dockerfile_name,
  //       template: pipeline.template,
  //       use_project_dockerfile: pipeline.use_project_dockerfile,
  //       project_type: pipeline.project_type,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion

  // 先重置Tab，确保显示基本信息Tab，而不是自动跳转到build Tab
  activeTab.value = "basic";
  // 然后设置编辑模式
  editingPipeline.value = pipeline;

  // 查找对应的数据源
  const source = gitSources.value.find(
    (s) => s.source_id === pipeline.source_id || s.git_url === pipeline.git_url
  );

  // 保存原始配置，避免被扫描覆盖
  const savedDockerfileName = pipeline.dockerfile_name || "Dockerfile";
  const savedTemplate = pipeline.template || "";
  // 优先使用后端返回的 use_project_dockerfile，如果没有则根据 template 推断
  const savedUseProjectDockerfile =
    pipeline.use_project_dockerfile !== undefined
      ? pipeline.use_project_dockerfile
      : !pipeline.template; // 有模板则 false，无模板则 true

  const normalizedPipelineSpc = normalizeServicePushConfig(
    pipeline.service_push_config || {}
  );

  formData.value = {
    name: pipeline.name,
    description: pipeline.description || "",
    git_url: pipeline.git_url,
    branch: pipeline.branch || "",
    sub_path: pipeline.sub_path || "",
    project_type: pipeline.project_type || "jar",
    template: savedTemplate,
    image_name: pipeline.image_name || "",
    tag: pipeline.tag || "latest",
    push:
      pipeline.push_mode === "multi"
        ? anyServicePushEnabled(normalizedPipelineSpc) || !!pipeline.push
        : pipeline.push || false,
    webhook_token: pipeline.webhook_token || "",
    webhook_secret: pipeline.webhook_secret || "",
    webhook_branch_strategy: getWebhookBranchStrategy(pipeline),
    webhook_allowed_branches: pipeline.webhook_allowed_branches
      ? [...pipeline.webhook_allowed_branches]
      : [],
    branch_tag_mapping: pipeline.branch_tag_mapping
      ? Object.entries(pipeline.branch_tag_mapping).map(([branch, tag]) => ({
          branch,
          tag: Array.isArray(tag) ? tag.join(",") : tag, // 如果是数组，转换为逗号分隔的字符串
        }))
      : [],
    post_build_webhooks: (() => {
      if (
        !pipeline.post_build_webhooks ||
        pipeline.post_build_webhooks.length === 0
      ) {
        return [];
      }
      // 将headers对象转换为headers_json字符串
      return pipeline.post_build_webhooks.map((webhook) => ({
        url: webhook.url || "",
        method: webhook.method || "POST",
        headers: webhook.headers || {},
        headers_json: JSON.stringify(webhook.headers || {}, null, 2),
        body_template: webhook.body_template || "{}",
        enabled: webhook.enabled !== false,
        branch_strategy: webhook.branch_strategy || "all",
        branches: webhook.branches || [],
      }));
    })(),
    enabled: pipeline.enabled !== false,
    trigger_schedule: !!pipeline.cron_expression, // 如果有cron表达式则启用
    cron_expression: pipeline.cron_expression || "",
    dockerfile_name: savedDockerfileName,
    use_project_dockerfile: savedUseProjectDockerfile,
    dockerfile_content: pipeline.dockerfile_content || "", // Dockerfile内容
    source_id: pipeline.source_id || (source ? source.source_id : ""),
    push_mode: pipeline.push_mode || "multi",
    selected_service:
      pipeline.selected_services && pipeline.selected_services.length === 1
        ? pipeline.selected_services[0]
        : "",
    selected_services: pipeline.selected_services || [],
    service_push_config: normalizedPipelineSpc,
    service_template_params: pipeline.service_template_params || {},
    resource_package_configs: pipeline.resource_package_configs || [],
  };

  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1956",
  //     message: "formData initialized",
  //     data: {
  //       dockerfile_name: formData.value.dockerfile_name,
  //       template: formData.value.template,
  //       use_project_dockerfile: formData.value.use_project_dockerfile,
  //       branch: formData.value.branch,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion

  // 如果数据源有分支信息，加载分支列表
  if (source && source.branches && source.branches.length > 0) {
    branchesAndTags.value = {
      branches: source.branches || [],
      tags: source.tags || [],
      default_branch: source.default_branch || null,
    };
    repoVerified.value = true;

    // 如果当前分支为空或不在分支列表中，使用默认分支
    if (
      !formData.value.branch ||
      !source.branches.includes(formData.value.branch)
    ) {
      formData.value.branch =
        source.default_branch ||
        source.branches[0] ||
        formData.value.branch ||
        "";
    }

    // 编辑模式下：不自动扫描 Dockerfile 和加载服务列表
    // 用户需要手动在服务配置 tab 中点击加载按钮
    // 这样可以避免编辑时卡死的问题
  }

  // 编辑模式下：不加载服务列表，避免卡死问题
  // 服务管理功能已移除

  // 初始化Dockerfile编辑器内容
  dockerfileContentText.value = formData.value.dockerfile_content || "";
// #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1980",
  //     message: "editPipeline completed",
  //     data: {
  //       final_dockerfile_name: formData.value.dockerfile_name,
  //       final_template: formData.value.template,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion
}

// 添加分支标签映射
function addBranchTagMapping() {
  if (!formData.value.branch_tag_mapping) {
    formData.value.branch_tag_mapping = [];
  }
  formData.value.branch_tag_mapping.push({ branch: "", tag: "" });
}

// 删除分支标签映射
function addPostBuildWebhook() {
  if (!formData.value.post_build_webhooks) {
    formData.value.post_build_webhooks = [];
  }
  formData.value.post_build_webhooks.push({
    url: "",
    method: "POST",
    headers: {},
    headers_json: "{}",
    body_template:
      '{"task_id": "{task_id}", "image": "{image}", "tag": "{tag}", "status": "{status}"}',
    enabled: true,
    branch_strategy: "all",
    branches: [],
  });
}

function removePostBuildWebhook(index) {
  if (formData.value.post_build_webhooks) {
    formData.value.post_build_webhooks.splice(index, 1);
  }
}

function removeBranchTagMapping(index) {
  formData.value.branch_tag_mapping.splice(index, 1);
}

// 全选/取消全选分支
function toggleAllBranches(event) {
  if (event.target.checked) {
    // 全选：添加所有分支
    formData.value.webhook_allowed_branches = [
      ...(branchesAndTags.value.branches || []),
    ];
  } else {
    // 取消全选：清空选择
    formData.value.webhook_allowed_branches = [];
  }
}

// 计算是否全选分支
const isAllBranchesSelected = computed(() => {
  const branches = branchesAndTags.value.branches || [];
  if (branches.length === 0) return false;
  const selected = formData.value.webhook_allowed_branches || [];
  return (
    branches.length === selected.length &&
    branches.every((branch) => selected.includes(branch))
  );
});

// 根据旧配置获取新的分支策略
function getWebhookBranchStrategy(pipeline) {
  // 如果流水线有webhook_allowed_branches字段且不为空，说明是选择分支触发策略
  if (
    pipeline.webhook_allowed_branches &&
    Array.isArray(pipeline.webhook_allowed_branches) &&
    pipeline.webhook_allowed_branches.length > 0
  ) {
    return "select_branches";
  }

  const webhook_branch_filter = pipeline.webhook_branch_filter || false;
  const webhook_use_push_branch = pipeline.webhook_use_push_branch !== false; // 默认为true

  if (webhook_branch_filter) {
    return "filter_match";
  } else if (webhook_use_push_branch) {
    return "use_push";
  } else {
    return "use_configured";
  }
}

async function savePipeline() {
  // 防止重复提交
  if (saving.value) {
    return;
  }

  saving.value = true;
  try {
    // 将分支标签映射从数组转换为对象
    // 支持一个分支对应多个标签（用逗号分隔，转换为数组）
    const branch_tag_mapping = {};
    if (
      formData.value.branch_tag_mapping &&
      formData.value.branch_tag_mapping.length > 0
    ) {
      formData.value.branch_tag_mapping.forEach((mapping) => {
        if (mapping.branch && mapping.tag) {
          // 如果标签包含逗号，转换为数组；否则保持字符串
          const tagValue = mapping.tag.trim().replace(/，/g, ',');
          if (tagValue.includes(",")) {
            // 多个标签，转换为数组
            branch_tag_mapping[mapping.branch] = tagValue
              .split(",")
              .map((t) => t.trim())
              .filter((t) => t);
          } else {
            // 单个标签，保持字符串（向后兼容）
            branch_tag_mapping[mapping.branch] = tagValue;
          }
        }
      });
    }

    // 根据分支策略设置webhook_branch_filter和webhook_use_push_branch
    let webhook_branch_filter = false;
    let webhook_use_push_branch = true;

    if (formData.value.webhook_branch_strategy === "filter_match") {
      webhook_branch_filter = true;
      webhook_use_push_branch = true;
    } else if (formData.value.webhook_branch_strategy === "use_push") {
      webhook_branch_filter = false;
      webhook_use_push_branch = true;
    } else if (formData.value.webhook_branch_strategy === "select_branches") {
      // 选择分支触发策略：验证是否选择了分支
      if (
        !formData.value.webhook_allowed_branches ||
        formData.value.webhook_allowed_branches.length === 0
      ) {
        toastError("请至少选择一个允许触发的分支");
        saving.value = false;
        return false;
      }
      webhook_branch_filter = true;
      webhook_use_push_branch = true;
    } else {
      // use_configured
      webhook_branch_filter = false;
      webhook_use_push_branch = false;
    }

    // 确保 template 和 use_project_dockerfile 的一致性
    // 如果使用项目 Dockerfile，则清空 template
    // 如果使用模板，则确保 use_project_dockerfile 为 false
    if (formData.value.use_project_dockerfile) {
      formData.value.template = "";
    } else {
      // 使用模板时，确保选择了模板
      if (!formData.value.template) {
        toastError("请选择 Dockerfile 模板");
        saving.value = false;
        return false;
      }
    }

    // 准备提交数据
    const payload = {
      ...formData.value,
      // 确保 use_project_dockerfile 和 template 的一致性
      use_project_dockerfile: formData.value.use_project_dockerfile,
      // 如果使用项目 Dockerfile，template 应该为空字符串
      // 如果使用模板，template 必须有值（不能为空）
      template: formData.value.use_project_dockerfile
        ? ""
        : formData.value.template || "",
      // 将分支策略转换为旧格式（向后兼容）
      webhook_branch_filter: webhook_branch_filter,
      webhook_use_push_branch: webhook_use_push_branch,
      // 将分支标签映射转换为对象格式
      branch_tag_mapping:
        Object.keys(branch_tag_mapping).length > 0 ? branch_tag_mapping : null,
      // 如果未启用定时触发，则cron_expression为null
      cron_expression: formData.value.trigger_schedule
        ? formData.value.cron_expression
        : null,
      // 传递数据源ID
      source_id: formData.value.source_id || null,
      // 多服务配置：根据推送模式处理
      // 编辑模式下，如果formData中没有多阶段配置，从原始流水线数据中保留
      selected_services: (() => {
        const fromForm =
          formData.value.push_mode === "single" &&
          formData.value.selected_service
            ? [formData.value.selected_service]
            : formData.value.selected_services &&
              formData.value.selected_services.length > 0
            ? formData.value.selected_services
            : null;

        // 如果formData中有配置，使用formData的配置
        if (fromForm && fromForm.length > 0) {
          return fromForm;
        }

        // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
        if (
          editingPipeline.value &&
          editingPipeline.value.selected_services &&
          editingPipeline.value.selected_services.length > 0
        ) {
          return editingPipeline.value.selected_services;
        }

        return null;
      })(),
      // 规范化服务推送配置（确保所有配置都是对象格式，包含 push、imageName 和 tag 字段）
      service_push_config: (() => {
        // 只处理已选择的服务
        const selectedServices =
          formData.value.push_mode === "single" &&
          formData.value.selected_service
            ? [formData.value.selected_service]
            : formData.value.selected_services || [];

        // 如果formData中没有服务，但编辑模式下原始流水线有服务，使用原始流水线的服务
        if (
          selectedServices.length === 0 &&
          editingPipeline.value &&
          editingPipeline.value.selected_services &&
          editingPipeline.value.selected_services.length > 0
        ) {
          selectedServices.push(...editingPipeline.value.selected_services);
        }

        if (selectedServices.length === 0) {
          // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
          if (
            editingPipeline.value &&
            editingPipeline.value.service_push_config &&
            Object.keys(editingPipeline.value.service_push_config).length > 0
          ) {
            return editingPipeline.value.service_push_config;
          }
          return null;
        }

        const config = formData.value.service_push_config || {};
        // 编辑模式下，如果formData中没有配置，尝试从原始流水线数据中获取
        if (
          Object.keys(config).length === 0 &&
          editingPipeline.value &&
          editingPipeline.value.service_push_config
        ) {
          Object.assign(config, editingPipeline.value.service_push_config);
        }

        const normalized = {};

        selectedServices.forEach((serviceName) => {
          const value = config[serviceName];
          if (typeof value === "boolean") {
            // 旧格式：只有push字段
            normalized[serviceName] = {
              push: value,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || "latest",
            };
          } else if (value && typeof value === "object") {
            // 获取最终镜像名（自定义或默认）
            const customImageName = value.imageName && value.imageName.trim();
            const finalImageName =
              customImageName || getServiceDefaultImageName(serviceName);
            // 获取最终标签（自定义或全局）
            const finalTag =
              (value.tag && value.tag.trim()) || formData.value.tag || "latest";

            normalized[serviceName] = {
              push: value.push !== undefined ? value.push : false,
              imageName: finalImageName,
              tag: finalTag,
            };
          } else {
            // 新服务，使用默认值
            normalized[serviceName] = {
              push: false,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || "latest",
            };
          }
        });

        return Object.keys(normalized).length > 0 ? normalized : null;
      })(),
      service_template_params: (() => {
        const fromForm =
          formData.value.service_template_params &&
          Object.keys(formData.value.service_template_params).length > 0
            ? formData.value.service_template_params
            : null;

        // 如果formData中有配置，使用formData的配置
        if (fromForm) {
          return fromForm;
        }

        // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
        if (
          editingPipeline.value &&
          editingPipeline.value.service_template_params &&
          Object.keys(editingPipeline.value.service_template_params).length > 0
        ) {
          return editingPipeline.value.service_template_params;
        }

        return null;
      })(),
      // 确保push_mode被保留（编辑模式下，如果formData中没有，从原始流水线数据中保留）
      push_mode:
        formData.value.push_mode ||
        (editingPipeline.value && editingPipeline.value.push_mode) ||
        "multi",
      resource_package_configs:
        formData.value.resource_package_configs &&
        formData.value.resource_package_configs.length > 0
          ? formData.value.resource_package_configs
          : null,
      // Webhook 配置：如果为空字符串，传递 null 让后端自动生成
      webhook_token:
        formData.value.webhook_token && formData.value.webhook_token.trim()
          ? formData.value.webhook_token.trim()
          : null,
      webhook_secret:
        formData.value.webhook_secret && formData.value.webhook_secret.trim()
          ? formData.value.webhook_secret.trim()
          : null,
      // 选择分支触发：只在策略为select_branches时传递
      webhook_allowed_branches:
        formData.value.webhook_branch_strategy === "select_branches"
          ? formData.value.webhook_allowed_branches || []
          : null,
      // 构建后webhook配置
      post_build_webhooks: (() => {
        if (
          !formData.value.post_build_webhooks ||
          formData.value.post_build_webhooks.length === 0
        ) {
          return null;
        }
        // 处理每个webhook，将headers_json转换为headers对象
        return formData.value.post_build_webhooks.map((webhook) => {
          const processed = {
            url: webhook.url,
            method: webhook.method || "POST",
            body_template: webhook.body_template || "{}",
            enabled: webhook.enabled !== false,
            branch_strategy: webhook.branch_strategy || "all",
            branches: webhook.branches || [],
          };
          // 解析headers_json为对象
          if (webhook.headers_json) {
            try {
              processed.headers = JSON.parse(webhook.headers_json);
            } catch (e) {
              console.warn("解析webhook headers失败，使用空对象:", e);
              processed.headers = {};
            }
          } else {
            processed.headers = webhook.headers || {};
          }
          return processed;
        });
      })(),
    };
    // 多阶段模式：顶层 push 与分服务推送开关同步（否则仅保存 service_push_config 时 DB 仍为 false）
    if (payload.push_mode === "multi" && payload.service_push_config) {
      payload.push = anyServicePushEnabled(payload.service_push_config);
    }
    // 移除webhook_branch_strategy，因为后端不需要这个字段
    delete payload.webhook_branch_strategy;
    delete payload.selected_service; // 移除单服务字段，后端不需要
    delete payload.trigger_schedule; // 移除前端字段

    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      toastError("请填写 Cron 表达式");
      saving.value = false;
      return;
    }

    // 验证：如果使用模板，必须选择了模板
    if (!payload.use_project_dockerfile && !payload.template) {
      toastError("使用模板时必须选择 Dockerfile 模板");
      saving.value = false;
      return;
    }

    // 验证流水线名字不能重复
    const pipelineName = payload.name && payload.name.trim();
    if (!pipelineName) {
      toastError("请输入流水线名称");
      saving.value = false;
      return;
    }

    // 调试信息
    console.log("保存流水线参数:", {
      use_project_dockerfile: payload.use_project_dockerfile,
      template: payload.template,
      project_type: payload.project_type,
    });

    if (editingPipeline.value) {
      // 更新
      await axios.put(
        `/api/pipelines/${editingPipeline.value.pipeline_id}`,
        payload
      );
      toastSuccess("流水线更新成功");
      if (onSaved) onSaved(editingPipeline.value.pipeline_id);
      return editingPipeline.value.pipeline_id;
    } else {
      // 创建
      const res = await axios.post("/api/pipelines", payload);
      const newId = res.data?.pipeline_id;
      toastSuccess("流水线创建成功");
      if (onSaved) onSaved(newId);
      return newId || true;
    }
  } catch (error) {
    console.error("保存流水线失败:", error);
    toastApiError(error, "保存流水线失败");
  } finally {
    saving.value = false;
  }
}

/** 向导创建：仅提交基础字段，跳过完整配置校验 */
async function createPipelineMinimal() {
  if (saving.value) {
    return null;
  }

  const pipelineName = formData.value.name?.trim();
  if (!pipelineName) {
    toastError("请输入流水线名称");
    return null;
  }

  const hasGit =
    Boolean(formData.value.source_id) ||
    Boolean(formData.value.git_url?.trim());
  if (!hasGit) {
    toastError("请选择数据源或填写 Git 仓库地址");
    return null;
  }

  if (!formData.value.push_mode) {
    toastError("请选择单服务或多服务模式");
    return null;
  }

  saving.value = true;
  try {
    const payload = {
      name: pipelineName,
      description: formData.value.description || "",
      git_url: formData.value.git_url?.trim() || null,
      branch: formData.value.branch || null,
      source_id: formData.value.source_id || null,
      project_type: formData.value.project_type || "jar",
      sub_path: formData.value.sub_path || null,
      push_mode: formData.value.push_mode,
      use_project_dockerfile: true,
      dockerfile_name: formData.value.dockerfile_name || "Dockerfile",
      template: "",
      tag: "latest",
      push: false,
      enabled: true,
      webhook_branch_filter: false,
      webhook_use_push_branch: true,
      cron_expression: null,
      branch_tag_mapping: null,
      selected_services:
        formData.value.push_mode === "multi" &&
        formData.value.selected_services?.length > 0
          ? formData.value.selected_services
          : null,
      service_push_config:
        formData.value.push_mode === "multi" &&
        formData.value.service_push_config &&
        Object.keys(formData.value.service_push_config).length > 0
          ? formData.value.service_push_config
          : null,
      service_template_params: null,
      resource_package_configs: null,
      post_build_webhooks: null,
      webhook_token: null,
      webhook_secret: null,
      webhook_allowed_branches: null,
    };

    const res = await axios.post("/api/pipelines", payload);
    const newId = res.data?.pipeline_id;
    if (onSaved && newId) {
      onSaved(newId);
    }
    return newId || null;
  } catch (error) {
    console.error("创建流水线失败:", error);
    toastApiError(error, "创建流水线失败");
    return null;
  } finally {
    saving.value = false;
  }
}

function resetFormState() {
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
  wizardForceSingleMode.value = false;
  wizardServiceAnalysisDone.value = false;
}

/** 根据 Dockerfile/模板解析结果设置单服务或多服务推送模式 */
function applyPushModeFromDockerfileAnalysis(forceSingle = false) {
  const useSingle =
    forceSingle ||
    wizardForceSingleMode.value ||
    services.value.length === 0;

  if (useSingle) {
    formData.value.push_mode = "single";
    formData.value.selected_services = [];
    formData.value.selected_service = "";
  } else {
    formData.value.push_mode = "multi";
    formData.value.selected_service = "";
    formData.value.selected_services = services.value.map((s) => s.name);
    initializeServiceConfigs();
  }
}

function switchWizardToSingleAppMode() {
  wizardForceSingleMode.value = true;
  applyPushModeFromDockerfileAnalysis(true);
}

function switchWizardToMultiAppMode() {
  wizardForceSingleMode.value = false;
  applyPushModeFromDockerfileAnalysis(false);
}

/** 向导内用户手动切换推送模式（可覆盖 Dockerfile 自动识别结果） */
function setWizardPushMode(mode) {
  if (mode === "single") {
    switchWizardToSingleAppMode();
    return;
  }
  wizardForceSingleMode.value = false;
  formData.value.push_mode = "multi";
  formData.value.selected_service = "";
  if (services.value.length > 0) {
    formData.value.selected_services = services.value.map((s) => s.name);
    initializeServiceConfigs();
  } else {
    formData.value.selected_services = [];
    formData.value.service_push_config = {};
  }
}

/** 创建向导进入「服务模式」步骤前：扫描 Dockerfile 并解析服务 */
async function analyzeDockerfileForWizard() {
  wizardServiceAnalysisDone.value = false;
  wizardForceSingleMode.value = false;
  servicesError.value = "";

  if (!formData.value.git_url?.trim() && !formData.value.source_id) {
    servicesError.value = "请先选择数据源或填写 Git 仓库地址";
    return false;
  }

  if (!formData.value.branch?.trim()) {
    const defaultBranch = branchesAndTags.value.default_branch;
    if (defaultBranch) {
      formData.value.branch = defaultBranch;
    } else if (formData.value.source_id || formData.value.git_url) {
      await refreshBranches(false);
    }
  }

  formData.value.use_project_dockerfile = true;

  try {
    if (formData.value.git_url && (formData.value.branch || branchesAndTags.value.default_branch)) {
      await scanDockerfiles(false, false);
    }
    await loadServices(true);
    applyPushModeFromDockerfileAnalysis(false);
    wizardServiceAnalysisDone.value = true;
    return true;
  } catch (error) {
    console.error("向导分析 Dockerfile 失败:", error);
    services.value = [];
    applyPushModeFromDockerfileAnalysis(false);
    wizardServiceAnalysisDone.value = true;
    return false;
  }
}

async function refreshBranches(forceRefresh = true) {
  const sourceId = formData.value.source_id;
  if (!sourceId) {
    if (!formData.value.git_url) {
      toastError("请先选择数据源或填写 Git 仓库地址");
      return;
    }
    // 如果没有数据源但有 Git URL，使用 verify-git-repo API
    try {
      refreshingBranches.value = true;

      // 如果强制刷新，先清除缓存
      if (forceRefresh) {
        clearGitCache(formData.value.git_url, null);
      }

      // 使用缓存机制获取Git信息
      const data = await getGitInfoWithCache(
        async () => {
          const response = await axios.post("/api/verify-git-repo", {
            git_url: formData.value.git_url,
            source_id: null,
          });
          return response.data;
        },
        formData.value.git_url,
        null,
        forceRefresh
      );

      if (data && data.branches) {
        branchesAndTags.value = {
          branches: data.branches || [],
          tags: data.tags || [],
          default_branch: data.default_branch || null,
        };
        repoVerified.value = true;

        // 如果当前选择的分支不在新列表中，重置为默认分支
        const currentBranch = formData.value.branch;
        if (
          currentBranch &&
          !branchesAndTags.value.branches.includes(currentBranch) &&
          !branchesAndTags.value.tags.includes(currentBranch)
        ) {
          formData.value.branch = branchesAndTags.value.default_branch || "";
        }
      }
    } catch (error) {
      console.error("刷新分支列表失败:", error);
      toastApiError(error, "刷新分支列表失败，请稍后重试");
    } finally {
      refreshingBranches.value = false;
    }
    return;
  }

  const source = gitSources.value.find((s) => s.source_id === sourceId);
  if (!source) {
    return;
  }

  refreshingBranches.value = true;
  try {
    // 如果强制刷新，先清除缓存
    if (forceRefresh) {
      clearGitCache(source.git_url, sourceId);
    }

    // 使用缓存机制获取Git信息
    const data = await getGitInfoWithCache(
      async () => {
        const response = await axios.post("/api/verify-git-repo", {
          git_url: source.git_url,
          source_id: sourceId,
        });
        return response.data;
      },
      source.git_url,
      sourceId,
      forceRefresh
    );

    if (data && data.branches) {
      // 更新分支和标签列表
      branchesAndTags.value = {
        branches: data.branches || [],
        tags: data.tags || [],
        default_branch: data.default_branch || null,
      };
      repoVerified.value = true;

      // 如果当前选择的分支不在新列表中，重置为默认分支
      const currentBranch = formData.value.branch;
      if (
        currentBranch &&
        !branchesAndTags.value.branches.includes(currentBranch) &&
        !branchesAndTags.value.tags.includes(currentBranch)
      ) {
        formData.value.branch = branchesAndTags.value.default_branch || "";
      }

      // 如果使用项目 Dockerfile，重新扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
      }
    }
  } catch (error) {
    console.error("刷新分支列表失败:", error);
    toastApiError(error, "刷新分支列表失败，请稍后重试");
  } finally {
    refreshingBranches.value = false;
  }
}

// 扫描项目中的 Dockerfile
async function scanDockerfiles(
  keepCurrentSelection = true,
  forceRefresh = false
) {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:2316",
  //     message: "scanDockerfiles started",
  //     data: {
  //       source_id: formData.value.source_id,
  //       git_url: formData.value.git_url,
  //       dockerfile_name: formData.value.dockerfile_name,
  //       branch: formData.value.branch,
  //       keep_current_selection: keepCurrentSelection,
  //       editing: !!editingPipeline.value,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "A",
  //   }),
  // }).catch(() => {});
  // #endregion
  const sourceId = formData.value.source_id;
  if (!sourceId && !formData.value.git_url) {
    dockerfilesError.value = "请先选择数据源或填写 Git 仓库地址";
    return;
  }

  // 保存当前的 dockerfile_name，避免被覆盖（编辑模式下必须保持）
  const savedDockerfileName = formData.value.dockerfile_name;
  // 判断是否是编辑模式（正在编辑已有流水线）
  const isEditing = !!editingPipeline.value || keepCurrentSelection;
  // 保存当前已扫描的列表，以便在扫描失败时恢复
  const previousDockerfiles = [...availableDockerfiles.value];

  scanningDockerfiles.value = true;
  dockerfilesError.value = "";
  // 注意：不要立即清空 availableDockerfiles，这样下拉框可以继续显示已保存的值
  // 只有在扫描成功后才更新列表

  try {
    // 获取 Git URL 和分支
    let gitUrl = formData.value.git_url;
    if (sourceId) {
      const source = gitSources.value.find((s) => s.source_id === sourceId);
      if (source) {
        gitUrl = source.git_url;
      }
    }

    if (!gitUrl) {
      dockerfilesError.value = "无法获取 Git 仓库地址";
      return;
    }

    const branch =
      formData.value.branch || branchesAndTags.value.default_branch || "main";

    if (!branch) {
      dockerfilesError.value = "请先选择分支";
      return;
    }

    // 使用缓存机制获取 Dockerfile 列表
    const dockerfilePaths = await getDockerfilesWithCache(
      async () => {
        // 调用 API 扫描 Dockerfile
        const response = await axios.post("/api/git-sources/scan-dockerfiles", {
          git_url: gitUrl,
          branch: branch,
          source_id: sourceId || null,
        });
        return response;
      },
      gitUrl,
      branch,
      sourceId || null,
      forceRefresh // 根据参数决定是否强制刷新
    );

    if (dockerfilePaths && dockerfilePaths.length > 0) {
      // 保存完整路径信息（包含路径和文件名）
      const dockerfileList = dockerfilePaths.map((path) => {
        const parts = path.split("/");
        return {
          path: path, // 完整路径，如 "frontend/Dockerfile"
          name: parts[parts.length - 1], // 文件名，如 "Dockerfile"
        };
      });

      // 按路径排序
      dockerfileList.sort((a, b) => {
        // 根目录的 Dockerfile 优先
        if (a.path === "Dockerfile") return -1;
        if (b.path === "Dockerfile") return 1;
        return a.path.localeCompare(b.path);
      });

      // 只有在成功扫描到结果时才更新列表
      availableDockerfiles.value = dockerfileList;
    } else {
      // 如果 API 返回成功但没有 dockerfiles，保持原列表（如果有）或设为空数组
      // 这样可以保留之前扫描的结果，或者如果是首次扫描则设为空
      if (availableDockerfiles.value.length === 0) {
        // 如果是首次扫描且没有结果，设为空数组
        availableDockerfiles.value = [];
      }
      // 否则保持原列表不变
    }

    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2402",
    //     message: "Dockerfiles scanned",
    //     data: {
    //       count: availableDockerfiles.value.length,
    //       saved_dockerfile_name: savedDockerfileName,
    //       available_paths: availableDockerfiles.value.map((df) => df.path),
    //       is_editing: isEditing,
    //       keep_current_selection: keepCurrentSelection,
    //     },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion

    // 在编辑模式下，始终保持原有的 dockerfile_name，不进行任何自动选择
    // 在新建模式下，只有在当前没有选择时才自动设置
    if (keepCurrentSelection && savedDockerfileName) {
      // 编辑模式或有已保存的选择：始终保持原选择（即使不在新扫描的列表中，下拉框也会显示它）
      formData.value.dockerfile_name = savedDockerfileName;
      const currentInList = availableDockerfiles.value.some(
        (df) => df.path === savedDockerfileName
      );
      // #region agent log (disabled - causes connection errors)
      // fetch(
      //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({
      //       location: "PipelinePanel.vue:2412",
      //       message:
      //         "Dockerfile name preserved (editing mode or has saved selection)",
      //       data: {
      //         dockerfile_name: savedDockerfileName,
      //         in_list: currentInList,
      //         is_editing: isEditing,
      //       },
      //       timestamp: Date.now(),
      //       sessionId: "debug-session",
      //       runId: "run1",
      //       hypothesisId: "A",
      //     }),
      //   }
      // ).catch(() => {});
      // #endregion
    } else if (availableDockerfiles.value.length > 0) {
      // 新建模式且没有保存的选择：自动选择第一个
      if (
        !savedDockerfileName ||
        savedDockerfileName === "" ||
        savedDockerfileName === "Dockerfile"
      ) {
        // 当前没有选择或只有默认值，自动选择第一个（优先选择根目录的 Dockerfile）
        const rootDockerfile = availableDockerfiles.value.find(
          (df) => df.path === "Dockerfile"
        );
        formData.value.dockerfile_name = rootDockerfile
          ? "Dockerfile"
          : availableDockerfiles.value[0].path;
        // #region agent log (disabled - causes connection errors)
        // fetch(
        //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
        //   {
        //     method: "POST",
        //     headers: { "Content-Type": "application/json" },
        //     body: JSON.stringify({
        //       location: "PipelinePanel.vue:2420",
        //       message:
        //         "Dockerfile name auto-selected (new mode, no previous selection)",
        //       data: {
        //         new: formData.value.dockerfile_name,
        //         old: savedDockerfileName,
        //       },
        //       timestamp: Date.now(),
        //       sessionId: "debug-session",
        //       runId: "run1",
        //       hypothesisId: "A",
        //     }),
        //   }
        // ).catch(() => {});
        // #endregion
      } else {
        // 有保存的选择（非编辑模式），检查是否在新列表中，如果在则保持，否则选择第一个
        const currentInList = availableDockerfiles.value.some(
          (df) => df.path === savedDockerfileName
        );
        if (currentInList) {
          formData.value.dockerfile_name = savedDockerfileName;
        } else {
          const rootDockerfile = availableDockerfiles.value.find(
            (df) => df.path === "Dockerfile"
          );
          formData.value.dockerfile_name = rootDockerfile
            ? "Dockerfile"
            : availableDockerfiles.value[0].path;
        }
        // #region agent log (disabled - causes connection errors)
        // fetch(
        //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
        //   {
        //     method: "POST",
        //     headers: { "Content-Type": "application/json" },
        //     body: JSON.stringify({
        //       location: "PipelinePanel.vue:2430",
        //       message:
        //         "Dockerfile name handled (new mode with previous selection)",
        //       data: {
        //         saved: savedDockerfileName,
        //         final: formData.value.dockerfile_name,
        //         in_list: currentInList,
        //       },
        //       timestamp: Date.now(),
        //       sessionId: "debug-session",
        //       runId: "run1",
        //       hypothesisId: "A",
        //     }),
        //   }
        // ).catch(() => {});
        // #endregion
      }
      // 扫描后重新加载服务（如果是用户主动切换 Dockerfile，传入 true）
      if (formData.value.use_project_dockerfile) {
        // 这里是在扫描 Dockerfile 后，可能是用户切换了 Dockerfile，传入 true 表示需要重新识别
        loadServices(true);
      }
    } else {
      // 没有扫描到 Dockerfile，如果当前选择不为空，保持原选择，否则设为默认值
      if (!savedDockerfileName) {
        formData.value.dockerfile_name = "Dockerfile";
      }
    }
  } catch (error) {
    console.error("扫描 Dockerfile 失败:", error);
    dockerfilesError.value =
      error.response?.data?.detail || "扫描 Dockerfile 失败";
    // 扫描失败时不清空列表，保持之前的列表（如果有），这样已保存的值还能显示
    // availableDockerfiles.value 保持原值
    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2404",
    //     message: "scanDockerfiles error",
    //     data: {
    //       error: error.message,
    //       response: error.response?.data,
    //       preserved_list_count: availableDockerfiles.value.length,
    //     },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion
  } finally {
    scanningDockerfiles.value = false;
    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2320",
    //     message: "scanDockerfiles completed",
    //     data: { final_dockerfile_name: formData.value.dockerfile_name },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion
  }
}

// 分支变化处理
function onBranchChanged() {
  // 如果切换到新分支且使用项目 Dockerfile，重新扫描 Dockerfile
  if (
    formData.value.use_project_dockerfile &&
    formData.value.branch &&
    formData.value.git_url
  ) {
    scanDockerfiles();
  }
}

// 加载服务列表（带防抖和去重）
async function loadServices(isDockerfileChanged = false) {
  if (!formData.value.git_url) {
    services.value = [];
    return Promise.resolve();
  }

  // 生成唯一标识，用于去重
  const currentKey = `${formData.value.git_url}_${formData.value.branch}_${
    formData.value.dockerfile_name
  }_${formData.value.source_id || ""}`;

  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === currentKey) {
    console.log("服务正在加载中，跳过重复请求:", currentKey);
    return Promise.resolve();
  }

  // 清除之前的防抖定时器
  if (loadingServicesTimer.value) {
    clearTimeout(loadingServicesTimer.value);
    loadingServicesTimer.value = null;
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value;

  // 编辑模式下且未切换 Dockerfile：不显示加载状态，直接返回（已保存的配置会直接显示）
  if (isEditing && !isDockerfileChanged) {
    // 如果正在验证，直接返回，避免重复验证
    if (isVerifyingServices.value) {
      return Promise.resolve();
    }

    // 在后台异步加载服务列表进行验证，但不阻塞界面
    // 先返回，让界面立即显示已保存的配置
    setTimeout(async () => {
      // 防止重复验证
      if (isVerifyingServices.value) {
        return;
      }
      isVerifyingServices.value = true;

      try {
        await loadServicesInternal(isDockerfileChanged, currentKey);
        // 加载完成后验证已保存的服务是否还存在（只验证一次）
        if (
          formData.value.push_mode === "multi" &&
          formData.value.selected_services
        ) {
          const validServices = formData.value.selected_services.filter(
            (serviceName) => services.value.some((s) => s.name === serviceName)
          );
          if (
            validServices.length !== formData.value.selected_services.length
          ) {
            formData.value.selected_services = validServices;
            Object.keys(formData.value.service_push_config || {}).forEach(
              (serviceName) => {
                if (!services.value.some((s) => s.name === serviceName)) {
                  delete formData.value.service_push_config[serviceName];
                }
              }
            );
          }
        } else if (
          formData.value.push_mode === "single" &&
          formData.value.selected_service
        ) {
          if (
            !services.value.some(
              (s) => s.name === formData.value.selected_service
            )
          ) {
            formData.value.selected_service = "";
          }
        }
      } catch (error) {
        // 后台验证失败不影响已保存的配置显示
        console.warn("后台验证服务列表失败，但已保存的配置仍然有效:", error);
      } finally {
        isVerifyingServices.value = false;
      }
    }, 100);
    return Promise.resolve();
  }

  // 新建模式或切换 Dockerfile：使用防抖延迟加载，避免重复触发
  return new Promise((resolve) => {
    loadingServicesTimer.value = setTimeout(async () => {
      loadingServicesTimer.value = null;
      try {
        await loadServicesInternal(isDockerfileChanged, currentKey);
        resolve();
      } catch (error) {
        resolve(); // 即使出错也 resolve，避免阻塞
      }
    }, 300); // 300ms 防抖延迟
  });
}

// 内部加载服务列表函数
async function loadServicesInternal(
  isDockerfileChanged = false,
  currentKey = ""
) {
  if (!formData.value.git_url) {
    services.value = [];
    return Promise.resolve();
  }

  // 生成唯一标识
  const key =
    currentKey ||
    `${formData.value.git_url}_${formData.value.branch}_${
      formData.value.dockerfile_name
    }_${formData.value.source_id || ""}`;

  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === key) {
    console.log("服务正在加载中，跳过重复请求:", key);
    return Promise.resolve();
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value;

  loadingServices.value = true;
  loadingServicesKey.value = key;
  servicesError.value = "";

  try {
    if (formData.value.use_project_dockerfile) {
      // 使用项目 Dockerfile
      const gitUrl = formData.value.git_url;
      const branch = formData.value.branch || null;
      const dockerfileName = formData.value.dockerfile_name || "Dockerfile";
      const sourceId = formData.value.source_id || null;

      // 使用缓存机制获取服务分析结果
      const servicesList = await getServiceAnalysisWithCache(
        async () => {
          const payload = {
            git_url: gitUrl,
            branch: branch,
            dockerfile_name: dockerfileName,
            source_id: sourceId,
          };
          return await axios.post("/api/parse-dockerfile-services", payload);
        },
        gitUrl,
        branch || "main",
        dockerfileName,
        sourceId,
        false // 不强制刷新，使用缓存
      );

      if (servicesList && servicesList.length > 0) {
        services.value = servicesList;

        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换 Dockerfile：保持原有配置
        } else {
          applyPushModeFromDockerfileAnalysis(wizardForceSingleMode.value);
        }
      } else {
        services.value = [];
        if (!isEditing || isDockerfileChanged) {
          applyPushModeFromDockerfileAnalysis(true);
        }
      }
    } else if (formData.value.template) {
      // 使用模板
      const res = await axios.get("/api/template-params", {
        params: {
          template: formData.value.template,
          project_type: formData.value.project_type,
        },
      });
      const templateServices = res.data.services || [];
      if (templateServices.length > 0) {
        services.value = templateServices;

        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换模板：保持原有配置
        } else {
          applyPushModeFromDockerfileAnalysis(wizardForceSingleMode.value);
        }
      } else {
        services.value = [];
        if (!isEditing || isDockerfileChanged) {
          applyPushModeFromDockerfileAnalysis(true);
        }
      }
    } else {
      services.value = [];
    }
  } catch (error) {
    console.error("加载服务列表失败:", error);
    servicesError.value = error.response?.data?.detail || "加载服务列表失败";
    services.value = [];
    return Promise.reject(error);
  } finally {
    loadingServices.value = false;
    loadingServicesKey.value = ""; // 清除加载标识
  }

  return Promise.resolve();
}

// 初始化服务配置
function initializeServiceConfigs() {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {};
  }
  formData.value.selected_services.forEach((serviceName) => {
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      // 如果是布尔值（旧格式），转换为对象格式
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保对象格式包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  });
}

// 推送模式变化
function onPushModeChange() {
  if (formData.value.push_mode === "single") {
    formData.value.selected_services = [];
    formData.value.selected_service = "";
  } else {
    formData.value.selected_service = "";
    if (
      services.value.length > 0 &&
      (!formData.value.selected_services ||
        formData.value.selected_services.length === 0)
    ) {
      formData.value.selected_services = services.value.map((s) => s.name);
      initializeServiceConfigs();
    }
  }
}

// 切换服务选择
function toggleService(serviceName) {
  if (!formData.value.selected_services) {
    formData.value.selected_services = [];
  }
  const index = formData.value.selected_services.indexOf(serviceName);
  if (index > -1) {
    formData.value.selected_services.splice(index, 1);
    delete formData.value.service_push_config[serviceName];
  } else {
    formData.value.selected_services.push(serviceName);
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  }
}

// 服务选择变化
function onServiceSelectionChange() {
  // 移除未选中服务的配置
  Object.keys(formData.value.service_push_config).forEach((serviceName) => {
    if (!formData.value.selected_services.includes(serviceName)) {
      delete formData.value.service_push_config[serviceName];
    }
  });
  // 为新选中的服务初始化配置
  formData.value.selected_services.forEach((serviceName) => {
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  });
}

// 全选服务
function selectAllServices() {
  if (services.value.length > 0) {
    formData.value.selected_services = services.value.map((s) => s.name);
    initializeServiceConfigs();
  }
}

// 全不选服务
function deselectAllServices() {
  formData.value.selected_services = [];
  formData.value.service_push_config = {};
}

// 移除服务
function removeService(serviceName) {
  const index = formData.value.selected_services.indexOf(serviceName);
  if (index > -1) {
    formData.value.selected_services.splice(index, 1);
    delete formData.value.service_push_config[serviceName];
  }
}

// 获取服务配置对象（确保返回对象格式，包含 push、imageName 和 tag 字段）
function getServiceConfig(serviceName) {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {};
  }
  // 如果是布尔值（旧格式），转换为对象格式
  if (
    formData.value.service_push_config[serviceName] === undefined ||
    typeof formData.value.service_push_config[serviceName] === "boolean"
  ) {
    const oldValue = formData.value.service_push_config[serviceName];
    formData.value.service_push_config[serviceName] = {
      push: typeof oldValue === "boolean" ? oldValue : false,
      imageName: "",
      tag: "",
    };
  } else if (
    formData.value.service_push_config[serviceName] &&
    typeof formData.value.service_push_config[serviceName] === "object"
  ) {
    // 确保包含所有字段
    const config = formData.value.service_push_config[serviceName];
    formData.value.service_push_config[serviceName] = {
      push: config.push !== undefined ? config.push : false,
      imageName: config.imageName !== undefined ? config.imageName : "",
      tag: config.tag !== undefined ? config.tag : "",
    };
  }
  return formData.value.service_push_config[serviceName];
}

// 获取服务的默认镜像名称（基于全局镜像名称前缀 + 服务名）
function getServiceDefaultImageName(serviceName) {
  if (!serviceName) {
    return formData.value.image_name || "myapp/demo";
  }

  let prefix = formData.value.image_name || "myapp/demo";

  // 去除前缀末尾的斜杠，避免出现双斜杠
  prefix = prefix.replace(/\/+$/, "");

  // 如果前缀已经以服务名结尾，直接返回前缀（避免重复拼接）
  // 检查格式：prefix/serviceName 或 prefix//serviceName 等
  const normalizedPrefix = prefix.replace(/\/+$/, "");
  if (
    normalizedPrefix.endsWith(`/${serviceName}`) ||
    normalizedPrefix === serviceName
  ) {
    return normalizedPrefix;
  }

  // 如果前缀就是服务名本身，直接返回
  if (prefix === serviceName) {
    return prefix;
  }

  // 否则拼接服务名（确保只有一个斜杠）
  return `${prefix}/${serviceName}`;
}

// 服务镜像名输入框失焦处理
function onServiceImageNameBlur(serviceName) {
  const config = getServiceConfig(serviceName);
  // 如果用户清空了自定义镜像名，确保使用默认值
  if (!config.imageName || !config.imageName.trim()) {
    config.imageName = "";
  }
}

// 恢复默认镜像名
function resetServiceImageName(serviceName) {
  const config = getServiceConfig(serviceName);
  config.imageName = "";
}

// 规范化服务推送配置（将旧格式的布尔值转换为新格式的对象，保留 push、imageName 和 tag 字段）
function normalizeServicePushConfig(config) {
  if (!config || typeof config !== "object") {
    return {};
  }
  const normalized = {};
  Object.keys(config).forEach((serviceName) => {
    const value = config[serviceName];
    // 如果是布尔值（旧格式），转换为对象格式
    if (typeof value === "boolean") {
      normalized[serviceName] = {
        push: value,
        imageName: "",
        tag: "",
      };
    } else if (value && typeof value === "object") {
      // 已经是对象格式，保留所有字段
      normalized[serviceName] = {
        push: value.push !== undefined ? value.push : false,
        imageName: value.imageName !== undefined ? value.imageName : "",
        tag: value.tag !== undefined ? value.tag : "",
      };
    }
  });
  return normalized;
}

/** 多阶段模式下任一分服务是否开启推送（用于同步顶层 pipeline.push） */
function anyServicePushEnabled(servicePushConfig) {
  if (!servicePushConfig || typeof servicePushConfig !== "object") {
    return false;
  }
  return Object.values(servicePushConfig).some(
    (cfg) => cfg && typeof cfg === "object" && cfg.push === true
  );
}

// 加载资源包列表
async function loadResourcePackages() {
  try {
    const res = await axios.get("/api/resource-packages");
    resourcePackages.value = res.data.packages || [];

    // 编辑模式下：确保已保存的资源包配置中的 target_path 有默认值
    // 如果某个已保存的资源包配置没有 target_path 或为空，使用资源包名称作为默认值（与分步构建一致）
    if (editingPipeline.value && formData.value.resource_package_configs) {
      formData.value.resource_package_configs.forEach((config) => {
        if (!config.target_path || config.target_path.trim() === "") {
          const pkg = resourcePackages.value.find(
            (p) => p.package_id === config.package_id
          );
          if (pkg && pkg.name) {
            // 如果路径为空，使用资源包名称（与分步构建一致）
            config.target_path = pkg.name;
          } else {
            config.target_path = "resources";
          }
        }
      });
    }
  } catch (error) {
    console.error("加载资源包列表失败:", error);
  }
}

// 获取资源包名称
function getResourcePackageName(packageId) {
  const pkg = resourcePackages.value.find((p) => p.package_id === packageId);
  return pkg ? pkg.name : packageId;
}

// 移除资源包
function removeResourcePackage(index) {
  formData.value.resource_package_configs.splice(index, 1);
}

// 检查资源包是否已选择
function isResourcePackageSelected(packageId) {
  return formData.value.resource_package_configs.some(
    (pkg) => pkg.package_id === packageId
  );
}

// 切换资源包选择
function toggleResourcePackage(pkg) {
  const index = formData.value.resource_package_configs.findIndex(
    (p) => p.package_id === pkg.package_id
  );
  if (index > -1) {
    // 取消选择：移除配置
    formData.value.resource_package_configs.splice(index, 1);
  } else {
    // 选择：添加配置，使用默认路径（资源包名称，与分步构建一致）
    const defaultPath = pkg.name || "resources";
    formData.value.resource_package_configs.push({
      package_id: pkg.package_id,
      target_path: defaultPath, // 默认使用资源包名称作为路径，与分步构建一致
    });
  }
}

// 获取资源包配置
function getResourcePackageConfig(packageId) {
  let config = formData.value.resource_package_configs.find(
    (p) => p.package_id === packageId
  );
  if (!config) {
    // 如果配置不存在，根据资源包信息创建默认配置
    const pkg = resourcePackages.value.find((p) => p.package_id === packageId);
    // 编辑模式下，如果已有保存的配置，不应该自动创建新配置
    // 只有在用户主动选择资源包时才创建配置
    // 这里返回一个临时对象，但不添加到列表中（由 toggleResourcePackage 处理）
    return {
      package_id: packageId,
      target_path: pkg ? pkg.name || "resources" : "resources", // 默认使用资源包名称作为路径
    };
  }
  return config;
}

// 更新资源包目标路径
function updateResourcePackagePath(packageId, targetPath) {
  const config = formData.value.resource_package_configs.find(
    (p) => p.package_id === packageId
  );
  if (config) {
    config.target_path = targetPath || "";
  } else {
    // 如果配置不存在，创建新配置
    formData.value.resource_package_configs.push({
      package_id: packageId,
      target_path: targetPath || "",
    });
  }
}

// Dockerfile 来源变化处理
async function onDockerfileSourceChange() {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:2744",
  //     message: "Dockerfile source changed",
  //     data: {
  //       use_project_dockerfile: formData.value.use_project_dockerfile,
  //       template: formData.value.template,
  //       dockerfile_name: formData.value.dockerfile_name,
  //       git_url: formData.value.git_url,
  //       branch: formData.value.branch,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "D",
  //   }),
  // }).catch(() => {});
  // #endregion
  if (formData.value.use_project_dockerfile) {
    // 使用项目 Dockerfile 时，清空模板
    formData.value.template = "";
    // 如果有数据源、分支和 Dockerfile，尝试加载 Dockerfile 内容
    if (
      formData.value.source_id &&
      formData.value.branch &&
      formData.value.dockerfile_name
    ) {
      try {
        await loadDockerfileFromRepo();
      } catch (error) {
        // 如果加载失败，清空编辑器
        dockerfileContentText.value = "";
      }
    } else {
      // 如果没有完整信息，清空编辑器
      dockerfileContentText.value = "";
    }
    // 如果有分支和 Dockerfile，重新加载服务（服务列表依赖于 Dockerfile）
    if (
      formData.value.git_url &&
      formData.value.branch &&
      formData.value.dockerfile_name
    ) {
      // Dockerfile 来源变化是用户主动切换，需要重新识别服务
      loadServices(true);
    } else if (formData.value.git_url && formData.value.branch) {
      // 如果有分支但没有 Dockerfile，先扫描 Dockerfile（扫描完成后会自动加载服务）
      scanDockerfiles();
    }
  } else {
    // 使用模板时，清空 Dockerfile 名称和内容
    formData.value.dockerfile_name = "Dockerfile";
    dockerfileContentText.value = "";
    // 如果选择了模板，加载模板内容并重新加载服务（切换到模板是用户主动切换）
    if (formData.value.template) {
      await onTemplateChange();
    }
  }
}

// 模板变化处理
async function onTemplateChange() {
  // 选择模板时，确保 use_project_dockerfile 为 false
  if (formData.value.template) {
    formData.value.use_project_dockerfile = false;
    // 加载模板的 Dockerfile 内容
    try {
      const res = await axios.get("/api/templates", {
        params: {
          name: formData.value.template,
          project_type: formData.value.project_type,
        },
      });
      if (res.data && res.data.content) {
        dockerfileContentText.value = res.data.content;
      }
    } catch (error) {
      console.error("加载模板内容失败:", error);
      // 如果加载失败，清空编辑器
      dockerfileContentText.value = "";
    }
    // 编辑模式下不自动加载，需要用户手动点击加载按钮
    // 新建模式下可以自动加载（通过判断 editingPipeline）
    if (!editingPipeline.value) {
      loadServices(true);
    }
  } else {
    // 清空模板时，清空 Dockerfile 内容
    dockerfileContentText.value = "";
    // 清空模板时，如果使用项目 Dockerfile 且有分支，重新加载服务（切换到项目 Dockerfile 是用户主动切换）
    // 编辑模式下不自动加载，需要用户手动点击加载按钮
    if (
      formData.value.use_project_dockerfile &&
      formData.value.git_url &&
      formData.value.branch &&
      !editingPipeline.value
    ) {
      loadServices(true);
    }
  }
}

// 根据项目类型过滤模板
const filteredTemplates = computed(() => {
  if (!formData.value.project_type) {
    return [];
  }
  return templates.value.filter(
    (t) => t.project_type === formData.value.project_type
  );
});

// 构建配置JSON（基于统一的任务配置结构）
const buildConfigJson = computed(() => {
  // 构建服务推送配置（与StepBuildPanel格式一致）
  const servicePushConfig = {};
  if (
    formData.value.selected_services &&
    formData.value.selected_services.length > 0
  ) {
    if (formData.value.push_mode === "multi") {
      // 多服务模式：处理所有启用的服务
      formData.value.selected_services.forEach((serviceName) => {
        const config = getServiceConfig(serviceName);
        const customImageName = config.imageName && config.imageName.trim();
        const finalImageName =
          customImageName || getServiceDefaultImageName(serviceName);
        const finalTag =
          (config.tag && config.tag.trim()) || formData.value.tag || "latest";

        servicePushConfig[serviceName] = {
          push: config.push || false,
          imageName: finalImageName,
          tag: finalTag,
        };
      });
    } else if (formData.value.push_mode === "single") {
      // 单服务模式：只处理第一个服务
      const firstService = formData.value.selected_services[0];
      if (firstService) {
        const config = getServiceConfig(firstService);
        // 单服务模式使用全局镜像名和标签
        servicePushConfig[firstService] = {
          push: config.push || false,
          imageName: formData.value.image_name || "",
          tag: formData.value.tag || "latest",
        };
      }
    }
  }

  const config = {
    git_url: formData.value.git_url || "",
    image_name: formData.value.image_name || "",
    tag: formData.value.tag || "latest",
    branch: formData.value.branch || null,
    project_type: formData.value.project_type || "jar",
    template: formData.value.template || "",
    template_params: formData.value.template_params || {},
    should_push: formData.value.push || false,
    sub_path: formData.value.sub_path || null,
    use_project_dockerfile: formData.value.use_project_dockerfile !== false,
    dockerfile_name: formData.value.dockerfile_name || "Dockerfile",
    dockerfile_content: formData.value.dockerfile_content || null,
    source_id: formData.value.source_id || null,
    selected_services: formData.value.selected_services || [],
    service_push_config:
      Object.keys(servicePushConfig).length > 0
        ? servicePushConfig
        : formData.value.service_push_config || {},
    service_template_params: formData.value.service_template_params || {},
    push_mode: formData.value.push_mode || "multi",
    resource_package_configs: formData.value.resource_package_configs || [],
  };

  // 移除null值和空值（保留false和0）
  // 注意：多阶段相关配置（push_mode、selected_services、service_push_config、service_template_params）需要保留
  const multiStageKeys = [
    "push_mode",
    "selected_services",
    "service_push_config",
    "service_template_params",
  ];
  Object.keys(config).forEach((key) => {
    // 多阶段相关配置始终保留
    if (multiStageKeys.includes(key)) {
      return;
    }

    if (
      config[key] === null ||
      config[key] === "" ||
      (Array.isArray(config[key]) && config[key].length === 0) ||
      (typeof config[key] === "object" &&
        !Array.isArray(config[key]) &&
        Object.keys(config[key]).length === 0)
    ) {
      delete config[key];
    }
  });

  return JSON.stringify(config, null, 2);
});


function formatGitUrl(url) {
  if (!url) return "";
  return url.replace(/^https?:\/\//, "").replace(/\.git$/, "");
}


async function loadProjectTypes() {
  projectTypesList.value = await getProjectTypes();
}


async function copyBuildConfigJson() {
  const text = buildConfigJson.value;
  const success = await copyToClipboard(text);
  if (success) {
    toastSuccess("构建配置JSON已复制到剪贴板");
  } else {
    toastError("自动复制失败，请手动选择并复制文本");
  }
}

async function regenerateWebhookToken() {
  if (await showConfirm({ message: "确定要重新生成 Webhook Token 吗？重新生成后需要更新 Git 平台的 Webhook URL。" })) {
    formData.value.webhook_token = generateUUID();
  }
}

async function regenerateWebhookSecret() {
  if (await showConfirm({ message: "确定要重新生成 Webhook 密钥吗？重新生成后需要更新 Git 平台的 Webhook Secret。" })) {
    formData.value.webhook_secret = generateUUID();
  }
}

function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

  async function loadPipelineForEdit(pipelineId) {
    try {
      const res = await axios.get(`/api/pipelines/${pipelineId}`);
      const pipeline = res.data?.pipeline ?? res.data;
      if (!pipeline || !pipeline.pipeline_id) {
        toastError("流水线不存在");
        return false;
      }
      applyPipelineToForm(pipeline);
      return true;
    } catch (error) {
      console.error("加载流水线失败:", error);
      toastApiError(error, "加载流水线失败");
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
    showResourcePackageModal,
    showBuildConfigJsonModal,
    saveBuildConfigJson,
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
    createPipelineMinimal,
    analyzeDockerfileForWizard,
    applyPushModeFromDockerfileAnalysis,
    switchWizardToSingleAppMode,
    switchWizardToMultiAppMode,
    setWizardPushMode,
    wizardForceSingleMode,
    wizardServiceAnalysisDone,
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
    loadDeployTasks,
    formatGitUrl,
    regenerateWebhookToken,
    regenerateWebhookSecret,
    generateUUID,
    copyBuildConfigJson,
  };
}
