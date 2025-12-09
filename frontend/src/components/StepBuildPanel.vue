<template>
  <div class="step-build-panel">
    <!-- 步骤指示器 -->
    <div class="steps-indicator mb-4">
      <div
        class="step-item"
        :class="{ active: currentStep >= 1, completed: currentStep > 1 }"
      >
        <div class="step-number">1</div>
        <div class="step-label">选择数据源</div>
      </div>
      <div class="step-connector" :class="{ completed: currentStep > 1 }"></div>
      <div
        class="step-item"
        :class="{ active: currentStep >= 2, completed: currentStep > 2 }"
      >
        <div class="step-number">2</div>
        <div class="step-label">确认分支</div>
      </div>
      <div class="step-connector" :class="{ completed: currentStep > 2 }"></div>
      <div
        class="step-item"
        :class="{ active: currentStep >= 3, completed: currentStep > 3 }"
      >
        <div class="step-number">3</div>
        <div class="step-label">选择模板</div>
      </div>
      <div class="step-connector" :class="{ completed: currentStep > 3 }"></div>
      <div
        class="step-item"
        :class="{ active: currentStep >= 4, completed: currentStep > 4 }"
      >
        <div class="step-number">4</div>
        <div class="step-label">选择服务</div>
      </div>
      <div class="step-connector" :class="{ completed: currentStep > 4 }"></div>
      <div
        class="step-item"
        :class="{ active: currentStep >= 5, completed: currentStep > 5 }"
      >
        <div class="step-number">5</div>
        <div class="step-label">选择资源包</div>
      </div>
      <div class="step-connector" :class="{ completed: currentStep > 5 }"></div>
      <div
        class="step-item"
        :class="{ active: currentStep >= 6, completed: currentStep > 6 }"
      >
        <div class="step-number">6</div>
        <div class="step-label">开始构建</div>
      </div>
    </div>

    <!-- 步骤内容 -->
    <div class="step-content">
      <!-- 步骤1: 选择数据源 -->
      <div v-if="currentStep === 1" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-database text-primary"></i> 步骤 1：选择数据源
        </h5>

        <div class="mb-3">
          <label class="form-label">
            数据源类型 <span class="text-danger">*</span>
          </label>
          <div class="btn-group w-100" role="group">
            <button
              type="button"
              class="btn"
              :class="
                buildConfig.sourceType === 'file'
                  ? 'btn-primary'
                  : 'btn-outline-primary'
              "
              @click="buildConfig.sourceType = 'file'"
            >
              <i class="fas fa-file-upload"></i> 上传文件
            </button>
            <button
              type="button"
              class="btn"
              :class="
                buildConfig.sourceType === 'git'
                  ? 'btn-primary'
                  : 'btn-outline-primary'
              "
              @click="buildConfig.sourceType = 'git'"
            >
              <i class="fas fa-code-branch"></i> Git 数据源
            </button>
          </div>
        </div>

        <!-- 文件上传 -->
        <div v-if="buildConfig.sourceType === 'file'" class="mb-3">
          <label class="form-label">
            选择文件 <span class="text-danger">*</span>
          </label>
          <input
            type="file"
            class="form-control"
            :accept="fileAccept"
            @change="handleFileChange"
            required
          />
          <div
            v-if="buildConfig.file"
            class="alert alert-success mt-2 py-2 px-3 small"
          >
            <i class="fas fa-check-circle"></i> 已选择:
            <strong>{{ buildConfig.file.name }}</strong> ({{
              formatFileSize(buildConfig.file.size)
            }})
          </div>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 支持 .jar 文件或
            .zip、.tar、.tar.gz 压缩包
          </div>
        </div>

        <!-- Git 数据源 -->
        <div v-if="buildConfig.sourceType === 'git'" class="mb-3">
          <label class="form-label">
            Git 数据源 <span class="text-danger">*</span>
          </label>
          <select
            v-model="buildConfig.sourceId"
            class="form-select"
            @change="onSourceSelected"
            required
          >
            <option value="">-- 请选择数据源 --</option>
            <option
              v-for="source in gitSources"
              :key="source.source_id"
              :value="source.source_id"
            >
              {{ source.name }} ({{ formatGitUrl(source.git_url) }})
            </option>
          </select>
          <div
            v-if="buildConfig.sourceId && repoVerified"
            class="alert alert-success alert-sm mt-2 mb-0"
          >
            <i class="fas fa-check-circle"></i>
            数据源已选择：{{ branchesAndTags.branches.length }} 个分支、{{
              branchesAndTags.tags.length
            }}
            个标签
          </div>
        </div>

        <div class="d-flex justify-content-end mt-4">
          <button
            class="btn btn-primary"
            @click="nextStep"
            :disabled="!canProceedStep1"
          >
            下一步 <i class="fas fa-arrow-right ms-1"></i>
          </button>
        </div>
      </div>

      <!-- 步骤2: 确认分支（仅Git数据源） -->
      <div v-if="currentStep === 2" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-code-branch text-primary"></i> 步骤 2：确认分支
        </h5>

        <div v-if="buildConfig.sourceType === 'file'" class="alert alert-info">
          <i class="fas fa-info-circle"></i>
          文件上传模式无需选择分支，将直接进入下一步。
        </div>

        <div v-else class="mb-3">
          <label class="form-label"
            >分支/标签 <span class="text-danger">*</span></label
          >
          <select
            v-if="repoVerified"
            v-model="buildConfig.branch"
            class="form-select"
            @change="onBranchChanged"
            required
          >
            <option value="">
              使用默认分支 ({{ branchesAndTags.default_branch || "main" }})
            </option>
            <optgroup v-if="branchesAndTags.branches.length > 0" label="分支">
              <option
                v-for="branch in branchesAndTags.branches"
                :key="branch"
                :value="branch"
              >
                {{ branch }}
              </option>
            </optgroup>
            <optgroup v-if="branchesAndTags.tags.length > 0" label="标签">
              <option
                v-for="tag in branchesAndTags.tags"
                :key="tag"
                :value="tag"
              >
                {{ tag }}
              </option>
            </optgroup>
          </select>
          <input
            v-else
            type="text"
            class="form-control"
            placeholder="请先选择数据源"
            disabled
          />
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 选择要构建的分支或标签
          </div>
        </div>

        <div class="d-flex justify-content-between mt-4">
          <button class="btn btn-outline-secondary" @click="prevStep">
            <i class="fas fa-arrow-left me-1"></i> 上一步
          </button>
          <button
            class="btn btn-primary"
            @click="nextStep"
            :disabled="
              buildConfig.sourceType === 'git' &&
              !buildConfig.branch &&
              !branchesAndTags.default_branch
            "
          >
            下一步 <i class="fas fa-arrow-right ms-1"></i>
          </button>
        </div>
      </div>

      <!-- 步骤3: 选择模板 -->
      <div v-if="currentStep === 3" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-layer-group text-primary"></i> 步骤 3：选择模板
        </h5>

        <div class="mb-3">
          <label class="form-label">
            项目类型 <span class="text-danger">*</span>
          </label>
          <div class="btn-group w-100" role="group">
            <button
              v-for="type in projectTypes"
              :key="type.value"
              type="button"
              class="btn"
              :class="
                buildConfig.projectType === type.value
                  ? 'btn-primary'
                  : 'btn-outline-primary'
              "
              @click="changeProjectType(type.value)"
            >
              <i :class="getProjectTypeIcon(type.value)"></i>
              {{ type.label }}
            </button>
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label">模板</label>
          <div class="input-group input-group-sm mb-1">
            <span class="input-group-text"><i class="fas fa-search"></i></span>
            <input
              v-model="templateSearch"
              type="text"
              class="form-control"
              placeholder="搜索模板..."
              :disabled="buildConfig.useProjectDockerfile"
            />
          </div>
          <select
            v-model="buildConfig.template"
            class="form-select"
            @change="loadTemplateParams"
            :disabled="buildConfig.useProjectDockerfile"
          >
            <option value="">-- 请选择模板 --</option>
            <option
              v-for="tpl in filteredTemplates"
              :key="tpl.name"
              :value="tpl.name"
            >
              {{ tpl.name }} ({{ getProjectTypeLabel(tpl.project_type)
              }}{{ tpl.type === "builtin" ? " · 内置" : "" }})
            </option>
          </select>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i>
            <span v-if="buildConfig.useProjectDockerfile">
              将使用项目中的 Dockerfile，模板选项已禁用
            </span>
            <span v-else> 已按项目类型过滤，可在模板管理中维护 </span>
          </div>
        </div>

        <!-- Dockerfile 选择选项（仅Git数据源且非文件上传） -->
        <div v-if="buildConfig.sourceType === 'git'" class="mb-3">
          <div class="form-check">
            <input
              v-model="buildConfig.useProjectDockerfile"
              type="checkbox"
              class="form-check-input"
              id="useProjectDockerfile"
              @change="onUseProjectDockerfileChange"
            />
            <label class="form-check-label" for="useProjectDockerfile">
              <i class="fas fa-file-code"></i> 优先使用项目中的 Dockerfile
            </label>
          </div>
          <div v-if="buildConfig.useProjectDockerfile" class="mt-2">
            <label class="form-label">Dockerfile 文件名</label>
            <select
              v-model="buildConfig.dockerfileName"
              class="form-select form-select-sm"
            >
              <option value="Dockerfile">Dockerfile（默认）</option>
              <option
                v-for="dockerfile in availableDockerfiles"
                :key="dockerfile"
                :value="dockerfile"
              >
                {{ dockerfile }}
              </option>
            </select>
          </div>
        </div>

        <div class="d-flex justify-content-between mt-4">
          <button class="btn btn-outline-secondary" @click="prevStep">
            <i class="fas fa-arrow-left me-1"></i> 上一步
          </button>
          <button
            class="btn btn-primary"
            @click="nextStep"
            :disabled="
              !buildConfig.projectType ||
              (!buildConfig.template && !buildConfig.useProjectDockerfile)
            "
          >
            下一步 <i class="fas fa-arrow-right ms-1"></i>
          </button>
        </div>
      </div>

      <!-- 步骤4: 选择服务（单应用/多服务） -->
      <div v-if="currentStep === 4" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-server text-primary"></i> 步骤 4：选择服务
        </h5>

        <div v-if="parsingServices" class="text-center py-4">
          <span class="spinner-border spinner-border-sm me-2"></span>
          正在分析模板...
        </div>

        <div v-else-if="servicesError" class="alert alert-warning">
          <i class="fas fa-exclamation-triangle"></i> {{ servicesError }}
        </div>

        <div v-else-if="services.length === 0" class="alert alert-info">
          <i class="fas fa-info-circle"></i>
          当前模板为单应用模式，无需选择服务。
        </div>

        <!-- 多服务模式 -->
        <div v-else class="mb-3">
          <!-- 推送模式选择（仅模板模式且非文件上传，项目 Dockerfile 总是多阶段推送） -->
          <div
            v-if="
              !buildConfig.useProjectDockerfile &&
              buildConfig.sourceType === 'git'
            "
            class="mb-3"
          >
            <label class="form-label"
              >推送模式 <span class="text-danger">*</span></label
            >
            <div class="btn-group w-100" role="group">
              <button
                type="button"
                class="btn"
                :class="
                  buildConfig.pushMode === 'single'
                    ? 'btn-primary'
                    : 'btn-outline-primary'
                "
                @click="onPushModeChange('single')"
              >
                <i class="fas fa-box"></i> 单服务推送
              </button>
              <button
                type="button"
                class="btn"
                :class="
                  buildConfig.pushMode === 'multi'
                    ? 'btn-primary'
                    : 'btn-outline-primary'
                "
                @click="onPushModeChange('multi')"
              >
                <i class="fas fa-boxes"></i> 多服务推送
              </button>
            </div>
            <div class="form-text small text-muted">
              <i class="fas fa-info-circle"></i>
              <span v-if="buildConfig.pushMode === 'single'">
                单服务推送：只能选择一个服务，定义镜像名和标签
              </span>
              <span v-else> 多服务推送：可以批量设置推送、镜像名和标签 </span>
            </div>
            <div
              v-if="buildConfig.pushMode === 'single'"
              class="alert alert-info alert-sm mt-2 mb-0"
            >
              <i class="fas fa-info-circle"></i>
              单服务推送模式下，请选择一个服务并定义镜像名和标签
            </div>
          </div>

          <!-- 单服务推送模式 -->
          <div
            v-if="
              buildConfig.pushMode === 'single' &&
              !buildConfig.useProjectDockerfile &&
              buildConfig.sourceType === 'git'
            "
            class="mb-3"
          >
            <div class="card border-primary">
              <div class="card-header bg-primary bg-opacity-10">
                <h6 class="mb-0">
                  <i class="fas fa-box text-primary"></i> 单服务推送模式
                </h6>
              </div>
              <div class="card-body">
                <div class="mb-3">
                  <label class="form-label"
                    >选择服务 <span class="text-danger">*</span></label
                  >
                  <div class="list-group">
                    <label
                      v-for="service in services"
                      :key="service.name"
                      class="list-group-item list-group-item-action"
                      :class="{
                        active: buildConfig.selectedService === service.name,
                      }"
                      style="cursor: pointer"
                    >
                      <div class="d-flex align-items-center">
                        <input
                          type="radio"
                          :value="service.name"
                          v-model="buildConfig.selectedService"
                          class="form-check-input me-3"
                          @change="onSingleServiceSelected"
                        />
                        <div class="flex-grow-1">
                          <div class="fw-bold">
                            <code>{{ service.name }}</code>
                          </div>
                          <small class="text-muted">
                            <span v-if="service.port"
                              >端口: {{ service.port }}</span
                            >
                            <span v-if="service.port && service.user"> | </span>
                            <span v-if="service.user"
                              >用户: {{ service.user }}</span
                            >
                          </small>
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                <div v-if="buildConfig.selectedService" class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">
                      镜像前缀 <span class="text-danger">*</span>
                    </label>
                    <select
                      v-model="buildConfig.imagePrefix"
                      class="form-select mb-2"
                      @change="onImagePrefixChange"
                    >
                      <option value="">-- 选择仓库或手动输入 --</option>
                      <option
                        v-for="reg in registries"
                        :key="reg.name"
                        :value="reg.registry_prefix || reg.registry"
                      >
                        {{ reg.name }} ({{
                          reg.registry_prefix || reg.registry
                        }})
                      </option>
                    </select>
                    <input
                      v-if="!isRegistrySelected(buildConfig.imagePrefix)"
                      v-model="buildConfig.imagePrefix"
                      type="text"
                      class="form-control mb-2"
                      placeholder="myapp/demo"
                      required
                    />
                    <label class="form-label">
                      完整镜像名 <small class="text-muted">(可编辑)</small>
                    </label>
                    <input
                      :value="getSingleServiceImageNameDisplay()"
                      @input="onSingleServiceImageNameInput($event)"
                      type="text"
                      class="form-control"
                    />
                    <div class="form-text small text-muted">
                      <i class="fas fa-info-circle"></i>
                      格式: 前缀/服务名 或 完整镜像名
                      <button
                        v-if="buildConfig.customImageName"
                        type="button"
                        class="btn btn-link btn-sm p-0 ms-2"
                        style="font-size: 0.75rem; vertical-align: baseline"
                        @click="buildConfig.customImageName = ''"
                        title="恢复默认"
                      >
                        <i class="fas fa-undo"></i> 恢复默认
                      </button>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">标签</label>
                    <input
                      v-model="buildConfig.tag"
                      type="text"
                      class="form-control"
                      placeholder="latest"
                    />
                  </div>
                </div>

                <div v-if="buildConfig.selectedService" class="mt-3">
                  <div class="form-check">
                    <input
                      v-model="buildConfig.push"
                      type="checkbox"
                      class="form-check-input"
                      id="pushImageSingle"
                    />
                    <label class="form-check-label" for="pushImageSingle">
                      <i class="fas fa-cloud-upload-alt"></i> 构建后推送到仓库
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 多服务推送模式 -->
          <div v-else class="mb-3">
            <div class="card border-info">
              <div
                class="card-header bg-info bg-opacity-10 d-flex justify-content-between align-items-center"
              >
                <div>
                  <i class="fas fa-server"></i> 服务选择
                  <span class="badge bg-info ms-2"
                    >{{ services.length }} 个服务</span
                  >
                  <small class="text-muted ms-2">
                    <i
                      v-if="buildConfig.useProjectDockerfile"
                      class="fas fa-file-code"
                    ></i>
                    <i v-else class="fas fa-layer-group"></i>
                    {{
                      buildConfig.useProjectDockerfile
                        ? "来自项目 Dockerfile"
                        : "来自模板"
                    }}
                  </small>
                </div>
                <div>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-info me-2"
                    @click="selectAllServices"
                  >
                    <i class="fas fa-check-square"></i> 全选
                  </button>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-info"
                    @click="deselectAllServices"
                  >
                    <i class="fas fa-square"></i> 全不选
                  </button>
                </div>
              </div>
              <div class="card-body">
                <!-- 全局模板参数 -->
                <div
                  v-if="templateParams.length > 0"
                  class="mb-3 p-3 bg-light rounded"
                >
                  <h6 class="mb-3"><i class="fas fa-cog"></i> 全局模板参数</h6>
                  <div class="row g-3">
                    <div
                      v-for="param in templateParams"
                      :key="param.name"
                      class="col-md-6"
                    >
                      <label class="form-label">
                        {{ param.description || param.name }}
                        <span v-if="param.required" class="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        v-model="buildConfig.templateParams[param.name]"
                        :placeholder="param.default || ''"
                        class="form-control"
                        :required="param.required"
                      />
                    </div>
                  </div>
                </div>

                <!-- 批量操作（快速设置多个服务） -->
                <div
                  v-if="selectedServices.length > 0"
                  class="mb-3 p-3 bg-light rounded"
                >
                  <h6 class="mb-3">
                    <i class="fas fa-magic"></i> 批量操作（快速设置已选中的
                    {{ selectedServices.length }} 个服务）
                  </h6>
                  <div class="row g-3">
                    <div class="col-md-4">
                      <label class="form-label">批量设置镜像前缀</label>
                      <select
                        v-model="batchImagePrefix"
                        class="form-select form-select-sm mb-2"
                        @change="onBatchPrefixChange"
                      >
                        <option value="">-- 选择仓库或手动输入 --</option>
                        <option
                          v-for="reg in registries"
                          :key="reg.name"
                          :value="reg.registry_prefix || reg.registry"
                        >
                          {{ reg.name }} ({{
                            reg.registry_prefix || reg.registry
                          }})
                        </option>
                      </select>
                      <div class="input-group input-group-sm">
                        <input
                          v-if="!isRegistrySelected(batchImagePrefix)"
                          v-model="batchImagePrefix"
                          type="text"
                          class="form-control"
                          placeholder="myapp/demo"
                        />
                        <button
                          class="btn btn-outline-secondary"
                          type="button"
                          @click="batchSetImagePrefix"
                          :disabled="!batchImagePrefix.trim()"
                        >
                          <i class="fas fa-check"></i> 应用
                        </button>
                      </div>
                      <small class="text-muted d-block mt-1">
                        <i class="fas fa-info-circle"></i>
                        前缀会自动与服务名称拼接
                      </small>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">批量设置标签</label>
                      <div class="input-group input-group-sm">
                        <input
                          v-model="batchTag"
                          type="text"
                          class="form-control"
                          placeholder="latest"
                        />
                        <button
                          class="btn btn-outline-secondary"
                          type="button"
                          @click="batchSetTag"
                          :disabled="!batchTag.trim()"
                        >
                          <i class="fas fa-check"></i> 应用
                        </button>
                      </div>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">批量设置推送</label>
                      <div class="btn-group w-100" role="group">
                        <button
                          class="btn btn-sm btn-outline-success"
                          type="button"
                          @click="batchSetPush(true)"
                        >
                          <i class="fas fa-check"></i> 全部推送
                        </button>
                        <button
                          class="btn btn-sm btn-outline-danger"
                          type="button"
                          @click="batchSetPush(false)"
                        >
                          <i class="fas fa-times"></i> 全部不推送
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 服务卡片列表 -->
                <div class="row g-3">
                  <div
                    v-for="service in services"
                    :key="service.name"
                    class="col-md-6 col-lg-4"
                  >
                    <div
                      class="card h-100"
                      :class="{
                        'border-success': selectedServices.includes(
                          service.name
                        ),
                        'border-secondary': !selectedServices.includes(
                          service.name
                        ),
                      }"
                    >
                      <div
                        class="card-header d-flex justify-content-between align-items-center"
                      >
                        <div class="form-check mb-0">
                          <input
                            type="checkbox"
                            :value="service.name"
                            v-model="selectedServices"
                            class="form-check-input"
                            @change="onServiceSelectionChange(service.name)"
                            :id="`service-${service.name}`"
                          />
                          <label
                            class="form-check-label fw-bold mb-0"
                            :for="`service-${service.name}`"
                            style="cursor: pointer"
                          >
                            <code>{{ service.name }}</code>
                          </label>
                        </div>
                        <span
                          v-if="selectedServices.includes(service.name)"
                          class="badge bg-success"
                        >
                          <i class="fas fa-check"></i> 已选择
                        </span>
                      </div>
                      <div class="card-body">
                        <!-- 服务参数信息已移除，只显示可配置项 -->

                        <!-- 服务模板参数（如果有） -->
                        <div
                          v-if="
                            service.template_params &&
                            service.template_params.length > 0
                          "
                          class="mb-3"
                        >
                          <h6 class="small mb-2">
                            <i class="fas fa-cog"></i> 模板参数
                          </h6>
                          <div
                            v-for="param in service.template_params"
                            :key="param.name"
                            class="mb-2"
                          >
                            <label class="form-label small mb-1">
                              {{ param.description || param.name }}
                              <span v-if="param.required" class="text-danger"
                                >*</span
                              >
                            </label>
                            <input
                              type="text"
                              :value="
                                getServiceTemplateParam(
                                  service.name,
                                  param.name
                                )
                              "
                              @input="
                                setServiceTemplateParam(
                                  service.name,
                                  param.name,
                                  $event.target.value
                                )
                              "
                              :placeholder="param.default || ''"
                              class="form-control form-control-sm"
                              :required="param.required"
                            />
                          </div>
                        </div>

                        <!-- 构建配置（仅 Git 数据源且已选择的服务） -->
                        <div
                          v-if="
                            buildConfig.sourceType === 'git' &&
                            selectedServices.includes(service.name)
                          "
                          class="border-top pt-3"
                        >
                          <!-- 镜像名：每个服务可以自定义，如果为空则使用全局前缀+服务名 -->
                          <div class="mb-2">
                            <label class="form-label small mb-1">
                              镜像名
                              <span class="text-muted small"
                                >(可选，默认使用全局前缀)</span
                              >
                            </label>
                            <div class="d-flex align-items-center gap-1">
                              <input
                                type="text"
                                v-model="
                                  getServiceConfig(service.name).customImageName
                                "
                                :placeholder="
                                  getServiceDefaultImageName(service.name)
                                "
                                class="form-control form-control-sm flex-grow-1"
                                @blur="onServiceImageNameBlur(service.name)"
                              />
                              <button
                                v-if="
                                  getServiceConfig(service.name).customImageName
                                "
                                type="button"
                                class="btn btn-link btn-sm p-0"
                                style="font-size: 0.75rem; flex-shrink: 0"
                                @click="resetServiceImageName(service.name)"
                                title="恢复默认"
                              >
                                <i class="fas fa-undo"></i>
                              </button>
                            </div>
                          </div>
                          <!-- 是否推送：每个服务单独配置 -->
                          <div class="form-check">
                            <input
                              type="checkbox"
                              v-model="getServiceConfig(service.name).push"
                              class="form-check-input"
                              :id="`push-${service.name}`"
                            />
                            <label
                              class="form-check-label small"
                              :for="`push-${service.name}`"
                            >
                              构建后推送
                            </label>
                          </div>
                        </div>
                        <div
                          v-else-if="buildConfig.sourceType === 'git'"
                          class="border-top pt-3 text-muted small text-center"
                        >
                          <i class="fas fa-info-circle"></i>
                          请先选择此服务以配置构建选项
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  v-if="selectedServices.length > 0"
                  class="mt-3 text-muted small"
                >
                  <i class="fas fa-info-circle"></i>
                  已选择 {{ selectedServices.length }} 个服务进行构建
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 镜像配置（单应用模式或文件上传模式，排除单服务推送模式） -->
        <div
          v-if="
            (services.length === 0 || buildConfig.sourceType === 'file') &&
            !(
              buildConfig.pushMode === 'single' &&
              !buildConfig.useProjectDockerfile &&
              buildConfig.sourceType === 'git'
            )
          "
          class="row g-3 mb-3"
        >
          <div class="col-md-6">
            <label class="form-label">
              镜像名称 <span class="text-danger">*</span>
            </label>
            <input
              v-model="buildConfig.imageName"
              type="text"
              class="form-control"
              placeholder="myapp/demo"
              required
            />
          </div>
          <div class="col-md-6">
            <label class="form-label">标签</label>
            <input
              v-model="buildConfig.tag"
              type="text"
              class="form-control"
              placeholder="latest"
            />
          </div>
        </div>

        <!-- 推送选项（单应用模式或文件上传模式，排除单服务推送模式） -->
        <div
          v-if="
            (services.length === 0 || buildConfig.sourceType === 'file') &&
            !(
              buildConfig.pushMode === 'single' &&
              !buildConfig.useProjectDockerfile &&
              buildConfig.sourceType === 'git'
            )
          "
          class="mb-3"
        >
          <div class="form-check">
            <input
              v-model="buildConfig.push"
              type="checkbox"
              class="form-check-input"
              id="pushImage"
            />
            <label class="form-check-label" for="pushImage">
              <i class="fas fa-cloud-upload-alt"></i> 构建后推送到仓库
            </label>
          </div>
        </div>

        <div class="d-flex justify-content-between mt-4">
          <button class="btn btn-outline-secondary" @click="prevStep">
            <i class="fas fa-arrow-left me-1"></i> 上一步
          </button>
          <button
            class="btn btn-primary"
            @click="nextStep"
            :disabled="
              !buildConfig.imageName ||
              (services.length > 0 &&
                buildConfig.pushMode === 'single' &&
                !buildConfig.selectedService) ||
              (services.length > 0 &&
                buildConfig.pushMode === 'multi' &&
                selectedServices.length === 0)
            "
          >
            下一步 <i class="fas fa-arrow-right ms-1"></i>
          </button>
        </div>
      </div>

      <!-- 步骤5: 选择资源包 -->
      <div v-if="currentStep === 5" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-archive text-primary"></i> 步骤 5：选择资源包
        </h5>

        <div class="mb-3">
          <label class="form-label">
            <i class="fas fa-info-circle text-info"></i> 资源包说明
          </label>
          <div class="alert alert-info small mb-3">
            <p class="mb-1">
              <strong
                >资源包用于在构建时添加配置文件、密钥、证书等不能公开的内容。</strong
              >
            </p>
            <p class="mb-0">
              选择资源包后，它们将被复制到构建上下文的指定目录中，可以在
              Dockerfile 中使用。
            </p>
          </div>
        </div>

        <div class="mb-3">
          <label class="form-label">选择资源包</label>
          <div v-if="loadingPackages" class="text-center py-2">
            <span class="spinner-border spinner-border-sm me-2"></span>
            加载资源包列表...
          </div>
          <div v-else-if="packages.length === 0" class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            暂无资源包，请先在"资源包"标签页上传资源包
          </div>
          <div v-else class="table-responsive">
            <table class="table table-sm table-hover">
              <thead>
                <tr>
                  <th style="width: 40px">
                    <input
                      type="checkbox"
                      @change="toggleAllPackages"
                      :checked="
                        selectedResourcePackages.length === packages.length &&
                        packages.length > 0
                      "
                    />
                  </th>
                  <th>名称</th>
                  <th>描述</th>
                  <th>大小</th>
                  <th>目标路径</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pkg in packages" :key="pkg.package_id">
                  <td>
                    <input
                      type="checkbox"
                      :value="pkg.package_id"
                      v-model="selectedResourcePackages"
                    />
                  </td>
                  <td>
                    <strong>{{ pkg.name }}</strong>
                    <i
                      v-if="pkg.extracted"
                      class="fas fa-folder-open text-info ms-1"
                      title="已解压"
                    ></i>
                  </td>
                  <td>
                    <span class="text-muted small">{{
                      pkg.description || "无描述"
                    }}</span>
                  </td>
                  <td>{{ formatBytes(pkg.size) }}</td>
                  <td>
                    <div class="input-group input-group-sm">
                      <span
                        class="input-group-text bg-light text-muted"
                        style="font-size: 0.75rem"
                      >
                        <i class="fas fa-folder"></i>
                      </span>
                      <input
                        type="text"
                        class="form-control form-control-sm"
                        :value="
                          resourcePackagePaths[pkg.package_id] ||
                          getDefaultResourcePath(pkg)
                        "
                        @input="
                          updateResourcePackagePath(
                            pkg.package_id,
                            $event.target.value
                          )
                        "
                      />
                    </div>
                    <small class="text-muted d-block mt-1">
                      <i class="fas fa-info-circle"></i>
                      相对路径，如：<code>test/b.txt</code> 或
                      <code>config/app.conf</code>
                    </small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div
          v-if="selectedResourcePackages.length > 0"
          class="alert alert-success"
        >
          <i class="fas fa-check-circle"></i> 已选择
          <strong>{{ selectedResourcePackages.length }}</strong> 个资源包
        </div>

        <div class="d-flex justify-content-between mt-4">
          <button class="btn btn-outline-secondary" @click="prevStep">
            <i class="fas fa-arrow-left me-1"></i> 上一步
          </button>
          <button class="btn btn-primary" @click="nextStep">
            下一步 <i class="fas fa-arrow-right ms-1"></i>
          </button>
        </div>
      </div>

      <!-- 步骤6: 开始构建 -->
      <div v-if="currentStep === 6" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-play-circle text-primary"></i> 步骤 6：开始构建
        </h5>

        <!-- 构建配置摘要 -->
        <div class="card mb-3 border-primary">
          <div class="card-header bg-primary text-white">
            <h6 class="mb-0">
              <i class="fas fa-list-check me-2"></i> 构建配置摘要
            </h6>
          </div>
          <div class="card-body">
            <div class="row g-3">
              <!-- 数据源信息 -->
              <div class="col-md-6">
                <div class="border rounded p-3 h-100">
                  <h6 class="text-primary mb-3">
                    <i class="fas fa-database me-2"></i> 数据源信息
                  </h6>
                  <div class="mb-2">
                    <span class="badge bg-info me-2">类型</span>
                    <strong>{{
                      buildConfig.sourceType === "file"
                        ? "文件上传"
                        : "Git 数据源"
                    }}</strong>
                  </div>
                  <div v-if="buildConfig.sourceType === 'file'" class="mb-2">
                    <span class="badge bg-info me-2">文件</span>
                    <code class="small">{{ buildConfig.file?.name }}</code>
                    <span class="text-muted small ms-2"
                      >({{ formatFileSize(buildConfig.file?.size) }})</span
                    >
                  </div>
                  <div v-if="buildConfig.sourceType === 'git'">
                    <div class="mb-2">
                      <span class="badge bg-info me-2">数据源</span>
                      <strong>{{ getSourceName(buildConfig.sourceId) }}</strong>
                    </div>
                    <div>
                      <span class="badge bg-info me-2">分支</span>
                      <code>{{
                        buildConfig.branch ||
                        branchesAndTags.default_branch ||
                        "默认分支"
                      }}</code>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 构建配置 -->
              <div class="col-md-6">
                <div class="border rounded p-3 h-100">
                  <h6 class="text-success mb-3">
                    <i class="fas fa-cogs me-2"></i> 构建配置
                  </h6>
                  <div class="mb-2">
                    <span class="badge bg-success me-2">项目类型</span>
                    <strong>{{
                      getProjectTypeLabel(buildConfig.projectType)
                    }}</strong>
                  </div>
                  <div class="mb-2">
                    <span class="badge bg-success me-2">模板</span>
                    <code>{{
                      buildConfig.useProjectDockerfile
                        ? "项目 Dockerfile"
                        : buildConfig.template || "未选择"
                    }}</code>
                  </div>
                  <div v-if="services.length > 0" class="mb-2">
                    <span class="badge bg-success me-2">服务</span>
                    <span
                      v-if="
                        buildConfig.pushMode === 'single' &&
                        buildConfig.selectedService
                      "
                    >
                      <code>{{ buildConfig.selectedService }}</code>
                      <span class="badge bg-warning text-dark ms-2"
                        >单服务推送</span
                      >
                    </span>
                    <span v-else-if="selectedServices.length > 0">
                      <span class="badge bg-primary"
                        >{{ selectedServices.length }}个服务</span
                      >
                      <span class="badge bg-warning text-dark ms-2"
                        >多服务推送</span
                      >
                      <div class="mt-2">
                        <code class="small">{{
                          selectedServices.join(", ")
                        }}</code>
                      </div>
                    </span>
                    <span v-else class="text-muted">未选择</span>
                  </div>
                </div>
              </div>

              <!-- 镜像配置 -->
              <div class="col-md-6">
                <div class="border rounded p-3 h-100">
                  <h6 class="text-warning mb-3">
                    <i class="fas fa-docker me-2"></i> 镜像配置
                  </h6>
                  <div
                    v-if="
                      services.length > 0 && buildConfig.pushMode === 'multi'
                    "
                  >
                    <div
                      v-for="serviceName in selectedServices"
                      :key="serviceName"
                      class="mb-2"
                    >
                      <div class="d-flex align-items-center mb-1">
                        <span class="badge bg-warning text-dark me-2">{{
                          serviceName
                        }}</span>
                        <code class="small">
                          {{
                            getServiceConfig(serviceName).customImageName ||
                            getServiceDefaultImageName(serviceName)
                          }}:{{ buildConfig.tag || "latest" }}
                        </code>
                      </div>
                      <div class="ms-4 small text-muted">
                        <span
                          v-if="getServiceConfig(serviceName).push"
                          class="badge bg-success me-1"
                          >推送</span
                        >
                        <span v-else class="badge bg-secondary me-1"
                          >不推送</span
                        >
                        <span
                          v-if="getServiceConfig(serviceName).registry"
                          class="badge bg-info"
                        >
                          仓库: {{ getServiceConfig(serviceName).registry }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div v-else>
                    <div class="mb-2">
                      <span class="badge bg-warning text-dark me-2"
                        >镜像名</span
                      >
                      <code>{{
                        buildConfig.imageName ||
                        (buildConfig.pushMode === "single" &&
                        buildConfig.selectedService
                          ? `${buildConfig.imagePrefix || "myapp/demo"}/${
                              buildConfig.selectedService
                            }`
                          : "myapp/demo")
                      }}</code>
                    </div>
                    <div>
                      <span class="badge bg-warning text-dark me-2">标签</span>
                      <code>{{ buildConfig.tag || "latest" }}</code>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 推送配置 -->
              <div class="col-md-6">
                <div class="border rounded p-3 h-100">
                  <h6 class="text-danger mb-3">
                    <i class="fas fa-cloud-upload-alt me-2"></i> 推送配置
                  </h6>
                  <div
                    v-if="
                      services.length > 0 && buildConfig.pushMode === 'multi'
                    "
                  >
                    <div class="mb-2">
                      <span class="badge bg-danger me-2">推送模式</span>
                      <strong>多服务推送</strong>
                    </div>
                    <div>
                      <span class="badge bg-danger me-2">推送服务数</span>
                      <strong
                        >{{
                          selectedServices.filter(
                            (s) => getServiceConfig(s).push
                          ).length
                        }}/{{ selectedServices.length }}</strong
                      >
                    </div>
                  </div>
                  <div v-else>
                    <div>
                      <span class="badge bg-danger me-2">推送</span>
                      <span
                        :class="
                          buildConfig.push
                            ? 'badge bg-success'
                            : 'badge bg-secondary'
                        "
                      >
                        {{ buildConfig.push ? "是" : "否" }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Docker 构建配置 -->
              <div class="col-md-12">
                <div class="border rounded p-3">
                  <h6 class="text-secondary mb-3">
                    <i class="fas fa-server me-2"></i> Docker 构建配置
                  </h6>
                  <div class="row g-3">
                    <div class="col-md-4">
                      <div class="mb-2">
                        <span class="badge bg-secondary me-2">构建模式</span>
                        <strong>{{
                          dockerInfo ? getBuildModeLabel() : "加载中..."
                        }}</strong>
                      </div>
                      <div
                        v-if="dockerInfo && dockerInfo.buildx_available"
                        class="mb-2"
                      >
                        <span class="badge bg-success me-2">
                          <i class="fas fa-check"></i> Buildx 支持
                        </span>
                        <code class="small" v-if="dockerInfo.buildx_version">{{
                          dockerInfo.buildx_version
                        }}</code>
                      </div>
                      <div v-else-if="dockerInfo" class="mb-2">
                        <span class="badge bg-warning text-dark me-2">
                          <i class="fas fa-exclamation-triangle"></i> Buildx
                          不可用
                        </span>
                      </div>
                    </div>
                    <div
                      class="col-md-4"
                      v-if="dockerInfo && dockerInfo.version"
                    >
                      <div class="mb-2">
                        <span class="badge bg-info me-2">Docker 版本</span>
                        <code class="small">{{ dockerInfo.version }}</code>
                      </div>
                      <div v-if="dockerInfo.api_version" class="mb-2">
                        <span class="badge bg-info me-2">API 版本</span>
                        <code class="small">{{ dockerInfo.api_version }}</code>
                      </div>
                    </div>
                    <div
                      class="col-md-4"
                      v-if="
                        dockerInfo &&
                        dockerInfo.builder_type === 'remote' &&
                        dockerInfo.remote_host
                      "
                    >
                      <div class="mb-2">
                        <span class="badge bg-primary me-2">远程主机</span>
                        <code class="small">{{ dockerInfo.remote_host }}</code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 模板参数 -->
              <div
                v-if="
                  templateParams.length > 0 ||
                  Object.keys(buildConfig.serviceTemplateParams).length > 0
                "
                class="col-12"
              >
                <div class="border rounded p-3">
                  <h6 class="text-info mb-3">
                    <i class="fas fa-sliders-h me-2"></i> 模板参数
                  </h6>
                  <div v-if="templateParams.length > 0" class="mb-3">
                    <div class="small text-muted mb-2">全局参数:</div>
                    <div class="d-flex flex-wrap gap-2">
                      <span
                        v-for="param in templateParams"
                        :key="param.name"
                        class="badge bg-info"
                      >
                        {{ param.description || param.name }}:
                        <code class="text-white">{{
                          buildConfig.templateParams[param.name] ||
                          param.default ||
                          "(空)"
                        }}</code>
                      </span>
                    </div>
                  </div>
                  <div
                    v-if="
                      Object.keys(buildConfig.serviceTemplateParams).length > 0
                    "
                  >
                    <div class="small text-muted mb-2">服务参数:</div>
                    <div
                      v-for="(
                        params, serviceName
                      ) in buildConfig.serviceTemplateParams"
                      :key="serviceName"
                      class="mb-2"
                    >
                      <span class="badge bg-secondary me-2">{{
                        serviceName
                      }}</span>
                      <span
                        v-for="(value, paramName) in params"
                        :key="paramName"
                        class="badge bg-info me-1"
                      >
                        {{ paramName }}:
                        <code class="text-white">{{ value || "(空)" }}</code>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 资源包 -->
              <div
                v-if="
                  buildConfig.resourcePackages &&
                  buildConfig.resourcePackages.length > 0
                "
                class="col-12"
              >
                <div class="border rounded p-3">
                  <h6 class="text-secondary mb-3">
                    <i class="fas fa-archive me-2"></i> 资源包
                  </h6>
                  <div class="table-responsive">
                    <table class="table table-sm table-borderless mb-0">
                      <thead>
                        <tr>
                          <th style="width: 30%">资源包名称</th>
                          <th style="width: 70%">目标路径</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="pkgConfig in buildConfig.resourcePackages"
                          :key="pkgConfig.package_id"
                        >
                          <td>
                            <strong>{{
                              packages.find(
                                (p) => p.package_id === pkgConfig.package_id
                              )?.name || pkgConfig.package_id
                            }}</strong>
                          </td>
                          <td>
                            <code class="text-primary">{{
                              pkgConfig.target_path ||
                              pkgConfig.target_dir ||
                              "resources"
                            }}</code>
                            <small class="text-muted ms-2"
                              >(相对构建上下文)</small
                            >
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="d-flex justify-content-between mt-4">
          <button
            class="btn btn-outline-secondary"
            @click="prevStep"
            :disabled="building"
          >
            <i class="fas fa-arrow-left me-1"></i> 上一步
          </button>
          <button
            class="btn btn-success btn-lg"
            @click="startBuild"
            :disabled="building"
          >
            <i class="fas fa-play"></i>
            {{ building ? "构建中..." : "开始构建" }}
            <span
              v-if="building"
              class="spinner-border spinner-border-sm ms-2"
            ></span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, ref } from "vue";

