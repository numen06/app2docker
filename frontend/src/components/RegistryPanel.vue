<template>
  <div class="registry-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0"><i class="fas fa-box"></i> 镜像仓库配置</h5>
      <div class="d-flex gap-2">
        <button
          class="btn btn-outline-secondary btn-sm"
          @click="loadRegistries"
          :disabled="loadingRegistries"
          title="刷新列表"
        >
          <i
            class="fas fa-sync-alt"
            :class="{ 'fa-spin': loadingRegistries }"
          ></i>
          刷新
        </button>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          @click="showCreateRegistryModal"
        >
          <i class="fas fa-plus"></i> 新建仓库
        </button>
      </div>
    </div>

    <!-- 仓库列表 -->
    <div v-if="loadingRegistries" class="text-center py-5">
      <span class="spinner-border spinner-border-sm"></span> 加载中...
    </div>
    <div
      v-else-if="registries && registries.length === 0"
      class="text-center py-5 text-muted"
    >
      <i class="fas fa-box fa-3x mb-3"></i>
      <p class="mb-0">暂无镜像仓库</p>
      <p class="text-muted small mt-2">点击"新建仓库"按钮添加镜像仓库配置</p>
    </div>
    <div v-else class="row g-4">
      <div
        v-for="(registry, index) in registries"
        :key="index"
        class="col-12 col-md-6 col-xl-4"
      >
        <div
          class="card h-100 shadow-sm"
          :class="{ 'border-primary': registry.active }"
        >
          <div class="card-header bg-white">
            <div class="mb-2">
              <h5 class="card-title mb-0">
                <strong>{{ registry.name }}</strong>
                <span v-if="registry.active" class="badge bg-primary ms-2"
                  >激活</span
                >
              </h5>
            </div>
            <div class="btn-group btn-group-sm w-100">
              <button
                class="btn btn-outline-primary"
                @click="editRegistry(index)"
                title="编辑"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button
                class="btn btn-outline-info"
                @click="testRegistryLogin(index)"
                :disabled="testingRegistry === index"
                title="测试登录"
              >
                <i
                  class="fas fa-vial"
                  :class="{ 'fa-spin': testingRegistry === index }"
                ></i>
              </button>
              <button
                class="btn btn-outline-danger"
                @click="removeRegistry(index)"
                :disabled="registries.length === 1"
                title="删除"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>

          <div class="card-body">
            <div class="mb-3">
              <div class="d-flex align-items-center mb-1">
                <i
                  class="fas fa-server text-muted me-2"
                  style="width: 18px"
                ></i>
                <small
                  class="font-monospace text-truncate"
                  :title="registry.registry"
                  style="font-size: 0.9rem"
                >
                  {{ registry.registry }}
                </small>
              </div>
            </div>

            <div class="mb-3">
              <div
                v-if="registry.registry_prefix"
                class="d-flex align-items-center mb-1"
              >
                <i class="fas fa-tag text-muted me-2" style="width: 18px"></i>
                <small class="text-muted"
                  >前缀：{{ registry.registry_prefix }}</small
                >
              </div>
              <div class="d-flex align-items-center mb-1">
                <i class="fas fa-user text-muted me-2" style="width: 18px"></i>
                <small class="text-muted"
                  >账号：{{ registry.username || "未设置" }}</small
                >
              </div>
              <div class="d-flex align-items-center">
                <i class="fas fa-key text-muted me-2" style="width: 18px"></i>
                <small class="text-muted"
                  >密码：{{
                    registry.has_password ? "已设置" : "未设置"
                  }}</small
                >
              </div>
            </div>

            <div v-if="registryTestResult[index]" class="border-top pt-2 mt-2">
              <div
                v-if="registryTestResult[index].success"
                class="alert alert-success alert-sm mb-0 py-1"
              >
                <i class="fas fa-check-circle"></i>
                {{ registryTestResult[index].message }}
              </div>
              <div v-else class="alert alert-danger alert-sm mb-0 py-1">
                <i class="fas fa-times-circle"></i>
                {{ registryTestResult[index].message }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑镜像仓库模态框 -->
    <div
      v-if="showRegistryModal"
      class="modal fade show"
      style="display: block; z-index: 1050"
      tabindex="-1"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{
                editingRegistryIndex !== null ? "编辑镜像仓库" : "新建镜像仓库"
              }}
            </h5>
            <button
              type="button"
              class="btn-close"
              @click="closeRegistryModal"
            ></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveRegistry">
              <div class="mb-3">
                <label class="form-label"
                  >仓库名称 <span class="text-danger">*</span></label
                >
                <input
                  v-model="registryForm.name"
                  type="text"
                  class="form-control"
                  placeholder="如：Docker Hub"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label"
                  >Registry 地址 <span class="text-danger">*</span></label
                >
                <input
                  v-model="registryForm.registry"
                  type="text"
                  class="form-control"
                  placeholder="docker.io"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">镜像前缀（可选）</label>
                <input
                  v-model="registryForm.registry_prefix"
                  type="text"
                  class="form-control"
                  placeholder="your-namespace"
                />
                <small class="text-muted">用于自动生成镜像名称的前缀</small>
              </div>
              <div class="mb-3">
                <label class="form-label">账号</label>
                <input
                  v-model="registryForm.username"
                  type="text"
                  class="form-control"
                  placeholder="用户名"
                />
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <div class="input-group">
                  <input
                    v-model="registryForm.password"
                    type="password"
                    class="form-control"
                    placeholder="密码"
                  />
                  <button
                    type="button"
                    class="btn btn-outline-primary"
                    @click="testCurrentRegistryLogin"
                    :disabled="testingRegistry === 'current'"
                    :title="
                      testingRegistry === 'current' ? '测试中...' : '测试登录'
                    "
                  >
                    <i
                      :class="
                        testingRegistry === 'current'
                          ? 'fas fa-spinner fa-spin'
                          : 'fas fa-vial'
                      "
                    ></i>
                    {{ testingRegistry === "current" ? "测试中..." : "测试" }}
                  </button>
                </div>
                <div v-if="registryTestResult['current']" class="mt-2">
                  <div
                    v-if="registryTestResult['current'].success"
                    class="alert alert-success alert-sm mb-0 py-1"
                  >
                    <i class="fas fa-check-circle"></i>
                    {{ registryTestResult["current"].message }}
                  </div>
                  <div v-else class="alert alert-danger alert-sm mb-0 py-1">
                    <i class="fas fa-times-circle"></i>
                    {{ registryTestResult["current"].message }}
                    <div
                      v-if="registryTestResult['current'].suggestions"
                      class="mt-1"
                    >
                      <small>
                        <ul class="mb-0 ps-3">
                          <li
                            v-for="(suggestion, idx) in registryTestResult[
                              'current'
                            ].suggestions"
                            :key="idx"
                          >
                            {{ suggestion }}
                          </li>
                        </ul>
                      </small>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <div class="form-check">
                  <input
                    v-model="registryForm.active"
                    type="checkbox"
                    class="form-check-input"
                    id="registryActive"
                  />
                  <label class="form-check-label" for="registryActive">
                    设为激活仓库
                  </label>
                </div>
                <small class="text-muted">激活的仓库将作为默认推送目标</small>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              @click="closeRegistryModal"
            >
              取消
            </button>
            <button
              type="button"
              class="btn btn-primary btn-sm"
              @click="saveRegistry"
              :disabled="!registryForm.name || !registryForm.registry"
            >
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="showRegistryModal"
      class="modal-backdrop fade show"
      style="z-index: 1045"
    ></div>
  </div>
