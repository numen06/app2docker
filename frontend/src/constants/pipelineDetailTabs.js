/** 流水线配置页 Tab（列表页仅浏览/运行，配置在独立页完成） */

export const PIPELINE_CONFIG_TAB_KEYS = [
  "basic",
  "git",
  "services",
  "build",
  "dockerfile",
  "resource",
  "webhook",
  "post_webhook",
  "other",
];

export const PIPELINE_DETAIL_TAB_ALIASES = {
  edit: "basic",
  overview: "basic",
  history: "basic",
  permission: "basic",
  settings: "other",
};

const TAB_META = {
  basic: { label: "基本信息", icon: "fas fa-info-circle" },
  git: { label: "Git 配置", icon: "fas fa-code-branch" },
  services: { label: "多服务配置", icon: "fas fa-layer-group" },
  build: { label: "构建 JSON", icon: "fas fa-code" },
  dockerfile: { label: "Dockerfile", icon: "fas fa-file-code" },
  resource: { label: "资源包", icon: "fas fa-archive" },
  webhook: { label: "Webhook", icon: "fas fa-link" },
  post_webhook: { label: "构建后 Webhook", icon: "fas fa-bell" },
  other: { label: "其他选项", icon: "fas fa-sliders-h" },
};

export const PIPELINE_CONFIG_TABS = PIPELINE_CONFIG_TAB_KEYS.map((key) => ({
  key,
  ...TAB_META[key],
}));

export const PIPELINE_DETAIL_TABS = PIPELINE_CONFIG_TABS;
export const PIPELINE_CREATE_TABS = PIPELINE_CONFIG_TABS;
export const PIPELINE_DETAIL_TAB_KEYS = PIPELINE_CONFIG_TAB_KEYS;

export function normalizePipelineConfigTab(raw) {
  if (typeof raw !== "string" || !raw) return "basic";
  const mapped = PIPELINE_DETAIL_TAB_ALIASES[raw] || raw;
  return PIPELINE_CONFIG_TAB_KEYS.includes(mapped) ? mapped : "basic";
}

/** @deprecated 使用 normalizePipelineConfigTab */
export function normalizePipelineDetailTab(raw) {
  return normalizePipelineConfigTab(raw);
}

export function isPipelineConfigTab(tab) {
  return PIPELINE_CONFIG_TAB_KEYS.includes(tab);
}