const currentStep = ref(1);
const building = ref(false);

// 构建配置
const buildConfig = ref({
  sourceType: "git", // 'file' 或 'git'
  file: null,
  sourceId: "",
  branch: "",
  projectType: "jar",
  template: "",
  useProjectDockerfile: true,
  dockerfileName: "Dockerfile",
  imageName: "myapp/demo",
  tag: "latest",
  push: false,
  pushMode: "multi", // 推送模式：'single' 单一推送，'multi' 多阶段推送
  imagePrefix: "", // 镜像前缀（可以选择仓库或手动输入）
  customImageName: "", // 自定义完整镜像名（单服务推送模式，如果为空则使用拼接结果）
  templateParams: {},
  selectedServices: [],
  selectedService: "", // 单服务推送模式选中的服务（单选）
  servicePushConfig: {},
  serviceTemplateParams: {}, // 每个服务的模板参数 {serviceName: {paramName: value}}
});

// 数据源相关
const gitSources = ref([]);
const repoVerified = ref(false);
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null,
});
const availableDockerfiles = ref([]);

// 模板相关
const templates = ref([]);
const templateSearch = ref("");
const templateParams = ref([]);
const services = ref([]);
const selectedServices = ref([]);
const servicePushConfig = ref({}); // 每个服务的推送配置
const parsingServices = ref(false);
const servicesError = ref("");
const registries = ref([]); // 仓库列表
const batchImagePrefix = ref(""); // 批量设置镜像前缀
const batchTag = ref(""); // 批量设置标签
// 批量设置相关变量已移除，使用全局配置