</template>

<script setup>
import axios from "axios";
import { onMounted, ref } from "vue";

// 镜像仓库相关状态
const registries = ref([]);
const loadingRegistries = ref(false);
const savingRegistries = ref(false);
const testingRegistry = ref(null);
const registryTestResult = ref({});
const showRegistryModal = ref(false);
const editingRegistryIndex = ref(null);
const registryForm = ref({
  name: "",
  registry: "",
  registry_prefix: "",
  username: "",
  password: "",
  active: false,
});

// 镜像仓库相关函数
async function loadRegistries() {
  loadingRegistries.value = true;
  try {
    const res = await axios.get("/api/get-config");
    const docker = res.data.docker || {};
    let registriesList = docker.registries || [];

    if (!registriesList || registriesList.length === 0) {
      registriesList = [
        {
          name: "Docker Hub",
          registry: "docker.io",
          registry_prefix: "",
          username: "",
          password: "",
          active: true,
        },
      ];
    }

    const hasActive = registriesList.some((r) => r.active);
    if (!hasActive && registriesList.length > 0) {
      registriesList[0].active = true;
    }

    registries.value = registriesList;
  } catch (error) {
    console.error("加载镜像仓库配置失败:", error);
    alert("加载镜像仓库配置失败");
  } finally {
    loadingRegistries.value = false;
  }
}

