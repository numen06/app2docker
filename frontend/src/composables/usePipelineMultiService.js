import axios from "axios";
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";
import { ref, watch } from "vue";

function anyServicePushEnabled(servicePushConfig) {
  if (!servicePushConfig || typeof servicePushConfig !== "object") return false;
  return Object.values(servicePushConfig).some(
    (cfg) => cfg && typeof cfg === "object" && cfg.push === true
  );
}

function initFormFromPipeline(pipeline) {
  const form = {
    push_mode: pipeline.push_mode || "multi",
    selected_services: pipeline.selected_services
      ? [...pipeline.selected_services]
      : [],
    service_push_config: pipeline.service_push_config
      ? JSON.parse(JSON.stringify(pipeline.service_push_config))
      : {},
    image_name: pipeline.image_name || "",
    tag: pipeline.tag || "latest",
  };
  const isSingle = form.push_mode === "single";
  if (isSingle && form.selected_services.length === 0) {
    const name = "service1";
    form.selected_services.push(name);
    form.service_push_config[name] = {
      enabled: false,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  form.selected_services.forEach((serviceName) => {
    if (!form.service_push_config[serviceName]) {
      form.service_push_config[serviceName] = {
        enabled: isSingle ? false : true,
        push: false,
        imageName: "",
        tag: "",
      };
    } else if (typeof form.service_push_config[serviceName] === "boolean") {
      const oldValue = form.service_push_config[serviceName];
      form.service_push_config[serviceName] = {
        enabled: isSingle ? false : true,
        push: oldValue,
        imageName: "",
        tag: "",
      };
    } else if (form.service_push_config[serviceName].enabled === undefined) {
      form.service_push_config[serviceName].enabled = isSingle ? false : true;
    } else if (isSingle) {
      form.service_push_config[serviceName].enabled = false;
    }
  });
  return form;
}

function ensureMultiServiceFormState(fd) {
  const isSingle = fd.push_mode === "single";
  if (isSingle && (!fd.selected_services || fd.selected_services.length === 0)) {
    const name = "service1";
    if (!fd.selected_services) fd.selected_services = [];
    fd.selected_services.push(name);
    if (!fd.service_push_config) fd.service_push_config = {};
    fd.service_push_config[name] = {
      enabled: false,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  (fd.selected_services || []).forEach((serviceName) => {
    if (!fd.service_push_config) fd.service_push_config = {};
    if (!fd.service_push_config[serviceName]) {
      fd.service_push_config[serviceName] = {
        enabled: isSingle ? false : true,
        push: false,
        imageName: "",
        tag: "",
      };
    } else if (typeof fd.service_push_config[serviceName] === "boolean") {
      const oldValue = fd.service_push_config[serviceName];
      fd.service_push_config[serviceName] = {
        enabled: isSingle ? false : true,
        push: oldValue,
        imageName: "",
        tag: "",
      };
    } else if (fd.service_push_config[serviceName].enabled === undefined) {
      fd.service_push_config[serviceName].enabled = isSingle ? false : true;
    } else if (isSingle) {
      fd.service_push_config[serviceName].enabled = false;
    }
  });
}

export function usePipelineMultiService({
  formData: externalFormData,
  getPipeline,
  onSaved,
  embedded = false,
} = {}) {
  const pipelineRef = ref(null);
  const multiServiceFormData =
    externalFormData ||
    ref({
      push_mode: "multi",
      selected_services: [],
      service_push_config: {},
      image_name: "",
      tag: "latest",
    });
  const savingMultiServiceConfig = ref(false);
  const parsingDockerfileForMultiService = ref(false);

  function loadFromPipeline(pipeline) {
    pipelineRef.value = pipeline;
    if (externalFormData) {
      ensureMultiServiceFormState(multiServiceFormData.value);
      return;
    }
    multiServiceFormData.value = initFormFromPipeline(pipeline);
  }

  function resolvePipeline() {
    if (typeof getPipeline === "function") return getPipeline();
    return pipelineRef.value;
  }

  watch(
    () => multiServiceFormData.value.push_mode,
    (newMode, oldMode) => {
      if (newMode === "single") {
        if (multiServiceFormData.value.selected_services.length === 0) {
          const defaultServiceName = "service1";
          multiServiceFormData.value.selected_services.push(defaultServiceName);
          if (
            !multiServiceFormData.value.service_push_config[defaultServiceName]
          ) {
            multiServiceFormData.value.service_push_config[defaultServiceName] =
              {
                enabled: false,
                push: false,
                imageName: "",
                tag: "",
              };
          }
        } else {
          multiServiceFormData.value.selected_services.forEach((serviceName) => {
            if (!multiServiceFormData.value.service_push_config[serviceName]) {
              multiServiceFormData.value.service_push_config[serviceName] = {
                enabled: false,
                push: false,
                imageName: "",
                tag: "",
              };
            } else {
              multiServiceFormData.value.service_push_config[
                serviceName
              ].enabled = false;
            }
          });
        }
      } else if (newMode === "multi" && oldMode === "single") {
        multiServiceFormData.value.selected_services.forEach((serviceName) => {
          if (!multiServiceFormData.value.service_push_config[serviceName]) {
            multiServiceFormData.value.service_push_config[serviceName] = {
              enabled: false,
              push: false,
              imageName: "",
              tag: "",
            };
          } else if (
            multiServiceFormData.value.service_push_config[serviceName]
              .enabled === undefined
          ) {
            multiServiceFormData.value.service_push_config[
              serviceName
            ].enabled = false;
          }
        });
      }
    }
  );

  function getMultiServiceDefaultImageName(serviceName) {
    if (!serviceName) {
      return multiServiceFormData.value.image_name || "myapp/demo";
    }
    let prefix = multiServiceFormData.value.image_name || "myapp/demo";
    prefix = prefix.replace(/\/+$/, "");
    const normalizedPrefix = prefix.replace(/\/+$/, "");
    if (
      normalizedPrefix.endsWith(`/${serviceName}`) ||
      normalizedPrefix === serviceName
    ) {
      return normalizedPrefix;
    }
    if (prefix === serviceName) return prefix;
    return `${prefix}/${serviceName}`;
  }

  function addServiceToMultiConfig() {
    const newServiceName = `service${
      multiServiceFormData.value.selected_services.length + 1
    }`;
    multiServiceFormData.value.selected_services.push(newServiceName);
    multiServiceFormData.value.service_push_config[newServiceName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }

  function removeServiceFromMultiConfig(index) {
    const serviceName = multiServiceFormData.value.selected_services[index];
    multiServiceFormData.value.selected_services.splice(index, 1);
    if (multiServiceFormData.value.service_push_config[serviceName]) {
      delete multiServiceFormData.value.service_push_config[serviceName];
    }
  }

  function updateServiceName(index, newName) {
    const oldName = multiServiceFormData.value.selected_services[index];
    if (oldName === newName) return;
    multiServiceFormData.value.selected_services[index] = newName;
    if (multiServiceFormData.value.service_push_config[oldName]) {
      multiServiceFormData.value.service_push_config[newName] =
        multiServiceFormData.value.service_push_config[oldName];
      delete multiServiceFormData.value.service_push_config[oldName];
    } else {
      multiServiceFormData.value.service_push_config[newName] = {
        enabled: true,
        push: false,
        imageName: "",
        tag: "",
      };
    }
  }

  function updateServiceImageName(serviceName, imageName) {
    if (!multiServiceFormData.value.service_push_config[serviceName]) {
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: true,
        push: false,
        imageName: "",
        tag: "",
      };
    }
    multiServiceFormData.value.service_push_config[serviceName].imageName =
      imageName;
  }

  function updateServiceTag(serviceName, tag) {
    if (!multiServiceFormData.value.service_push_config[serviceName]) {
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: true,
        push: false,
        imageName: "",
        tag: "",
      };
    }
    multiServiceFormData.value.service_push_config[serviceName].tag = tag;
  }

  function updateServicePush(serviceName, push) {
    if (!multiServiceFormData.value.service_push_config[serviceName]) {
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: true,
        push: false,
        imageName: "",
        tag: "",
      };
    }
    multiServiceFormData.value.service_push_config[serviceName].push = push;
  }

  function getSingleServicePush() {
    if (multiServiceFormData.value.push_mode !== "single") return false;
    const firstService =
      multiServiceFormData.value.selected_services?.[0] || null;
    if (!firstService) return false;
    const config = multiServiceFormData.value.service_push_config[firstService];
    return config && config.push !== undefined ? config.push : false;
  }

  function updateSingleServicePush(push) {
    if (multiServiceFormData.value.push_mode !== "single") return;
    const firstService =
      multiServiceFormData.value.selected_services?.[0] || null;
    if (!firstService) return;
    updateServicePush(firstService, push);
  }

  function updateServiceEnabled(serviceName, enabled) {
    if (!multiServiceFormData.value.service_push_config[serviceName]) {
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: true,
        push: false,
        imageName: "",
        tag: "",
      };
    }
    multiServiceFormData.value.service_push_config[serviceName].enabled =
      enabled;
  }

  function enableAllServices() {
    multiServiceFormData.value.selected_services.forEach((serviceName) => {
      updateServiceEnabled(serviceName, true);
    });
  }

  function disableAllServices() {
    multiServiceFormData.value.selected_services.forEach((serviceName) => {
      updateServiceEnabled(serviceName, false);
    });
  }

  async function parseDockerfileForMultiService() {
    const pipeline = resolvePipeline();
    if (!pipeline) {
      toastError("无法获取流水线信息");
      return;
    }
    if (!pipeline.git_url) {
      toastError("流水线未配置 Git 地址，无法识别 Dockerfile");
      return;
    }
    if (!pipeline.branch) {
      toastError("流水线未配置分支，无法识别 Dockerfile");
      return;
    }
    parsingDockerfileForMultiService.value = true;
    try {
      const res = await axios.post("/api/parse-dockerfile-services", {
        git_url: pipeline.git_url,
        branch: pipeline.branch,
        dockerfile_name: pipeline.dockerfile_name || "Dockerfile",
        source_id: pipeline.source_id || null,
      });
      const servicesList = res.data.services || [];
      if (servicesList.length === 0) {
        toastInfo("未从 Dockerfile 中识别到服务");
        return;
      }
      if (multiServiceFormData.value.selected_services.length > 0) {
        const confirmed = await showConfirm({ message: `已识别到 ${servicesList.length} 个服务，是否覆盖现有服务列表？` });
        if (!confirmed) return;
      }
      multiServiceFormData.value.selected_services = [];
      multiServiceFormData.value.service_push_config = {};
      servicesList.forEach((service) => {
        const serviceName = service.name;
        multiServiceFormData.value.selected_services.push(serviceName);
        multiServiceFormData.value.service_push_config[serviceName] = {
          enabled: true,
          push: false,
          imageName: "",
          tag: multiServiceFormData.value.tag || "latest",
        };
      });
      if (!multiServiceFormData.value.image_name?.trim()) {
        const match = pipeline.git_url.match(/\/([^/]+?)(?:\.git)?$/);
        if (match?.[1]) {
          multiServiceFormData.value.image_name = match[1];
        }
      }
      toastSuccess(`成功识别 ${servicesList.length} 个服务`);
    } catch (error) {
      toastError(`识别失败: ${error.response?.data?.detail || "解析 Dockerfile 失败"}`);
    } finally {
      parsingDockerfileForMultiService.value = false;
    }
  }

  async function saveMultiServiceConfig() {
    if (embedded) return;
    const pipeline = resolvePipeline();
    if (savingMultiServiceConfig.value || !pipeline) return;
    const pipelineId = pipeline.pipeline_id;
    const serviceNames = multiServiceFormData.value.selected_services.filter(
      (name) => name && name.trim()
    );
    if (
      serviceNames.length === 0 &&
      multiServiceFormData.value.push_mode === "multi"
    ) {
      toastInfo("多服务模式下至少需要添加一个服务");
      return;
    }
    if (new Set(serviceNames).size !== serviceNames.length) {
      toastError("服务名称不能重复");
      return;
    }

    savingMultiServiceConfig.value = true;
    try {
      let payload;
      if (multiServiceFormData.value.push_mode === "single") {
        const names = [...serviceNames];
        if (names.length === 0) names.push("service1");
        const normalizedServicePushConfig = {};
        names.forEach((serviceName) => {
          const config =
            multiServiceFormData.value.service_push_config[serviceName];
          normalizedServicePushConfig[serviceName] = {
            enabled: false,
            push: config?.push ?? false,
            imageName: config?.imageName || "",
            tag: config?.tag || "",
          };
        });
        const firstCfg = normalizedServicePushConfig[names[0]];
        payload = {
          push_mode: "single",
          selected_services: names,
          service_push_config: normalizedServicePushConfig,
          image_name:
            multiServiceFormData.value.image_name ||
            pipeline.image_name ||
            "",
          tag:
            multiServiceFormData.value.tag ||
            pipeline.tag ||
            "latest",
          push: !!(firstCfg && firstCfg.push),
        };
      } else {
        const enabledServices = serviceNames.filter((serviceName) => {
          const config =
            multiServiceFormData.value.service_push_config[serviceName];
          return config?.enabled !== false;
        });
        if (enabledServices.length === 0) {
          toastInfo("多服务模式下至少需要启用一个服务");
          return;
        }
        const normalizedServicePushConfig = {};
        enabledServices.forEach((serviceName) => {
          const config =
            multiServiceFormData.value.service_push_config[serviceName];
          const customImageName = config?.imageName?.trim();
          normalizedServicePushConfig[serviceName] = {
            push: config?.push ?? false,
            imageName:
              customImageName || getMultiServiceDefaultImageName(serviceName),
            tag:
              config?.tag?.trim() ||
              multiServiceFormData.value.tag ||
              "latest",
          };
        });
        payload = {
          push_mode: "multi",
          selected_services: enabledServices,
          service_push_config: normalizedServicePushConfig,
          image_name:
            multiServiceFormData.value.image_name ||
            pipeline.image_name ||
            "",
          tag:
            multiServiceFormData.value.tag ||
            pipeline.tag ||
            "latest",
          push: anyServicePushEnabled(normalizedServicePushConfig),
        };
      }
      await axios.put(`/api/pipelines/${pipelineId}`, payload);
      toastSuccess("多服务配置已保存");
      onSaved?.();
    } catch (error) {
      toastApiError(error, "保存多服务配置失败");
    } finally {
      savingMultiServiceConfig.value = false;
    }
  }

  return {
    multiServiceFormData,
    savingMultiServiceConfig,
    parsingDockerfileForMultiService,
    loadFromPipeline,
    addServiceToMultiConfig,
    removeServiceFromMultiConfig,
    updateServiceName,
    updateServiceImageName,
    updateServiceTag,
    updateServicePush,
    getSingleServicePush,
    updateSingleServicePush,
    updateServiceEnabled,
    enableAllServices,
    disableAllServices,
    getMultiServiceDefaultImageName,
    parseDockerfileForMultiService,
    saveMultiServiceConfig,
  };
}