// 资源包相关
const packages = ref([]);
const loadingPackages = ref(false);
const selectedResourcePackages = ref([]); // 选中的资源包ID列表
const resourcePackagePaths = ref({}); // 资源包路径映射 {package_id: target_dir}

// Docker 信息相关
const dockerInfo = ref(null);

const projectTypes = computed(() => {
  const types = new Set();
  templates.value.forEach((t) => types.add(t.project_type));

  const labelMap = {
    jar: "Java 应用（JAR）",
    nodejs: "Node.js 应用",
    python: "Python 应用",
    go: "Go 应用",
    rust: "Rust 应用",
  };

  const orderMap = {
    jar: 1,
    nodejs: 2,
    python: 3,
    rust: 4,
    go: 5,
  };

  const result = [];
  types.forEach((type) => {
    result.push({
      value: type,
      label:
        labelMap[type] ||
        `${type.charAt(0).toUpperCase()}${type.slice(1)} 应用`,
      order: orderMap[type] || 999,
    });
  });

  if (result.length === 0) {
    return [
      { value: "jar", label: "Java 应用（JAR）", order: 1 },
      { value: "nodejs", label: "Node.js 应用", order: 2 },
      { value: "python", label: "Python 应用", order: 3 },
      { value: "rust", label: "Rust 应用", order: 4 },
      { value: "go", label: "Go 应用", order: 5 },
    ];
  }

  return result.sort((a, b) => a.order - b.order);
});