function showCreateRegistryModal() {
  editingRegistryIndex.value = null;
  registryForm.value = {
    name: "",
    registry: "docker.io",
    registry_prefix: "",
    username: "",
    password: "",
    active: false,
  };
  registryTestResult.value = {};
  showRegistryModal.value = true;
}

function editRegistry(index) {
  editingRegistryIndex.value = index;
  const registry = registries.value[index];
  registryForm.value = {
    name: registry.name,
    registry: registry.registry,
    registry_prefix: registry.registry_prefix || "",
    username: registry.username || "",
    password: registry.has_password ? "******" : "", // 不显示真实密码，使用 has_password 标志
    active: registry.active,
  };
  registryTestResult.value = {};
  showRegistryModal.value = true;
}

function closeRegistryModal() {
  showRegistryModal.value = false;
  editingRegistryIndex.value = null;
  registryForm.value = {
    name: "",
    registry: "",
    registry_prefix: "",
    username: "",
    password: "",
    active: false,
  };
  registryTestResult.value = {};
}

async function saveRegistry() {
  if (!registryForm.value.name || !registryForm.value.registry) {
    alert("请填写仓库名称和 Registry 地址");
    return;
  }

  savingRegistries.value = true;
  try {
    if (editingRegistryIndex.value !== null) {
      // 更新现有仓库
      const index = editingRegistryIndex.value;
      // 如果密码是占位符，不更新密码（后端会保留现有密码）
      const password =
        registryForm.value.password && registryForm.value.password !== "******"
          ? registryForm.value.password
          : undefined; // 不发送密码字段，让后端保留现有密码

      const updatedRegistry = {
        ...registryForm.value,
      };
      if (password !== undefined) {
        updatedRegistry.password = password;
      }

      registries.value[index] = {
        ...updatedRegistry,
        has_password:
          password !== undefined ? true : registries.value[index].has_password,
      };

      // 如果设置为激活，取消其他仓库的激活状态
      if (registryForm.value.active) {
        registries.value.forEach((reg, i) => {
          if (i !== index) {
            reg.active = false;
          }
        });
      }
    } else {
      // 添加新仓库
      const newRegistry = {
        ...registryForm.value,
      };

      // 如果设置为激活，取消其他仓库的激活状态
      if (newRegistry.active) {
        registries.value.forEach((reg) => {
          reg.active = false;
        });
      }

      registries.value.push(newRegistry);
    }

    // 保存到服务器
    await saveRegistries();
    closeRegistryModal();
  } catch (error) {
    console.error("保存镜像仓库失败:", error);
    alert(error.response?.data?.detail || "保存镜像仓库失败");
  } finally {
    savingRegistries.value = false;
  }
}

async function testCurrentRegistryLogin() {
  if (!registryForm.value.registry) {
    alert("请先填写Registry地址");
    return;
  }

  if (
    !registryForm.value.username ||
    !registryForm.value.password ||
    registryForm.value.password === "******"
  ) {
    alert("请先填写用户名和密码");
    return;
  }

  testingRegistry.value = "current";
  registryTestResult.value["current"] = null;

  try {
    const res = await axios.post("/api/registries/test", {
      name: registryForm.value.name,
      registry: registryForm.value.registry,
      username: registryForm.value.username,
      password: registryForm.value.password,
    });

    registryTestResult.value["current"] = {
      success: res.data.success,
      message: res.data.message,
      details: res.data.details,
      suggestions: res.data.suggestions,
    };

    if (res.data.success) {
      console.log("✅ Registry登录测试成功:", res.data);
    } else {
      console.warn("⚠️ Registry登录测试失败:", res.data);
    }
  } catch (error) {
    console.error("❌ Registry登录测试异常:", error);
    const errorData = error.response?.data || {};
    registryTestResult.value["current"] = {
      success: false,
      message: errorData.message || errorData.detail || "测试失败",
      details: errorData.details,
      suggestions: errorData.suggestions,
    };
  } finally {
    testingRegistry.value = null;
  }
}

function removeRegistry(index) {
  if (registries.value.length === 1) {
    alert("至少需要保留一个仓库");
    return;
  }

  const wasActive = registries.value[index].active;
  registries.value.splice(index, 1);

  if (wasActive && registries.value.length > 0) {
    registries.value[0].active = true;
  }
}

function setActiveRegistry(index) {
  registries.value.forEach((reg, i) => {
    reg.active = i === index;
  });
  // 自动保存
  saveRegistries();
}

async function testRegistryLogin(index) {
  const registry = registries.value[index];

  if (!registry.registry) {
    alert("请先填写Registry地址");
    return;
  }

  if (!registry.username) {
    alert("请先填写用户名");
    return;
  }

  // 如果密码未设置，提示用户
  if (!registry.has_password) {
    alert("请先配置密码");
    return;
  }

  testingRegistry.value = index;
  registryTestResult.value[index] = null;

  try {
    // 测试时使用仓库名称，后端会从配置中获取密码
    const res = await axios.post("/api/registries/test", {
      name: registry.name,
      registry: registry.registry,
      username: registry.username,
      // 不传递密码，后端会从配置中获取
    });

    registryTestResult.value[index] = {
      success: res.data.success,
      message: res.data.message,
      details: res.data.details,
      suggestions: res.data.suggestions,
    };

    if (res.data.success) {
      console.log("✅ Registry登录测试成功:", res.data);
    } else {
      console.warn("⚠️ Registry登录测试失败:", res.data);
    }
  } catch (error) {
    console.error("❌ Registry登录测试异常:", error);
    const errorData = error.response?.data || {};
    registryTestResult.value[index] = {
      success: false,
      message: errorData.message || errorData.detail || "测试失败",
      details: errorData.details,
      suggestions: errorData.suggestions,
    };
  } finally {
    testingRegistry.value = null;
  }
}

async function saveRegistries() {
  savingRegistries.value = true;
  try {
    const res = await axios.post("/api/registries", {
      registries: registries.value,
    });
    console.log("✅ 仓库配置保存成功:", res.data);
    alert("镜像仓库配置保存成功");
    // 重新加载以确保状态同步
    await loadRegistries();
  } catch (error) {
    console.error("❌ 保存镜像仓库配置失败:", error);
    const errorMsg =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      "保存配置失败";
    alert(errorMsg);
  } finally {
    savingRegistries.value = false;
  }
}

onMounted(() => {
  loadRegistries();
});
</script>

<style scoped>
.registry-panel {
  padding: 1rem;
}

.card {
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.125);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15) !important;
}

.card-header {
  border-bottom: 1px solid rgba(0, 0, 0, 0.125);
  padding: 1rem 1.25rem;
  background-color: #f8f9fa;
}

.card-title {
  font-size: 1.1rem;
  margin: 0;
  font-weight: 600;
  line-height: 1.5;
}

.card-body {
  padding: 1.25rem;
  line-height: 1.6;
}

.font-monospace {
  font-family: "Courier New", monospace;
  font-size: 0.85em;
}
</style>