const filteredTemplates = computed(() => {
  let list = templates.value.filter(
    (t) => t.project_type === buildConfig.value.projectType
  );
  if (templateSearch.value) {
    const kw = templateSearch.value.toLowerCase();
    list = list.filter((t) => t.name.toLowerCase().includes(kw));
  }
  return list;
});

const fileAccept = computed(() => {
  if (buildConfig.value.projectType === "jar") {
    return ".jar,.zip,.tar,.tar.gz,.tgz";
  }
  return ".zip,.tar,.tar.gz,.tgz";
});

const canProceedStep1 = computed(() => {
  if (buildConfig.value.sourceType === "file") {
    return buildConfig.value.file !== null;
  } else {
    return buildConfig.value.sourceId !== "" && repoVerified.value;
  }
});

// 步骤导航
function nextStep() {
  if (currentStep.value < 6) {
    currentStep.value++;

    // 如果是文件上传模式，跳过步骤2（分支确认）
    if (currentStep.value === 2 && buildConfig.value.sourceType === "file") {
      currentStep.value = 3;
    }

    // 步骤3完成后，自动分析模板
    if (currentStep.value === 4) {
      analyzeTemplate();
    }

    // 步骤4完成后，进入步骤5（选择资源包）
    if (currentStep.value === 5) {
      loadResourcePackages();
    }

    // 步骤5完成后，进入步骤6（开始构建）
    if (currentStep.value === 6) {
      // 保存资源包配置
      buildConfig.value.resourcePackages = selectedResourcePackages.value.map(
        (packageId) => {
          const pkg = packages.value.find((p) => p.package_id === packageId);
          // 如果用户没有输入路径，使用默认值（根目录下的文件名）
          const targetPath =
            resourcePackagePaths.value[packageId] ||
            getDefaultResourcePath(pkg);
          return {
            package_id: packageId,
            target_path: targetPath, // 使用 target_path 替代 target_dir，支持完整路径
          };
        }
      );
    }
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--;
  }
}

// 文件处理
function handleFileChange(e) {
  buildConfig.value.file = e.target.files[0];
  if (buildConfig.value.file) {
    // 自动建议镜像名
    const fileName = buildConfig.value.file.name.replace(/\.[^/.]+$/, "");
    buildConfig.value.imageName = fileName
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "-");
    // 文件上传模式不支持项目 Dockerfile
    buildConfig.value.useProjectDockerfile = false;
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

// Git 数据源处理
async function loadGitSources() {
  try {
    const res = await axios.get("/api/git-sources");
    gitSources.value = res.data.sources || [];
  } catch (error) {
    console.error("加载数据源列表失败:", error);
  }
}

async function onSourceSelected() {
  if (!buildConfig.value.sourceId) {
    repoVerified.value = false;
    branchesAndTags.value = { branches: [], tags: [], default_branch: null };
    buildConfig.value.branch = "";
    return;
  }

  const source = gitSources.value.find(
    (s) => s.source_id === buildConfig.value.sourceId
  );
  if (source) {
    branchesAndTags.value = {
      branches: source.branches || [],
      tags: source.tags || [],
      default_branch: source.default_branch || null,
    };
    repoVerified.value = true;
    buildConfig.value.branch = source.default_branch || "";
  }
}

function onBranchChanged() {
  // 分支变化时的处理
}

function formatGitUrl(url) {
  if (!url) return "";
  return url.replace("https://", "").replace("http://", "").replace(".git", "");
}

function getSourceName(sourceId) {
  const source = gitSources.value.find((s) => s.source_id === sourceId);
  return source ? source.name : "";
}

// 获取服务的参数（排除 name，返回所有动态参数）
function getServiceParams(service) {
  const params = {};
  Object.keys(service).forEach((key) => {
    if (
      key !== "name" &&
      service[key] !== null &&
      service[key] !== undefined &&
      service[key] !== ""
    ) {
      params[key] = service[key];
    }
  });
  return params;
}

// 获取参数的中文标签
function getParamLabel(key) {
  const labelMap = {
    port: "端口",
    user: "用户",
    workdir: "工作目录",
    env: "环境变量",
    cmd: "启动命令",
    entrypoint: "入口点",
    args: "构建参数",
  };
  return labelMap[key] || key;
}

// 镜像前缀选择变化
function onImagePrefixChange() {
  // 选择仓库时自动更新
  // 如果单服务推送模式且没有自定义镜像名，自动更新默认值
  if (
    buildConfig.value.pushMode === "single" &&
    buildConfig.value.selectedService
  ) {
    if (
      !buildConfig.value.customImageName ||
      !buildConfig.value.customImageName.trim()
    ) {
      buildConfig.value.customImageName = "";
    }
  }
  // 多服务推送模式：更新所有已选服务的默认值
  if (buildConfig.value.pushMode === "multi") {
    selectedServices.value.forEach((serviceName) => {
      const config = getServiceConfig(serviceName);
      if (!config.customImageName || !config.customImageName.trim()) {
        config.imagePrefix =
          buildConfig.value.imagePrefix || getDefaultImagePrefix();
      }
    });
  }
}

// 模板处理
async function loadTemplates() {
  try {
    const res = await axios.get("/api/templates");
    templates.value = res.data.items || [];
    if (filteredTemplates.value.length > 0) {
      buildConfig.value.template = filteredTemplates.value[0].name;
    }
  } catch (error) {
    console.error("加载模板失败:", error);
  }
}

function changeProjectType(type) {
  buildConfig.value.projectType = type;
  templateSearch.value = "";
  if (filteredTemplates.value.length > 0) {
    buildConfig.value.template = filteredTemplates.value[0].name;
    loadTemplateParams();
  }
}

function getProjectTypeIcon(type) {
  const iconMap = {
    jar: "fab fa-java",
    nodejs: "fab fa-node-js",
    python: "fab fa-python",
    go: "fas fa-code",
    rust: "fas fa-cog",
  };
  return iconMap[type] || "fas fa-cube";
}

function getProjectTypeLabel(type) {
  const labelMap = {
    jar: "Java",
    nodejs: "Node.js",
    python: "Python",
    go: "Go",
    rust: "Rust",
  };
  return labelMap[type] || type;
}

async function loadTemplateParams() {
  templateParams.value = [];
  buildConfig.value.templateParams = {};

  if (buildConfig.value.useProjectDockerfile) {
    return;
  }

  if (!buildConfig.value.template || !buildConfig.value.projectType) {
    return;
  }

  try {
    const res = await axios.get("/api/template-params", {
      params: {
        template: buildConfig.value.template,
        project_type: buildConfig.value.projectType,
      },
    });

    templateParams.value = res.data.params || [];
    templateParams.value.forEach((param) => {
      if (param.default) {
        buildConfig.value.templateParams[param.name] = param.default;
      }
    });
  } catch (error) {
    console.error("加载模板参数失败:", error);
  }
}

function onUseProjectDockerfileChange() {
  if (!buildConfig.value.useProjectDockerfile) {
    loadTemplateParams();
  } else {
    templateParams.value = [];
    buildConfig.value.templateParams = {};
  }
}

// 分析模板，判断单应用/多服务
async function analyzeTemplate() {
  parsingServices.value = true;
  servicesError.value = "";
  services.value = [];
  selectedServices.value = [];
  buildConfig.value.selectedService = "";
  servicePushConfig.value = {};

  try {
    // 如果是文件上传，不需要分析服务，默认为单服务推送
    if (buildConfig.value.sourceType === "file") {
      services.value = [];
      selectedServices.value = [];
      buildConfig.value.selectedService = "";
      servicePushConfig.value = {};
      buildConfig.value.pushMode = "single";
      parsingServices.value = false;
      return;
    }

    // 如果使用项目 Dockerfile，解析项目 Dockerfile
    if (buildConfig.value.useProjectDockerfile) {
      await parseDockerfileServices();
    } else {
      // 解析模板服务
      await parseTemplateServices();
    }
  } catch (error) {
    console.error("分析模板失败:", error);
    servicesError.value = error.response?.data?.detail || "分析模板失败";
  } finally {
    parsingServices.value = false;
  }
}

async function parseDockerfileServices() {
  if (!repoVerified.value || !buildConfig.value.sourceId) {
    services.value = [];
    selectedServices.value = [];
    return;
  }

  try {
    const source = gitSources.value.find(
      (s) => s.source_id === buildConfig.value.sourceId
    );
    if (!source) return;

    const payload = {
      git_url: source.git_url,
      branch: buildConfig.value.branch || undefined,
      dockerfile_name: buildConfig.value.dockerfileName || "Dockerfile",
      source_id: buildConfig.value.sourceId,
    };

    const res = await axios.post("/api/parse-dockerfile-services", payload);

    if (res.data.services && res.data.services.length > 0) {
      services.value = res.data.services;
      // 项目 Dockerfile 模式总是多服务推送
      selectedServices.value = services.value.map((s) => s.name);
      buildConfig.value.selectedService = "";
      // 初始化推送配置（默认都不推送）
      servicePushConfig.value = {};
      services.value.forEach((s) => {
        const config = getServiceConfig(s.name);
        config.push = false;
        config.imagePrefix = getDefaultImagePrefix();
        config.tag = buildConfig.value.tag.trim() || "latest";
        config.registry = "";
      });
    } else {
      services.value = [];
      selectedServices.value = [];
      buildConfig.value.selectedService = "";
      servicePushConfig.value = {};
    }
  } catch (error) {
    console.error("解析 Dockerfile 服务失败:", error);
    servicesError.value =
      error.response?.data?.detail || "解析 Dockerfile 失败";
    services.value = [];
    selectedServices.value = [];
  }
}

async function parseTemplateServices() {
  if (!buildConfig.value.template || !buildConfig.value.projectType) {
    services.value = [];
    selectedServices.value = [];
    return;
  }

  try {
    const res = await axios.get("/api/template-params", {
      params: {
        template: buildConfig.value.template,
        project_type: buildConfig.value.projectType,
      },
    });

    const templateServices = res.data.services || [];
    if (templateServices.length > 0) {
      services.value = templateServices;
      // 根据推送模式初始化选择
      if (buildConfig.value.pushMode === "single") {
        selectedServices.value = [];
        buildConfig.value.selectedService = "";
      } else {
        selectedServices.value = services.value.map((s) => s.name);
      }
      // 初始化推送配置（默认都不推送）
      servicePushConfig.value = {};
      services.value.forEach((s) => {
        const config = getServiceConfig(s.name);
        config.push = false;
        config.imagePrefix = getDefaultImagePrefix();
        config.tag = buildConfig.value.tag.trim() || "latest";
        config.registry = "";
      });
    } else {
      services.value = [];
      selectedServices.value = [];
      buildConfig.value.selectedService = "";
      servicePushConfig.value = {};
    }
  } catch (error) {
    console.error("解析模板服务失败:", error);
    servicesError.value = error.response?.data?.detail || "解析模板失败";
    services.value = [];
    selectedServices.value = [];
  }
}

// 获取服务的配置对象（如果不存在则创建默认配置）
function getServiceConfig(serviceName) {
  if (!servicePushConfig.value[serviceName]) {
    servicePushConfig.value[serviceName] = {
      push: false,
      imagePrefix: "", // 镜像前缀
      customImageName: "", // 自定义完整镜像名（如果为空则使用拼接结果）
      tag: "",
      registry: "",
    };
  }
  return servicePushConfig.value[serviceName];
}

// 获取服务的模板参数值
function getServiceTemplateParam(serviceName, paramName) {
  if (!buildConfig.value.serviceTemplateParams[serviceName]) {
    buildConfig.value.serviceTemplateParams[serviceName] = {};
  }
  return buildConfig.value.serviceTemplateParams[serviceName][paramName] || "";
}

// 设置服务的模板参数值
function setServiceTemplateParam(serviceName, paramName, value) {
  if (!buildConfig.value.serviceTemplateParams[serviceName]) {
    buildConfig.value.serviceTemplateParams[serviceName] = {};
  }
  buildConfig.value.serviceTemplateParams[serviceName][paramName] = value;
}

// 获取默认镜像前缀
function getDefaultImagePrefix() {
  return (
    buildConfig.value.imagePrefix.trim() ||
    buildConfig.value.imageName.trim() ||
    "myapp/demo"
  );
}

// 获取服务的完整镜像名（自定义或前缀 + 服务名称）
function getServiceFullImageName(serviceName) {
  const config = getServiceConfig(serviceName);
  // 如果用户自定义了镜像名，使用自定义的
  if (config.customImageName && config.customImageName.trim()) {
    return config.customImageName.trim();
  }
  // 否则使用前缀+服务名称拼接
  const prefix = config.imagePrefix.trim() || getDefaultImagePrefix();
  return `${prefix}/${serviceName}`;
}

// 获取服务镜像名的默认值（拼接结果，用于占位符）
function getServiceDefaultImageName(serviceName) {
  // 使用全局镜像前缀，而不是每个服务的单独前缀
  const prefix =
    buildConfig.value.imagePrefix.trim() || getDefaultImagePrefix();
  return `${prefix}/${serviceName}`;
}

// 服务镜像名输入框失焦处理
function onServiceImageNameBlur(serviceName) {
  const config = getServiceConfig(serviceName);
  // 如果用户清空了自定义镜像名，确保使用拼接结果
  if (!config.customImageName || !config.customImageName.trim()) {
    config.customImageName = "";
  }
}

// 恢复默认镜像名（使用拼接结果）
function resetServiceImageName(serviceName) {
  const config = getServiceConfig(serviceName);
  config.customImageName = "";
}

// 获取单服务推送模式的镜像名显示值
function getSingleServiceImageNameDisplay() {
  if (
    buildConfig.value.customImageName &&
    buildConfig.value.customImageName.trim()
  ) {
    return buildConfig.value.customImageName.trim();
  }
  const prefix =
    buildConfig.value.imagePrefix ||
    buildConfig.value.imageName ||
    "myapp/demo";
  return `${prefix}/${buildConfig.value.selectedService}`;
}

// 单服务推送模式镜像名输入处理
function onSingleServiceImageNameInput(event) {
  const value = event.target.value.trim();
  const prefix =
    buildConfig.value.imagePrefix ||
    buildConfig.value.imageName ||
    "myapp/demo";
  const defaultName = `${prefix}/${buildConfig.value.selectedService}`;

  // 如果输入的值与默认值相同，清空自定义值（使用默认）
  if (value === defaultName || !value) {
    buildConfig.value.customImageName = "";
  } else {
    // 否则保存为用户自定义值
    buildConfig.value.customImageName = value;
  }
}

// 检查是否是仓库选择
function isRegistrySelected(value) {
  if (!value) return false;
  return registries.value.some(
    (reg) => (reg.registry_prefix || reg.registry) === value
  );
}

// 批量前缀相关函数已移除，使用全局配置

// 规范化服务配置（已简化，使用全局配置）
function normalizeServiceConfig(serviceName) {
  // 不再需要单独设置每个服务的前缀和标签，使用全局配置
}

// 推送模式切换
function onPushModeChange(mode) {
  buildConfig.value.pushMode = mode;
  // 重置选择状态
  if (mode === "single") {
    buildConfig.value.selectedService = "";
    selectedServices.value = [];
  } else {
    buildConfig.value.selectedService = "";
    // 多服务模式默认全选
    selectedServices.value = services.value.map((s) => s.name);
    // 初始化所有服务的配置
    services.value.forEach((service) => {
      normalizeServiceConfig(service.name);
    });
  }
}

// 单服务推送模式：服务选择变化
function onSingleServiceSelected() {
  if (buildConfig.value.selectedService) {
    // 更新 selectedServices 为单选结果
    selectedServices.value = [buildConfig.value.selectedService];
    // 确保镜像前缀有默认值
    if (!buildConfig.value.imagePrefix.trim()) {
      buildConfig.value.imagePrefix =
        buildConfig.value.imageName || "myapp/demo";
    }
    // 如果没有自定义镜像名，清空（使用默认拼接）
    if (
      !buildConfig.value.customImageName ||
      !buildConfig.value.customImageName.trim()
    ) {
      buildConfig.value.customImageName = "";
    }
  } else {
    selectedServices.value = [];
  }
}

// 服务选择变化时的处理
function onServiceSelectionChange(serviceName) {
  if (!selectedServices.value.includes(serviceName)) {
    // 取消选中时，清空推送配置
    const config = getServiceConfig(serviceName);
    config.push = false;
    // 不清空 registry，因为它是全局批量设置的
  }
}

// 从镜像前缀推断推送仓库名称
function getRegistryNameFromPrefix(prefix) {
  if (!prefix) return "";
  // 查找匹配的仓库
  const registry = registries.value.find((reg) => {
    const regPrefix = reg.registry_prefix || reg.registry || "";
    return prefix === regPrefix || prefix.startsWith(regPrefix + "/");
  });
  return registry ? registry.name : "";
}

// 批量设置镜像前缀
function batchSetImagePrefix() {
  if (!batchImagePrefix.value.trim()) {
    alert("请输入镜像前缀或选择仓库");
    return;
  }
  const newPrefix = batchImagePrefix.value.trim();
  // 更新全局配置
  buildConfig.value.imagePrefix = newPrefix;

  // 从前缀推断推送仓库
  const registryName = getRegistryNameFromPrefix(newPrefix);

  // 直接将完整镜像名填入到每个服务的输入框，并设置推送仓库
  selectedServices.value.forEach((serviceName) => {
    const config = getServiceConfig(serviceName);
    // 直接设置完整镜像名：前缀/服务名
    config.customImageName = `${newPrefix}/${serviceName}`;
    // 如果从前缀推断出仓库，自动设置推送仓库
    if (registryName) {
      config.registry = registryName;
    }
  });
  // 清空批量设置输入框
  batchImagePrefix.value = "";
}

// 批量前缀选择变化
function onBatchPrefixChange() {
  // 选择仓库时，自动应用
  if (isRegistrySelected(batchImagePrefix.value)) {
    batchSetImagePrefix();
  }
}

// 批量设置标签
function batchSetTag() {
  if (!batchTag.value.trim()) {
    alert("请输入标签");
    return;
  }
  // 更新全局配置
  buildConfig.value.tag = batchTag.value.trim();
  // 清空批量设置输入框
  batchTag.value = "";
}

// 批量设置推送
function batchSetPush(push) {
  selectedServices.value.forEach((serviceName) => {
    const config = getServiceConfig(serviceName);
    config.push = push;
  });
}

// 服务选择
function selectAllServices() {
  selectedServices.value = services.value.map((s) => s.name);
  // 全选时，初始化所有服务的配置
  services.value.forEach((service) => {
    normalizeServiceConfig(service.name);
  });
}

function deselectAllServices() {
  selectedServices.value = [];
  // 全不选时，清空所有推送配置
  services.value.forEach((service) => {
    const config = getServiceConfig(service.name);
    config.push = false;
    config.registry = "";
  });
}

function toggleAllServices(event) {
  if (event.target.checked) {
    selectAllServices();
  } else {
    deselectAllServices();
  }
}

// 开始构建
async function startBuild() {
  building.value = true;

  try {
    let taskId = null;

    if (buildConfig.value.sourceType === "file") {
      // 文件上传构建
      // 构建步骤信息
      const buildSteps = {
        step1: {
          name: "选择数据源",
          completed: true,
          sourceType: buildConfig.value.sourceType,
          fileName: buildConfig.value.file?.name,
        },
        step2: {
          name: "确认分支",
          completed: true,
          skipped: true, // 文件上传模式跳过分支选择
        },
        step3: {
          name: "选择模板",
          completed: true,
          projectType: buildConfig.value.projectType,
          template: buildConfig.value.template,
        },
        step4: {
          name: "选择服务",
          completed: true,
          serviceCount: 0,
          selectedServices: [],
          isMultiService: false,
        },
        step5: {
          name: "选择资源包",
          completed: true,
          resourcePackageCount: buildConfig.value.resourcePackages?.length || 0,
        },
        step6: {
          name: "开始构建",
          completed: false,
          imageName: buildConfig.value.imageName,
          tag: buildConfig.value.tag,
          push: buildConfig.value.push,
        },
      };

      const formData = new FormData();
      formData.append("app_file", buildConfig.value.file);
      formData.append("project_type", buildConfig.value.projectType);
      formData.append("template", buildConfig.value.template);
      formData.append("imagename", buildConfig.value.imageName);
      formData.append("tag", buildConfig.value.tag || "latest");
      if (buildConfig.value.push) {
        formData.append("push", "on");
      }
      if (Object.keys(buildConfig.value.templateParams).length > 0) {
        formData.append(
          "template_params",
          JSON.stringify(buildConfig.value.templateParams)
        );
      }
      if (
        buildConfig.value.resourcePackages &&
        buildConfig.value.resourcePackages.length > 0
      ) {
        formData.append(
          "resource_package_configs",
          JSON.stringify(buildConfig.value.resourcePackages)
        );
      }
      formData.append("build_steps", JSON.stringify(buildSteps)); // 添加步骤信息

      const res = await axios.post("/api/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      taskId = res.data.build_id || res.data.task_id;
    } else {
      // Git 源码构建
      const source = gitSources.value.find(
        (s) => s.source_id === buildConfig.value.sourceId
      );
      if (!source) {
        throw new Error("数据源不存在");
      }

      // 构建步骤信息
      const buildSteps = {
        step1: {
          name: "选择数据源",
          completed: true,
          sourceType: buildConfig.value.sourceType,
          sourceId: buildConfig.value.sourceId,
          fileName: buildConfig.value.file?.name,
        },
        step2: {
          name: "确认分支",
          completed: true,
          branch:
            buildConfig.value.branch ||
            branchesAndTags.value.default_branch ||
            "默认分支",
          skipped: buildConfig.value.sourceType === "file",
        },
        step3: {
          name: "选择模板",
          completed: true,
          projectType: buildConfig.value.projectType,
          template: buildConfig.value.useProjectDockerfile
            ? "项目 Dockerfile"
            : buildConfig.value.template,
          useProjectDockerfile: buildConfig.value.useProjectDockerfile,
          dockerfileName: buildConfig.value.dockerfileName,
        },
        step4: {
          name: "选择服务",
          completed: true,
          serviceCount: services.value.length,
          selectedServices: selectedServices.value,
          isMultiService: services.value.length > 0,
        },
        step5: {
          name: "选择资源包",
          completed: true,
          resourcePackageCount: buildConfig.value.resourcePackages?.length || 0,
        },
        step6: {
          name: "开始构建",
          completed: false,
          imageName: buildConfig.value.imageName,
          tag: buildConfig.value.tag,
          push: buildConfig.value.push,
        },
      };

      const payload = {
        project_type: buildConfig.value.projectType,
        template: buildConfig.value.template,
        git_url: source.git_url,
        branch: buildConfig.value.branch || undefined,
        imagename:
          buildConfig.value.pushMode === "single" &&
          buildConfig.value.selectedService
            ? buildConfig.value.customImageName &&
              buildConfig.value.customImageName.trim()
              ? buildConfig.value.customImageName.trim()
              : `${
                  buildConfig.value.imagePrefix ||
                  buildConfig.value.imageName ||
                  "myapp/demo"
                }/${buildConfig.value.selectedService}`
            : buildConfig.value.imageName,
        tag: buildConfig.value.tag || "latest",
        push: buildConfig.value.push ? "on" : "off",
        template_params:
          Object.keys(buildConfig.value.templateParams).length > 0
            ? JSON.stringify(buildConfig.value.templateParams)
            : undefined,
        service_template_params:
          Object.keys(buildConfig.value.serviceTemplateParams).length > 0
            ? JSON.stringify(buildConfig.value.serviceTemplateParams)
            : undefined,
        use_project_dockerfile: buildConfig.value.useProjectDockerfile,
        dockerfile_name: buildConfig.value.dockerfileName || "Dockerfile",
        source_id: buildConfig.value.sourceId,
        selected_services:
          buildConfig.value.pushMode === "single" &&
          buildConfig.value.selectedService
            ? [buildConfig.value.selectedService]
            : selectedServices.value.length > 0
            ? selectedServices.value
            : undefined,
        service_push_config:
          selectedServices.value.length > 0 &&
          (buildConfig.value.pushMode === "multi" ||
            buildConfig.value.useProjectDockerfile)
            ? Object.fromEntries(
                selectedServices.value.map((serviceName) => {
                  const config = getServiceConfig(serviceName);
                  normalizeServiceConfig(serviceName);
                  // 使用完整镜像名（自定义或拼接）
                  // 获取完整镜像名（自定义或使用默认拼接）
                  const customName =
                    config.customImageName && config.customImageName.trim();
                  const imageName =
                    customName || getServiceDefaultImageName(serviceName);
                  return [
                    serviceName,
                    {
                      push: config.push || false,
                      imageName: imageName, // 完整镜像名（自定义或前缀/服务名）
                      tag:
                        config.tag.trim() ||
                        buildConfig.value.tag.trim() ||
                        "latest",
                      registry: config.registry || "",
                    },
                  ];
                })
              )
            : undefined,
        push_mode:
          buildConfig.value.sourceType === "file" ||
          buildConfig.value.useProjectDockerfile
            ? "multi"
            : buildConfig.value.pushMode || "multi",
        build_steps: buildSteps, // 添加步骤信息
        resource_package_configs:
          buildConfig.value.resourcePackages &&
          buildConfig.value.resourcePackages.length > 0
            ? buildConfig.value.resourcePackages
            : undefined, // 添加资源包配置
      };

      const res = await axios.post("/api/build-from-source", payload);
      taskId = res.data.task_id;
    }

    if (taskId) {
      console.log("✅ 构建任务已启动, task_id:", taskId);

      // 保存构建配置到任务（通过更新任务信息）
      try {
        // 任务信息会自动保存，这里可以添加额外的配置保存逻辑
        await saveBuildConfigToTask(taskId);
      } catch (saveError) {
        console.warn("⚠️ 保存构建配置失败:", saveError);
      }

      // 显示成功提示
      const imageName = buildConfig.value.imageName || '未知镜像';
      const tag = buildConfig.value.tag || 'latest';
      alert(`✅ 构建任务已创建！\n\n镜像: ${imageName}:${tag}\n任务ID: ${taskId}\n\n请到"任务管理"标签页查看进度和日志。`);

      // 重置构建状态
      building.value = false;

      window.dispatchEvent(new CustomEvent("show-build-log"));

      setTimeout(() => {
        pollBuildLogs(taskId);
      }, 100);
    } else {
      throw new Error("未返回 task_id");
    }
  } catch (error) {
    console.error("❌ 构建请求失败:", error);
    alert(
      error.response?.data?.error || error.response?.data?.detail || "构建失败"
    );
    building.value = false;
  }
}

// 保存构建配置到任务
async function saveBuildConfigToTask(taskId) {
  // 构建配置信息
  const configInfo = {
    sourceType: buildConfig.value.sourceType,
    sourceId: buildConfig.value.sourceId,
    branch: buildConfig.value.branch,
    projectType: buildConfig.value.projectType,
    template: buildConfig.value.template,
    useProjectDockerfile: buildConfig.value.useProjectDockerfile,
    dockerfileName: buildConfig.value.dockerfileName,
    imageName: buildConfig.value.imageName,
    tag: buildConfig.value.tag,
    push: buildConfig.value.push,
    templateParams: buildConfig.value.templateParams,
    selectedServices: selectedServices.value,
    buildSteps: {
      step1: "数据源选择完成",
      step2:
        buildConfig.value.sourceType === "git"
          ? "分支确认完成"
          : "跳过（文件上传）",
      step3: "模板选择完成",
      step4:
        services.value.length > 0
          ? `服务选择完成（${selectedServices.value.length}个服务）`
          : "单应用模式",
      step5: "构建任务已提交",
    },
  };

  // 注意：任务信息已经在创建任务时保存，这里可以记录额外的配置信息
  // 如果需要，可以通过 API 更新任务信息
  console.log("📋 构建配置信息:", configInfo);
}

// 轮询构建日志
let pollInterval = null;
async function pollBuildLogs(buildId) {
  let lastLogLength = 0;
  let taskCompleted = false;

  const poll = async () => {
    try {
      const taskRes = await axios.get(`/api/build-tasks/${buildId}`);
      const taskStatus = taskRes.data.status;

      let logs = "";
      try {
        const res = await axios.get(`/api/build-tasks/${buildId}/logs`);
        logs = typeof res.data === "string" ? res.data : String(res.data);
      } catch (e) {
        const res = await axios.get("/api/get-logs", {
          params: { build_id: buildId },
        });
        logs = typeof res.data === "string" ? res.data : String(res.data);
      }

      const logLines = logs
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      if (logLines.length > lastLogLength) {
        for (let i = lastLogLength; i < logLines.length; i++) {
          window.dispatchEvent(
            new CustomEvent("add-log", {
              detail: { text: logLines[i] },
            })
          );
        }
        lastLogLength = logLines.length;
      }

      if (taskStatus === "completed" || taskStatus === "failed") {
        taskCompleted = true;
        clearInterval(pollInterval);
        building.value = false;
        window.dispatchEvent(
          new CustomEvent("add-log", {
            detail: {
              text:
                taskStatus === "completed" ? "✅ 构建已完成" : "❌ 构建已失败",
            },
          })
        );
      }
    } catch (error) {
      console.error("❌ 获取日志失败:", error);
      if (error.response?.status === 404) {
        clearInterval(pollInterval);
        building.value = false;
        window.dispatchEvent(
          new CustomEvent("add-log", {
            detail: { text: "❌ 任务不存在" },
          })
        );
      }
    }
  };

  window.dispatchEvent(
    new CustomEvent("add-log", {
      detail: { text: `🚀 开始构建，Task ID: ${buildId}` },
    })
  );

  await poll();

  let pollCount = 0;
  pollInterval = setInterval(() => {
    if (taskCompleted) {
      clearInterval(pollInterval);
      return;
    }

    pollCount++;
    if (pollCount > 300) {
      clearInterval(pollInterval);
      building.value = false;
      window.dispatchEvent(
        new CustomEvent("add-log", {
          detail: { text: "⏰ 构建日志轮询超时（5分钟）" },
        })
      );
    } else {
      poll();
    }
  }, 1000);
}

// 加载资源包列表
async function loadResourcePackages() {
  loadingPackages.value = true;
  try {
    const res = await axios.get("/api/resource-packages");
    if (res.data.success) {
      packages.value = res.data.packages || [];
      // 初始化所有资源包的路径（直接填入默认值，用户可以编辑）
      packages.value.forEach((pkg) => {
        if (resourcePackagePaths.value[pkg.package_id] === undefined) {
          resourcePackagePaths.value[pkg.package_id] =
            getDefaultResourcePath(pkg);
        }
      });
    }
  } catch (error) {
    console.error("加载资源包列表失败:", error);
  } finally {
    loadingPackages.value = false;
  }
}

// 获取默认资源包路径（默认在根目录下，直接使用文件名）
function getDefaultResourcePath(pkg) {
  if (!pkg) return "";
  // 默认在根目录下，直接使用文件名
  return pkg.name;
}

// 更新资源包路径
function updateResourcePackagePath(packageId, path) {
  // 用户编辑时，直接保存输入的值
  resourcePackagePaths.value[packageId] = path ? path.trim() : "";
}

// 全选/取消全选资源包
function toggleAllPackages(event) {
  if (event.target.checked) {
    selectedResourcePackages.value = packages.value.map((p) => p.package_id);
    packages.value.forEach((pkg) => {
      if (!resourcePackagePaths.value[pkg.package_id]) {
        resourcePackagePaths.value[pkg.package_id] =
          getDefaultResourcePath(pkg);
      }
    });
  } else {
    selectedResourcePackages.value = [];
  }
}

// 格式化文件大小
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

async function loadRegistries() {
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
  } catch (error) {
    console.error("加载仓库列表失败:", error);
  }
}

async function loadDockerInfo() {
  try {
    const res = await axios.get("/api/docker/info");
    dockerInfo.value = res.data;
  } catch (error) {
    console.error("加载 Docker 信息失败:", error);
  }
}

// 获取构建模式标签
function getBuildModeLabel() {
  if (!dockerInfo.value) return "未知";

  if (dockerInfo.value.builder_type === "local") {
    return "容器内编译（本地 Docker）";
  } else if (dockerInfo.value.builder_type === "remote") {
    // 优先使用 remote_config，如果没有则从 remote_host 解析
    const remoteConfig = dockerInfo.value.remote_config;
    if (remoteConfig) {
      // 统一显示为"远程 Docker"
      const protocol = remoteConfig.use_tls ? "TLS" : "TCP";
      const port = remoteConfig.port || (remoteConfig.use_tls ? 2376 : 2375);
      return `远程 Docker (${protocol}://${remoteConfig.host}:${port})`;
    } else {
      // 兼容旧格式：从 remote_host 解析
      const remoteHost = dockerInfo.value.remote_host || "";
      const portMatch = remoteHost.match(/:(\d+)$/);
      if (portMatch) {
        const port = parseInt(portMatch[1]);
        const protocol = port === 2376 ? "TLS" : "TCP";
        return `远程 Docker (${protocol}://${remoteHost})`;
      }
      return remoteHost
        ? `远程 Docker (${remoteHost})`
        : "远程 Docker";
    }
  } else if (dockerInfo.value.builder_type === "mock") {
    return "模拟模式";
  }
  return "未知";
}

onMounted(() => {
  loadTemplates();
  loadGitSources();
  loadRegistries();
  loadDockerInfo();
});
</script>

<style scoped>
.step-build-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.steps-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #e9ecef;
  color: #6c757d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  transition: all 0.3s;
}

.step-item.active .step-number {
  background-color: #0d6efd;
  color: white;
}

.step-item.completed .step-number {
  background-color: #198754;
  color: white;
}

.step-label {
  margin-top: 8px;
  font-size: 0.875rem;
  color: #6c757d;
  transition: all 0.3s;
}

.step-item.active .step-label {
  color: #0d6efd;
  font-weight: 500;
}

.step-item.completed .step-label {
  color: #198754;
}

.step-connector {
  width: 60px;
  height: 2px;
  background-color: #e9ecef;
  margin: 0 10px;
  transition: all 0.3s;
}

.step-connector.completed {
  background-color: #198754;
}

.step-panel {
  min-height: 400px;
  padding: 20px;
}

.alert-sm {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}
</style>
