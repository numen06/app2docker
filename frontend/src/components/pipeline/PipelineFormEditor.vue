<template>
  <div class="pipeline-form-editor">
                <!-- 基本信息 Tab -->
                <div
                  v-if="section === 'basic'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="basic-pane"
                >
                  <div class="pipeline-field-grid pipeline-field-grid--2">
                    <div class="pipeline-field">
                      <label class="block text-sm font-medium text-slate-700"
                        >流水线名称 <span class="text-red-500">*</span></label
                      >
                      <input
                        v-model="formData.name"
                        type="text"
                        class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                        required
                        placeholder="例如：主分支自动构建"
                      />
                    </div>
                    <div class="pipeline-field pipeline-field--full">
                      <label class="block text-sm font-medium text-slate-700">描述</label>
                      <input
                        v-model="formData.description"
                        type="text"
                        class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                        placeholder="流水线描述（可选）"
                      />
                    </div>
                  </div>
                </div>

                <!-- Git 配置 Tab -->
                <div
                  v-if="section === 'git'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="git-pane"
                >
                  <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
                    <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                      <h6 class="mb-0">
                        <AppIcon  name="code-branch" class="text-blue-600" /> Git 配置
                      </h6>
                    </div>
                    <div class="p-4">
                      <div class="pipeline-field-grid pipeline-field-grid--3">
                        <div class="pipeline-field">
                          <label class="block text-sm font-medium text-slate-700">Git 数据源</label>
                          <select
                            v-model="formData.source_id"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                            @change="onSourceSelected"
                          >
                            <option value="">-- 选择数据源或手动输入 --</option>
                            <option
                              v-for="source in gitSources"
                              :key="source.source_id"
                              :value="source.source_id"
                            >
                              {{ source.name }} ({{
                                formatGitUrl(source.git_url)
                              }})
                            </option>
                          </select>
                          <div class="text-xs text-slate-500 text-sm mt-1">
                            <AppIcon  name="info-circle" />
                            可以从已保存的数据源中选择，或手动输入 Git 仓库地址
                          </div>
                        </div>
                        <div class="pipeline-field">
                          <label class="block text-sm font-medium text-slate-700"
                            >Git 仓库地址
                            <span class="text-red-500">*</span></label
                          >
                          <input
                            v-model="formData.git_url"
                            type="text"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                            required
                            placeholder="https://github.com/user/repo.git"
                          />
                        </div>
                        <div class="pipeline-field">
                          <label class="block text-sm font-medium text-slate-700">分支名称</label>
                          <div class="flex w-full">
                            <select
                              v-if="
                                repoVerified ||
                                formData.source_id ||
                                formData.git_url"
                              v-model="formData.branch"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              :disabled="
                                refreshingBranches ||
                                (!repoVerified &&
                                  !formData.source_id &&
                                  !formData.git_url)"
                              @change="onBranchChanged"
                            >
                              <option value="">
                                使用默认分支 ({{
                                  branchesAndTags.default_branch ||"main"
                                }})
                              </option>
                              <optgroup
                                v-if="branchesAndTags.branches.length > 0"
                                label="分支"
                              >
                                <option
                                  v-for="branch in branchesAndTags.branches"
                                  :key="branch"
                                  :value="branch"
                                >
                                  {{ branch }}
                                </option>
                              </optgroup>
                              <optgroup
                                v-if="branchesAndTags.tags.length > 0"
                                label="标签"
                              >
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
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              placeholder="请先选择数据源"
                              disabled
                            />
                            <Button
                              v-if="formData.source_id || formData.git_url"
                              variant="outline" size="sm"
                              type="button"
                              @click="refreshBranches(true)"
                              :disabled="refreshingBranches"
                              title="刷新分支列表"
                            >
                              <AppIcon
                                v-if="refreshingBranches"
                                
                               name="spinner" spin />
                              <AppIcon v-else  name="sync-alt" />
                            </Button>
                          </div>
                          <small class="text-slate-500">
                            <span v-if="refreshingBranches"
                              >正在刷新分支列表...</span
                            >
                            <span
                              v-else-if="
                                repoVerified &&
                                branchesAndTags.branches.length > 0"
                            >
                              已加载
                              {{ branchesAndTags.branches.length }} 个分支、{{
                                branchesAndTags.tags.length
                              }}
                              个标签
                            </span>
                            <span
                              v-else-if="formData.source_id || formData.git_url"
                            >
                              点击刷新按钮加载分支列表，或留空使用推送的分支
                            </span>
                            <span v-else>请先选择数据源</span>
                          </small>
                        </div>
                        <div class="pipeline-field">
                          <label class="block text-sm font-medium text-slate-700"
                            >项目类型 <span class="text-red-500">*</span></label
                          >
                          <select
                            v-model="formData.project_type"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                          >
                            <option value="jar">Java 应用（JAR）</option>
                            <option value="nodejs">Node.js 应用</option>
                            <option value="python">Python 应用</option>
                            <option value="go">Go 应用</option>
                            <option value="web">静态网站</option>
                          </select>
                        </div>
                        <div class="pipeline-field">
                          <label class="block text-sm font-medium text-slate-700">子路径</label>
                          <input
                            v-model="formData.sub_path"
                            type="text"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                            placeholder="留空表示根目录"
                          />
                        </div>
                        <div class="pipeline-field pipeline-field--full">
                          <div class="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                            <input
                              v-model="formData.tag_build_enabled"
                              class="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                              type="checkbox"
                              id="gitTagBuildEnabled"
                            />
                            <div>
                              <label class="text-sm font-medium text-slate-700" for="gitTagBuildEnabled">
                                启用 Tag 构建
                              </label>
                              <p class="mb-0 text-xs leading-5 text-slate-500">
                                开启后，手动触发可选择 Git tag，Webhook 收到 refs/tags/* 时按 tag 名称构建镜像标签。
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <PipelineMultiServiceTab
                  v-if="section === 'services'"
                  embedded
                />

                <!-- Dockerfile & 镜像配置 Tab -->
                <div
                  v-if="section === 'build'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="build-pane"
                >
                  <!-- JSON编辑器（新建和编辑模式都使用） -->
                  <div>
                    <div
                      class="flex justify-between items-center mb-3"
                    >
                      <h6 class="mb-0">
                        <AppIcon  name="code" />
                        {{ editingPipeline ?"编辑" :"新建" }}构建配置JSON
                      </h6>
                      <div class="inline-flex items-stretch text-sm" role="group">
                        <Button
                          type="button"
                          variant="outline" size="sm"
                          @click="copyBuildConfigJson"
                        >
                          <AppIcon  name="copy" /> 复制JSON
                        </Button>
                      </div>
                    </div>
                    <div class="rounded-md border px-3 py-2 text-sm border-sky-200 bg-sky-50 text-sky-900 mb-3">
                      <AppIcon  name="info-circle" />
                      <strong>提示：</strong
                      >编辑JSON后点击"应用"将配置应用到表单，然后点击底部"保存"按钮保存流水线。
                    </div>
                    <div class="pipeline-json-editor">
                      <codemirror
                        v-model="buildConfigJsonText"
                        :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
                        :extensions="jsonEditorExtensions"
                      />
                    </div>
                    <div
                      v-if="buildConfigJsonError"
                      class="rounded-md border px-3 py-2 text-sm border-red-200 bg-red-50 text-red-800 mt-2"
                    >
                      <AppIcon  name="exclamation-circle" />
                      {{ buildConfigJsonError }}
                    </div>
                    <div class="mt-3 flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline" size="sm"
                        @click="resetBuildConfigJson"
                      >
                        <AppIcon  name="undo" /> 重置
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        @click="applyBuildConfigJson"
                        :disabled="!!buildConfigJsonError"
                      >
                        <AppIcon  name="check" /> 应用
                      </Button>
                    </div>
                  </div>

                  <!-- 旧表单界面（已废弃，保留作为参考） -->
                  <div v-if="false" style="display: none">
                    <!-- 视图切换和查看JSON按钮 -->
                    <div
                      class="flex justify-between items-center mb-3"
                    >
                      <h6 class="mb-0">
                        <AppIcon  name="cogs" /> 编辑构建配置JSON
                      </h6>
                      <div class="inline-flex items-stretch text-sm" role="group">
                        <Button
                          type="button"
                          variant="outline" size="sm"
                          @click="showBuildConfigJsonModal = true"
                        >
                          <AppIcon  name="code" /> 查看JSON
                        </Button>
                      </div>
                    </div>

                    <!-- Dockerfile 配置模块 -->
                    <div class="rounded-lg border border-slate-200 bg-white shadow-sm mb-4">
                      <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                        <h6 class="mb-0">
                          <AppIcon  name="file-code" class="text-blue-600" />
                          Dockerfile 配置
                        </h6>
                      </div>
                      <div class="p-4">
                        <div class="pipeline-field-grid pipeline-field-grid--3">
                          <div class="pipeline-field pipeline-field--full">
                            <label class="block text-sm font-medium text-slate-700">Dockerfile 来源</label>
                            <div
                              class="pipeline-option-group pipeline-option-group--2"
                              role="group"
                            >
                              <input
                                type="radio"
                                class="choice-input"
                                id="use-project-dockerfile"
                                :value="true"
                                v-model="formData.use_project_dockerfile"
                                @change="onDockerfileSourceChange"
                              />
                              <label
                                class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
                                for="use-project-dockerfile"
                              >
                                <AppIcon  name="file-code" /> 项目Dockerfile
                              </label>

                              <input
                                type="radio"
                                class="choice-input"
                                id="use-template"
                                :value="false"
                                v-model="formData.use_project_dockerfile"
                                @change="onDockerfileSourceChange"
                              />
                              <label
                                class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
                                for="use-template"
                              >
                                <AppIcon  name="layer-group" /> 使用模板
                              </label>
                            </div>
                          </div>
                          <div
                            v-if="formData.use_project_dockerfile"
                            class="pipeline-field"
                          >
                            <label class="block text-sm font-medium text-slate-700">Dockerfile 文件名</label>
                            <div v-if="scanningDockerfiles" class="mb-2">
                              <AppIcon  name="spinner" spin />
                              <small class="text-slate-500"
                                >正在扫描项目中的 Dockerfile...</small
                              >
                            </div>
                            <div class="flex w-full">
                              <select
                                v-model="formData.dockerfile_name"
                                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                                :disabled="
                                  scanningDockerfiles || !formData.branch"
                                required
                              >
                                <option value="">-- 请先选择分支 --</option>
                                <option value="Dockerfile">
                                  Dockerfile（默认，根目录）
                                </option>
                                <!-- 如果当前选择不在扫描列表中，也要显示出来 -->
                                <option
                                  v-if="
                                    formData.dockerfile_name &&
                                    formData.dockerfile_name !== 'Dockerfile' &&
                                    !availableDockerfiles.some(
                                      (df) =>
                                        df.path === formData.dockerfile_name
                                    )"
                                  :value="formData.dockerfile_name"
                                  :key="'current-' + formData.dockerfile_name"
                                >
                                  {{ formData.dockerfile_name }} (当前选择)
                                </option>
                                <option
                                  v-for="dockerfile in availableDockerfiles"
                                  :key="dockerfile.path"
                                  :value="dockerfile.path"
                                >
                                  {{ dockerfile.path }}
                                  {{
                                    dockerfile.path !== dockerfile.name
                                      ? `(${dockerfile.name})`
                                      :""
                                  }}
                                </option>
                              </select>
                              <Button
                                variant="outline" size="sm"
                                type="button"
                                @click="scanDockerfiles(true, true)"
                                :disabled="
                                  scanningDockerfiles ||
                                  (!formData.branch &&
                                    !branchesAndTags.default_branch)"
                                title="刷新 Dockerfile 列表（强制刷新）"
                              >
                                <AppIcon
                                  v-if="scanningDockerfiles"
                                  
                                 name="spinner" spin />
                                <AppIcon v-else  name="sync-alt" />
                              </Button>
                            </div>
                            <small
                              v-if="dockerfilesError"
                              class="text-red-500 block mt-1"
                            >
                              <AppIcon  name="exclamation-triangle" />
                              {{ dockerfilesError }}
                            </small>
                            <small
                              v-else-if="availableDockerfiles.length > 0"
                              class="text-slate-500 block mt-1"
                            >
                              <AppIcon  name="check-circle" /> 已扫描到
                              {{ availableDockerfiles.length }} 个 Dockerfile
                            </small>
                            <small
                              v-else-if="formData.branch"
                              class="text-slate-500 block mt-1"
                            >
                              <AppIcon  name="info-circle" />
                              请先选择分支，然后点击刷新按钮扫描项目中的
                              Dockerfile
                            </small>
                            <small v-else class="text-slate-500 block mt-1">
                              <AppIcon  name="info-circle" /> 请先选择分支
                            </small>
                          </div>
                          <div v-else class="pipeline-field">
                            <label class="block text-sm font-medium text-slate-700">模板名称</label>

                            <!-- 当前选择提示 -->
                            <div
                              v-if="
                                formData.template && formData.template !== ''"
                              class="rounded-md border px-3 py-2 text-sm border-green-200 bg-green-50 text-green-800 px-2 py-1 text-xs mb-2"
                            >
                              <AppIcon  name="check-circle" class="mr-2" />
                              <strong>当前选择：</strong>{{ formData.template }}
                              <span
                                v-if="
                                  filteredTemplates.find(
                                    (t) => t.name === formData.template
                                  )"
                              >
                                ({{
                                  filteredTemplates.find(
                                    (t) => t.name === formData.template
                                  ).project_type
                                }})
                              </span>
                            </div>

                            <select
                              v-model="formData.template"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              @change="onTemplateChange"
                              :disabled="!formData.project_type"
                            >
                              <option value="">-- 请先选择项目类型 --</option>
                              <option
                                v-for="tpl in filteredTemplates"
                                :key="tpl.name"
                                :value="tpl.name"
                              >
                                {{ tpl.name }} ({{ tpl.project_type }})
                              </option>
                            </select>
                            <small
                              v-if="
                                formData.project_type &&
                                filteredTemplates.length === 0"
                              class="text-slate-500 block mt-1"
                            >
                              <AppIcon  name="info-circle" />
                              当前项目类型没有可用的模板
                            </small>
                            <small
                              v-else-if="
                                formData.project_type &&
                                filteredTemplates.length > 0"
                              class="text-slate-500 block mt-1"
                            >
                              <AppIcon  name="check-circle" />
                              已按项目类型过滤，共
                              {{ filteredTemplates.length }} 个模板
                            </small>
                            <small v-else class="text-slate-500 block mt-1">
                              <AppIcon  name="info-circle" /> 请先在 Git
                              配置中选择项目类型
                            </small>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 镜像配置 -->
                    <div class="rounded-lg border border-slate-200 bg-white shadow-sm mb-4">
                      <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                        <h6 class="mb-0">
                          <AppIcon  name="docker" class="text-blue-600" /> 镜像配置
                        </h6>
                      </div>
                      <div class="p-4">
                        <div class="pipeline-field-grid pipeline-field-grid--3">
                          <div class="pipeline-field">
                            <label class="block text-sm font-medium text-slate-700"
                              >镜像名称
                              <span class="text-red-500">*</span></label
                            >
                            <input
                              v-model="formData.image_name"
                              type="text"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              required
                              placeholder="myapp/demo"
                            />
                            <small class="text-slate-500 block mt-1">
                              <span v-if="formData.push_mode === 'single'">
                                <AppIcon  name="info-circle" />
                                单服务模式：直接使用此镜像名称
                              </span>
                              <span v-else>
                                <AppIcon  name="info-circle" />
                                多服务模式：作为镜像名称前缀，每个服务会自动拼接服务名
                              </span>
                            </small>
                          </div>
                          <div class="pipeline-field">
                            <label class="block text-sm font-medium text-slate-700">镜像标签</label>
                            <input
                              v-model="formData.tag"
                              type="text"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              placeholder="latest"
                            />
                            <small class="text-slate-500 block mt-1">
                              <AppIcon  name="info-circle" />
                              所有服务使用此标签，支持动态日期占位符
                            </small>
                          </div>
                          <div class="pipeline-field">
                            <div class="flex items-center gap-2 mt-4">
                              <input
                                v-model="formData.push"
                                class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                type="checkbox"
                                id="pushCheckBuild"
                              />
                              <label
                                class="text-sm text-slate-700"
                                for="pushCheckBuild"
                              >
                                构建完成后推送到仓库
                              </label>
                            </div>
                          </div>
                        </div>
                        <div
                          v-if="formData.push_mode === 'single'"
                          class="rounded-md border px-3 py-2 text-sm border-sky-200 bg-sky-50 text-sky-900 mt-3 mb-0"
                        >
                          <AppIcon  name="info-circle" />
                          <strong>单服务模式：</strong
                          >使用上方配置的镜像名称和标签
                        </div>
                        <div
                          v-else-if="formData.push_mode === 'multi'"
                          class="rounded-md border px-3 py-2 text-sm border-sky-200 bg-sky-50 text-sky-900 mt-3 mb-0"
                        >
                          <AppIcon  name="info-circle" />
                          <strong>多服务模式：</strong
                          >每个服务的镜像名称将自动生成为
                          <code
                            >{{
                              formData.image_name ||"myapp/demo"
                            }}-服务名</code
                          >，标签使用上方配置的全局标签
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Dockerfile 配置 Tab -->
                <div
                  v-if="section === 'dockerfile'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="dockerfile-pane"
                >
                  <!-- Dockerfile 来源选择 -->
                  <div class="rounded-lg border border-slate-200 bg-white shadow-sm mb-3">
                    <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                      <h6 class="mb-0">
                        <AppIcon  name="layer-group" class="text-blue-600" />
                        Dockerfile 来源
                      </h6>
                    </div>
                    <div class="p-4">
                      <div class="mb-2">
                        <label class="block text-sm font-medium text-slate-700"
                          >Dockerfile 来源
                          <span class="text-red-500">*</span></label
                        >
                        <div
                          class="pipeline-option-group pipeline-option-group--2"
                          role="group"
                        >
                          <input
                            type="radio"
                            class="choice-input"
                            id="dockerfile-from-project"
                            :value="true"
                            v-model="formData.use_project_dockerfile"
                            @change="onDockerfileSourceChange"
                          />
                          <label
                            class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
                            for="dockerfile-from-project"
                          >
                            <AppIcon  name="file-code" /> 从项目中选择
                          </label>

                          <input
                            type="radio"
                            class="choice-input"
                            id="dockerfile-from-template"
                            :value="false"
                            v-model="formData.use_project_dockerfile"
                            @change="onDockerfileSourceChange"
                          />
                          <label
                            class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"
                            for="dockerfile-from-template"
                          >
                            <AppIcon  name="layer-group" /> 从模板库中选择
                          </label>
                        </div>
                        <div class="text-xs text-slate-500 text-sm mt-1">
                          <AppIcon  name="info-circle" /> 选择 Dockerfile
                          的来源方式
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 模式1: 从项目中选择 Dockerfile -->
                  <div v-if="formData.use_project_dockerfile" class="rounded-lg border border-slate-200 bg-white shadow-sm mb-3">
                    <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                      <h6 class="mb-0">
                        <AppIcon  name="file-code" class="text-blue-600" />
                        从项目中选择 Dockerfile
                      </h6>
                    </div>
                    <div class="p-4">
                      <div class="mb-2">
                        <label class="block text-sm font-medium text-slate-700"
                          >Dockerfile 文件
                          <span class="text-red-500">*</span></label
                        >

                        <!-- 当前选择提示 -->
                        <div
                          v-if="
                            formData.dockerfile_name &&
                            formData.dockerfile_name !== ''"
                          class="rounded-md border px-3 py-2 text-sm border-green-200 bg-green-50 text-green-800 px-2 py-1 text-xs mb-2"
                        >
                          <AppIcon  name="check-circle" class="mr-2" />
                          <strong>当前选择：</strong
                          >{{ formData.dockerfile_name }}
                        </div>

                        <div v-if="scanningDockerfiles" class="mb-2">
                          <AppIcon  name="spinner" spin />
                          <small class="text-slate-500"
                            >正在扫描项目中的 Dockerfile...</small
                          >
                        </div>
                        <div class="flex w-full text-sm">
                          <select
                            v-model="formData.dockerfile_name"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                            :disabled="scanningDockerfiles || !formData.branch"
                            required
                          >
                            <option value="">-- 请先选择分支 --</option>
                            <option value="Dockerfile">
                              Dockerfile（默认，根目录）
                            </option>
                            <!-- 如果当前选择不在扫描列表中，也要显示出来 -->
                            <option
                              v-if="
                                formData.dockerfile_name &&
                                formData.dockerfile_name !== 'Dockerfile' &&
                                !availableDockerfiles.some(
                                  (df) => df.path === formData.dockerfile_name
                                )"
                              :value="formData.dockerfile_name"
                              :key="'current-' + formData.dockerfile_name"
                            >
                              {{ formData.dockerfile_name }} (当前选择)
                            </option>
                            <option
                              v-for="dockerfile in availableDockerfiles"
                              :key="dockerfile.path"
                              :value="dockerfile.path"
                            >
                              {{ dockerfile.path }}
                              {{
                                dockerfile.path !== dockerfile.name
                                  ? `(${dockerfile.name})`
                                  :""
                              }}
                            </option>
                          </select>
                          <Button
                            variant="outline" size="sm"
                            type="button"
                            @click="scanDockerfiles(true, true)"
                            :disabled="
                              scanningDockerfiles ||
                              (!formData.branch &&
                                !branchesAndTags.default_branch)"
                            title="刷新 Dockerfile 列表（强制刷新）"
                          >
                            <AppIcon
                              v-if="scanningDockerfiles"
                              
                             name="spinner" spin />
                            <AppIcon v-else  name="sync-alt" />
                          </Button>
                        </div>
                        <small
                          v-if="dockerfilesError"
                          class="text-red-500 block mt-1"
                        >
                          <AppIcon  name="exclamation-triangle" />
                          {{ dockerfilesError }}
                        </small>
                        <small
                          v-else-if="availableDockerfiles.length > 0"
                          class="text-slate-500 block mt-1"
                        >
                          <AppIcon  name="check-circle" /> 已扫描到
                          {{ availableDockerfiles.length }} 个 Dockerfile
                        </small>
                        <small
                          v-else-if="formData.branch"
                          class="text-slate-500 block mt-1"
                        >
                          <AppIcon  name="info-circle" />
                          请先选择分支，然后点击刷新按钮扫描项目中的 Dockerfile
                        </small>
                        <small v-else class="text-slate-500 block mt-1">
                          <AppIcon  name="info-circle" /> 请先在 Git
                          配置中选择分支
                        </small>
                      </div>
                    </div>
                  </div>

                  <!-- 模式2: 从模板库中选择 -->
                  <div
                    v-if="!formData.use_project_dockerfile"
                    class="rounded-lg border border-slate-200 bg-white shadow-sm mb-3"
                  >
                    <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                      <h6 class="mb-0">
                        <AppIcon  name="layer-group" class="text-blue-600" />
                        从模板库中选择
                      </h6>
                    </div>
                    <div class="p-4">
                      <div class="mb-2">
                        <label class="block text-sm font-medium text-slate-700"
                          >模板 <span class="text-red-500">*</span></label
                        >

                        <!-- 当前选择提示 -->
                        <div
                          v-if="formData.template && formData.template !== ''"
                          class="rounded-md border px-3 py-2 text-sm border-green-200 bg-green-50 text-green-800 px-2 py-1 text-xs mb-2"
                        >
                          <AppIcon  name="check-circle" class="mr-2" />
                          <strong>当前选择：</strong>{{ formData.template }}
                          <span
                            v-if="
                              filteredTemplates.find(
                                (t) => t.name === formData.template
                              )"
                          >
                            ({{
                              filteredTemplates.find(
                                (t) => t.name === formData.template
                              ).project_type
                            }})
                          </span>
                        </div>

                        <select
                          v-model="formData.template"
                          class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                          @change="onTemplateChange"
                          :disabled="!formData.project_type"
                          required
                        >
                          <option value="">-- 请先选择项目类型 --</option>
                          <option
                            v-for="tpl in filteredTemplates"
                            :key="tpl.name"
                            :value="tpl.name"
                          >
                            {{ tpl.name }} ({{ tpl.project_type }})
                          </option>
                        </select>
                        <small
                          v-if="
                            formData.project_type &&
                            filteredTemplates.length === 0"
                          class="text-slate-500 block mt-1"
                        >
                          <AppIcon  name="info-circle" />
                          当前项目类型没有可用的模板
                        </small>
                        <small
                          v-else-if="
                            formData.project_type &&
                            filteredTemplates.length > 0"
                          class="text-slate-500 block mt-1"
                        >
                          <AppIcon  name="check-circle" />
                          已按项目类型过滤，共
                          {{ filteredTemplates.length }} 个模板
                        </small>
                        <small v-else class="text-slate-500 block mt-1">
                          <AppIcon  name="info-circle" /> 请先在 Git
                          配置中选择项目类型
                        </small>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 资源包配置 Tab -->
                <div
                  v-if="section === 'resource'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="resource-pane"
                >
                  <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
                    <div
                      class="border-b border-slate-200 bg-slate-50 px-4 py-3 flex justify-between items-center"
                    >
                      <h6 class="mb-0">
                        <AppIcon  name="archive" class="text-blue-600" /> 资源包配置
                      </h6>
                      <Button
                        type="button"
                        variant="outline" size="sm"
                        @click="showResourcePackageModal = true"
                        title="添加资源包"
                      >
                        <AppIcon  name="plus" /> 添加
                      </Button>
                    </div>
                    <div class="p-4">
                      <div
                        v-if="
                          formData.resource_package_configs &&
                          formData.resource_package_configs.length > 0"
                        class="border rounded p-2"
                      >
                        <div
                          v-for="(
                            pkg, index
                          ) in formData.resource_package_configs"
                          :key="index"
                          class="flex items-center justify-between mb-2 p-2 bg-slate-50 rounded"
                        >
                          <div class="flex-1">
                            <strong>{{
                              getResourcePackageName(pkg.package_id)
                            }}</strong>
                            <small class="text-slate-500 ml-2"
                              >→ {{ pkg.target_path ||"resources" }}</small
                            >
                          </div>
                          <Button
                            type="button"
                            variant="destructive" size="sm"
                            @click="removeResourcePackage(index)"
                          >
                            <AppIcon  name="trash" />
                          </Button>
                        </div>
                      </div>
                      <div v-else class="text-slate-500 text-sm">
                        暂无资源包，点击"添加"按钮添加资源包
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Webhook 设置 Tab -->
                <div
                  v-if="section === 'webhook'"
                  class="pipeline-config-pane pipeline-webhook-pane"
                  role="tabpanel"
                  id="webhook-pane"
                >
                  <PipelineWebhookUrlBlock :webhook-token="formData.webhook_token" />

                  <section class="pipeline-webhook-block">
                    <h3 class="pipeline-webhook-block__title">
                      <AppIcon  name="key" /> 认证配置
                    </h3>
                    <div class="pipeline-field-grid pipeline-field-grid--2">
                      <div class="pipeline-webhook-field">
                        <label class="pipeline-webhook-field__label">Webhook Token（用于 URL）</label>
                        <div class="flex w-full">
                          <input
                            v-model="formData.webhook_token"
                            type="text"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 font-mono text-sm"
                            placeholder="留空自动生成"
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            type="button"
                            @click="regenerateWebhookToken"
                            title="重新生成 Token"
                          >
                            <AppIcon  name="sync-alt" /> 重新生成
                          </Button>
                        </div>
                        <span class="pipeline-webhook-field__hint">留空将自动生成 UUID</span>
                      </div>
                      <div class="pipeline-webhook-field">
                        <label class="pipeline-webhook-field__label">Webhook 密钥</label>
                        <div class="flex w-full">
                          <input
                            v-model="formData.webhook_secret"
                            type="text"
                            class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 font-mono text-sm"
                            placeholder="留空自动生成"
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            type="button"
                            @click="regenerateWebhookSecret"
                            title="重新生成密钥"
                          >
                            <AppIcon  name="sync-alt" /> 重新生成
                          </Button>
                        </div>
                        <span class="pipeline-webhook-field__hint">用于验证 Webhook 签名（可选）</span>
                      </div>
                    </div>
                  </section>

                  <section class="pipeline-webhook-block">
                    <h3 class="pipeline-webhook-block__title">
                      <AppIcon  name="filter" /> 触发条件
                    </h3>
                    <div class="pipeline-webhook-strategy" role="group">
                      <input
                        type="radio"
                        class="choice-input"
                        id="strategy-use-push"
                        value="use_push"
                        v-model="formData.webhook_branch_strategy"
                      />
                      <label class="pipeline-webhook-strategy__option" for="strategy-use-push">
                        <AppIcon  name="code-branch" />
                        任意分支推送触发
                        <small>编译推送分支</small>
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="strategy-filter-match"
                        value="filter_match"
                        v-model="formData.webhook_branch_strategy"
                      />
                      <label class="pipeline-webhook-strategy__option" for="strategy-filter-match">
                        <AppIcon  name="filter" />
                        仅配置分支规则触发
                        <small>编译推送分支</small>
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="strategy-use-configured"
                        value="use_configured"
                        v-model="formData.webhook_branch_strategy"
                      />
                      <label class="pipeline-webhook-strategy__option" for="strategy-use-configured">
                        <AppIcon  name="cog" />
                        仅配置分支触发
                        <small>编译配置分支</small>
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="strategy-select-branches"
                        value="select_branches"
                        v-model="formData.webhook_branch_strategy"
                      />
                      <label class="pipeline-webhook-strategy__option" for="strategy-select-branches">
                        <AppIcon  name="check-square" />
                        仅匹配允许规则触发
                        <small>编译推送分支</small>
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="strategy-select-configured"
                        value="select_configured"
                        v-model="formData.webhook_branch_strategy"
                      />
                      <label class="pipeline-webhook-strategy__option" for="strategy-select-configured">
                        <AppIcon  name="check-square" />
                        仅匹配允许规则触发
                        <small>编译配置分支</small>
                      </label>
                    </div>
                    <p class="pipeline-webhook-field__hint mt-2 mb-0">
                      <span
                        v-if="formData.webhook_branch_strategy === 'use_push'"
                      >
                        <AppIcon  name="info-circle" />
                        任意分支推送触发，编译推送分支。
                      </span>
                      <span
                        v-else-if="
                          formData.webhook_branch_strategy === 'filter_match'"
                      >
                        <AppIcon  name="info-circle" />
                        只有推送分支匹配 Git 配置中的分支规则时触发，编译推送分支。
                      </span>
                      <span
                        v-else-if="
                          formData.webhook_branch_strategy === 'select_branches'"
                      >
                        <AppIcon  name="info-circle" />
                        只有推送分支匹配下方允许规则时触发，编译推送分支。
                      </span>
                      <span
                        v-else-if="
                          formData.webhook_branch_strategy === 'select_configured'"
                      >
                        <AppIcon  name="info-circle" />
                        只有推送分支匹配下方允许规则时触发，编译配置分支。
                      </span>
                      <span v-else>
                        <AppIcon  name="info-circle" />
                        只有推送分支等于 Git 配置分支时触发，编译配置分支。
                      </span>
                    </p>
                  </section>

                  <section class="pipeline-webhook-block">
                    <h3 class="pipeline-webhook-block__title">
                      <AppIcon  name="cog" /> 编译目标
                    </h3>
                    <div class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                      <span
                        v-if="
                          formData.webhook_branch_strategy === 'use_configured' ||
                          formData.webhook_branch_strategy === 'select_configured'"
                      >
                        编译配置分支：{{ formData.branch || branchesAndTags.default_branch || "默认分支" }}
                      </span>
                      <span v-else>
                        编译 Webhook 推送分支。
                      </span>
                    </div>
                  </section>

                  <section
                    v-if="
                      formData.webhook_branch_strategy === 'select_branches' ||
                      formData.webhook_branch_strategy === 'select_configured'"
                    class="pipeline-webhook-block"
                  >
                    <h3 class="pipeline-webhook-block__title">
                      <AppIcon  name="list-check" /> 允许触发的分支规则
                      <span class="text-red-500 text-sm font-normal">*</span>
                    </h3>
                    <div
                      v-if="
                        !branchesAndTags.branches ||
                        branchesAndTags.branches.length === 0"
                      class="rounded-md border px-3 py-2 text-sm border-amber-200 bg-amber-50 text-amber-900"
                    >
                      <AppIcon  name="exclamation-triangle" /> 请先在 Git
                      配置中选择数据源和分支，以加载可用分支列表
                    </div>
                    <div
                      v-else
                      class="pipeline-webhook-list-box pipeline-webhook-list-box--scroll"
                    >
                      <div class="flex items-center gap-2 mb-2">
                        <input
                          class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          type="checkbox"
                          id="selectAllBranches"
                          :checked="isAllBranchesSelected"
                          @change="toggleAllBranches"
                        />
                        <label
                          class="text-sm text-slate-700 font-semibold"
                          for="selectAllBranches"
                        >
                          全选
                        </label>
                      </div>
                      <hr class="my-2" />
                      <div
                        v-for="branch in branchesAndTags.branches"
                        :key="branch"
                        class="flex items-center gap-2 mb-1"
                      >
                        <input
                          class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          type="checkbox"
                          :id="`branch-${branch}`"
                          :value="branch"
                          v-model="formData.webhook_allowed_branches"
                        />
                        <label
                          class="text-sm text-slate-700"
                          :for="`branch-${branch}`"
                        >
                          <AppIcon name="code-branch" class="mr-1 text-blue-600" />{{ branch }}
                        </label>
                      </div>
                    </div>
                    <div class="pipeline-webhook-field mt-3">
                      <label class="pipeline-webhook-field__label">手动分支规则</label>
                      <textarea
                        v-model="webhookAllowedBranchesText"
                        rows="4"
                        class="flex w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-sm"
                        placeholder="dev&#10;release/*&#10;feature/*"
                      ></textarea>
                    </div>
                    <p class="pipeline-webhook-field__hint mt-2 mb-0">
                      普通文本精确匹配：dev 只匹配 dev。显式通配符才模糊匹配：dev* 可匹配 dev1/dev2，release/* 可匹配 release/1.0。不使用包含匹配。
                    </p>
                  </section>

                  <section class="pipeline-webhook-block">
                    <div class="pipeline-webhook-block__head">
                      <div>
                        <h3 class="pipeline-webhook-block__title">
                          <AppIcon  name="tags" /> 分支标签映射
                        </h3>
                        <p class="pipeline-webhook-block__desc">
                          为不同分支设置镜像标签，支持通配符（如 feature/*）；多标签用半角逗号分隔；支持
                          ${DATE}、${TIMESTAMP} 等占位符。
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        @click="addBranchTagMapping"
                        title="添加映射"
                      >
                        <AppIcon  name="plus" /> 添加
                      </Button>
                    </div>
                    <div
                      v-if="
                        formData.branch_tag_mapping &&
                        formData.branch_tag_mapping.length > 0"
                      class="pipeline-webhook-list-box"
                    >
                      <div
                        v-for="(mapping, index) in formData.branch_tag_mapping"
                        :key="index"
                        class="pipeline-branch-mapping-row"
                      >
                        <input
                          v-model="mapping.branch"
                          type="text"
                          class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                          placeholder="分支名（如：main 或 feature/*）"
                        />
                        <span class="pipeline-branch-mapping-row__arrow text-center text-slate-500">
                          <AppIcon  name="arrow-right" />
                        </span>
                        <input
                          :value="mapping.tag"
                          type="text"
                          class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                          placeholder="标签（如：latest 或 latest,v1.0.0）"
                          title="多个标签用半角逗号（,）分隔"
                          @input="
                            mapping.tag = normalizeAsciiCommaSeparators(
                              $event.target.value
                            )"
                        />
                        <div class="pipeline-branch-mapping-row__action">
                          <Button
                            type="button"
                            variant="destructive" size="sm"
                            @click="removeBranchTagMapping(index)"
                            title="删除"
                          >
                            <AppIcon  name="trash" />
                          </Button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="pipeline-webhook-empty">
                      <AppIcon  name="info-circle" /> 暂无映射，点击「添加」创建
                    </div>
                  </section>
                </div>

                <!-- 构建后 Webhook Tab -->
                <div
                  v-if="section === 'post_webhook'"
                  class="pipeline-config-pane pipeline-webhook-pane"
                  role="tabpanel"
                  id="post-webhook-pane"
                >
                  <section class="pipeline-webhook-block">
                    <div class="pipeline-webhook-block__head">
                      <div>
                        <h3 class="pipeline-webhook-block__title">
                          <AppIcon  name="bell" /> 构建后 Webhook
                        </h3>
                        <p class="pipeline-webhook-block__desc">
                          构建成功完成后回调外部地址。支持变量：{task_id}、{image}、{tag}、{status}、{branch}、{pipeline_id}、{pipeline_name}、{created_at}、{completed_at}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        @click="addPostBuildWebhook"
                        title="添加 Webhook"
                      >
                        <AppIcon  name="plus" /> 添加
                      </Button>
                    </div>

                    <div
                      v-if="
                        formData.post_build_webhooks &&
                        formData.post_build_webhooks.length > 0"
                      class="pipeline-webhook-block__body"
                    >
                      <div
                        v-for="(webhook, index) in formData.post_build_webhooks"
                        :key="index"
                        class="pipeline-webhook-item"
                      >
                        <div class="pipeline-webhook-item__head">
                          <label class="pipeline-webhook-item__title mb-0">
                            <input
                              class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 mt-0"
                              type="checkbox"
                              :id="`post-webhook-enabled-${index}`"
                              v-model="webhook.enabled"
                            />
                            <AppIcon  name="bell" />
                            Webhook {{ index + 1 }}
                          </label>
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            @click="removePostBuildWebhook(index)"
                            title="删除"
                          >
                            <AppIcon  name="trash" />
                          </Button>
                        </div>
                        <div class="pipeline-webhook-item__body">
                          <section class="pipeline-webhook-block">
                            <h3 class="pipeline-webhook-block__title">
                              <AppIcon  name="code-branch" /> 分支触发策略
                            </h3>
                            <div class="pipeline-webhook-strategy" role="group">
                              <input
                                type="radio"
                                class="choice-input"
                                :id="`post-wh-branch-all-${index}`"
                                value="all"
                                v-model="webhook.branch_strategy"
                              />
                              <label
                                class="pipeline-webhook-strategy__option"
                                :for="`post-wh-branch-all-${index}`"
                              >
                                <AppIcon  name="code-branch" />
                                所有分支触发
                                <small>构建完成后均回调</small>
                              </label>
                              <input
                                type="radio"
                                class="choice-input"
                                :id="`post-wh-branch-match-${index}`"
                                value="filter_match"
                                v-model="webhook.branch_strategy"
                              />
                              <label
                                class="pipeline-webhook-strategy__option"
                                :for="`post-wh-branch-match-${index}`"
                              >
                                <AppIcon  name="filter" />
                                只允许匹配分支
                                <small>支持 feature/* 通配符</small>
                              </label>
                              <input
                                type="radio"
                                class="choice-input"
                                :id="`post-wh-branch-select-${index}`"
                                value="select_branches"
                                v-model="webhook.branch_strategy"
                              />
                              <label
                                class="pipeline-webhook-strategy__option"
                                :for="`post-wh-branch-select-${index}`"
                              >
                                <AppIcon  name="check-square" />
                                选择分支触发
                                <small>仅选中的分支触发</small>
                              </label>
                            </div>
                            <p class="pipeline-webhook-field__hint mt-2 mb-0">
                              <span v-if="webhook.branch_strategy === 'all'">
                                <AppIcon  name="info-circle" />
                                任意分支构建成功完成后都会触发此 Webhook
                              </span>
                              <span v-else-if="webhook.branch_strategy === 'filter_match'">
                                <AppIcon  name="info-circle" />
                                仅当构建分支与下方匹配模式一致时触发（支持通配符）
                              </span>
                              <span v-else-if="webhook.branch_strategy === 'select_branches'">
                                <AppIcon  name="info-circle" />
                                仅当选中分支构建成功完成后触发
                              </span>
                            </p>
                          </section>

                          <section
                            v-if="webhook.branch_strategy === 'filter_match'"
                            class="pipeline-webhook-block"
                          >
                            <h3 class="pipeline-webhook-block__title">
                              <AppIcon  name="filter" /> 匹配分支模式
                              <span class="text-red-500 text-sm font-normal">*</span>
                            </h3>
                            <input
                              type="text"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              inputmode="text"
                              autocomplete="off"
                              placeholder="main, feature/*, release/*"
                              :value="(webhook.branches || []).join(', ')"
                              @input="onPostBuildWebhookBranchesInput(webhook, $event)"
                            />
                            <p class="pipeline-webhook-field__hint mt-2 mb-0">
                              <AppIcon  name="info-circle" />
                              多个模式用半角逗号分隔，支持通配符（如 feature/*）
                            </p>
                          </section>

                          <section
                            v-if="webhook.branch_strategy === 'select_branches'"
                            class="pipeline-webhook-block"
                          >
                            <h3 class="pipeline-webhook-block__title">
                              <AppIcon  name="list-check" /> 允许触发的分支
                              <span class="text-red-500 text-sm font-normal">*</span>
                            </h3>
                            <input
                              type="text"
                              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              inputmode="text"
                              autocomplete="off"
                              placeholder="main, develop, staging"
                              :value="(webhook.branches || []).join(', ')"
                              @input="onPostBuildWebhookBranchesInput(webhook, $event)"
                            />
                            <p class="pipeline-webhook-field__hint mt-2 mb-0">
                              <AppIcon  name="info-circle" />
                              多个分支用半角逗号分隔；仅精确匹配分支名
                            </p>
                          </section>
                          <div class="pipeline-webhook-field">
                            <div class="pipeline-webhook-block__head pipeline-webhook-block__head--tight">
                              <h3 class="pipeline-webhook-block__title mb-0">
                                <AppIcon  name="link" /> 回调 URL
                                <span class="text-red-500 text-sm font-normal">*</span>
                              </h3>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                title="从部署任务中选择"
                                @click="loadDeployTasks"
                              >
                                <AppIcon  name="rocket" /> 从部署任务选择
                              </Button>
                            </div>
                            <div class="pipeline-webhook-url-row">
                              <input
                                v-model="webhook.url"
                                type="text"
                                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                                placeholder="https://example.com/webhook"
                              />
                              <select
                                class="flex h-9 shrink-0 rounded-md border border-slate-200 px-2 py-1 text-sm"
                                style="max-width: 11rem"
                                @change="onDeployTaskSelected(webhook, $event.target.value); $event.target.value = ''"
                              >
                                <option value="" disabled>部署任务…</option>
                                <option
                                  v-for="task in deployTaskList"
                                  :key="task.task_id"
                                  :value="task.task_id"
                                >
                                  {{ task.app_name || task.task_id.substring(0, 8) }}
                                </option>
                              </select>
                            </div>
                            <p
                              v-if="webhook.url && webhook.url.includes('/api/webhook/deploy/')"
                              class="pipeline-webhook-field__hint mt-2 mb-0"
                            >
                              <AppIcon  name="info-circle" />
                              已自动填充部署任务 Webhook URL
                            </p>
                          </div>
                          <div class="pipeline-field-grid pipeline-field-grid--3">
                            <div class="pipeline-webhook-field">
                              <label class="pipeline-webhook-field__label">
                                <AppIcon  name="paper-plane" class="text-blue-600 mr-1" />请求方法
                              </label>
                              <select
                                v-model="webhook.method"
                                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                              >
                                <option value="POST">POST</option>
                                <option value="PUT">PUT</option>
                                <option value="PATCH">PATCH</option>
                              </select>
                            </div>
                          </div>
                          <div class="pipeline-webhook-field">
                            <label class="pipeline-webhook-field__label">
                              <AppIcon  name="heading" class="text-blue-600 mr-1" />请求头（JSON，可选）
                            </label>
                            <textarea
                              v-model="webhook.headers_json"
                              class="flex min-h-[4rem] w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-sm"
                              rows="2"
                              placeholder='{"Content-Type":"application/json"}'
                            ></textarea>
                          </div>
                          <div class="pipeline-webhook-field">
                            <label class="pipeline-webhook-field__label">
                              <AppIcon  name="file-code" class="text-blue-600 mr-1" />请求体模板
                            </label>
                            <textarea
                              v-model="webhook.body_template"
                              class="flex min-h-[6rem] w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-sm"
                              rows="4"
                              placeholder='{"task_id":"{task_id}","status":"{status}"}'
                            ></textarea>
                            <p class="pipeline-webhook-field__hint mb-0">
                              <AppIcon  name="info-circle" />
                              支持 {task_id}、{image}、{tag}、{status}、{branch}、{pipeline_id} 等变量
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div v-else class="pipeline-webhook-empty">
                      <AppIcon  name="info-circle" /> 暂无配置，点击「添加」创建构建后 Webhook
                    </div>
                  </section>
                </div>

                <!-- 其他选项 Tab -->
                <div
                  v-if="section === 'other'"
                  class="pipeline-config-pane"
                  role="tabpanel"
                  id="other-pane"
                >
                  <div class="flex items-center gap-2 mb-3">
                    <input
                      v-model="formData.enabled"
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      id="enabledCheck"
                      checked
                    />
                    <label class="text-sm text-slate-700" for="enabledCheck">
                      启用流水线
                    </label>
                  </div>
                  <div class="mb-3">
                    <div class="flex items-center gap-2 mb-2">
                      <input
                        v-model="formData.trigger_schedule"
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        id="triggerScheduleCheck"
                      />
                      <label
                        class="text-sm text-slate-700"
                        for="triggerScheduleCheck"
                      >
                        启用定时触发
                      </label>
                    </div>
                    <div v-if="formData.trigger_schedule" class="ml-4">
                      <label class="block text-sm font-medium text-slate-700"
                        >Cron 表达式 <span class="text-red-500">*</span></label
                      >
                      <input
                        v-model="formData.cron_expression"
                        type="text"
                        class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 font-mono text-sm"
                        placeholder="0 0 * * *"
                        :required="formData.trigger_schedule"
                      />
                      <small class="text-slate-500">
                        <code>0 0 * * *</code> 每天零点 |
                        <code>0 */2 * * *</code> 每2小时 |
                        <code>*/30 * * * *</code> 每30分钟
                      </small>
                    </div>
                  </div>
                  <div
                    v-if="editingPipeline"
                    class="mt-6 rounded-lg border border-red-200 bg-red-50/50 p-4"
                  >
                    <h6 class="mb-2 text-red-700">
                      <AppIcon  name="exclamation-triangle" class="mr-1" /> 危险操作
                    </h6>
                    <p class="mb-3 text-sm text-slate-600">
                      删除后将无法恢复，相关构建历史可能一并清理。
                    </p>
                    <Button variant="destructive" size="sm" type="button" @click="deletePipeline">
                      <AppIcon  name="trash" class="mr-1" /> 删除流水线
                    </Button>
                  </div>
                </div>

<!-- 资源包选择模态框 -->
    <div
      v-if="showResourcePackageModal"
      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
      @click.self="showResourcePackageModal = false"
      >
      <div class="relative z-10 mx-auto w-full max-w-3xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AppIcon  name="archive" /> 选择资源包
            </h5>
            <button
              type="button"
              class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              @click="showResourcePackageModal = false"
            ><AppIcon  name="times" /></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4" style="max-height: 60vh; overflow-y: auto">
            <div
              v-if="resourcePackages.length === 0"
              class="text-center py-4 text-slate-500"
            >
              <AppIcon  name="inbox" class="mb-2" />
              <p class="mb-0">暂无资源包</p>
              <small class="text-slate-500">请先在"资源包"标签页上传资源包</small>
            </div>
            <div v-else class="pipeline-field-grid pipeline-field-grid--3">
              <div
                v-for="pkg in resourcePackages"
                :key="pkg.package_id"
                class="pipeline-field"
              >
                <div
                  class="rounded-lg border border-slate-200 bg-white shadow-sm h-full"
                  :class="{
                    'border-blue-300': isResourcePackageSelected(pkg.package_id),
                  }"
                >
                  <div class="p-4">
                    <div class="flex items-center gap-2">
                      <input
                        type="checkbox"
                        :value="pkg.package_id"
                        :checked="isResourcePackageSelected(pkg.package_id)"
                        @change="toggleResourcePackage(pkg)"
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <label class="text-sm text-slate-700 font-semibold">
                        {{ pkg.name }}
                      </label>
                    </div>
                    <small class="text-slate-500 block mt-1">{{
                      pkg.description ||"无描述"
                    }}</small>
                    <div
                      v-if="isResourcePackageSelected(pkg.package_id)"
                      class="mt-2"
                    >
                      <label class="block text-sm font-medium text-slate-700">目标路径</label>
                      <input
                        type="text"
                        :value="
                          getResourcePackageConfig(pkg.package_id).target_path"
                        @input="
                          updateResourcePackagePath(
                            pkg.package_id,
                            $event.target.value
                          )"
                        class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                        placeholder="resources"
                      />
                      <small class="text-slate-500 block mt-1">
                        <AppIcon  name="info-circle" />
                        相对路径，如：<code>test/b.txt</code> 或
                        <code>config/app.conf</code>
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="pipeline-dialog-footer flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
            <Button
              type="button"
              variant="outline" size="sm"
              @click="showResourcePackageModal = false"
            >
              完成
            </Button>
          </div>
        </div>
      </div>
    </div>
<!-- 构建配置JSON模态框 -->
    <div
      v-if="showBuildConfigJsonModal"
      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
      @click.self="showBuildConfigJsonModal = false"
      >
      <div class="relative z-10 mx-auto w-full max-w-3xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AppIcon  name="code" />
              {{ editingPipeline ?"编辑" :"查看" }}构建配置JSON
            </h5>
            <button
              type="button"
              class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              @click="closeBuildConfigJsonModal"
            ><AppIcon  name="times" /></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div v-if="editingPipeline" class="rounded-md border px-3 py-2 text-sm border-sky-200 bg-sky-50 text-sky-900 mb-3">
              <AppIcon  name="info-circle" />
              <strong>提示：</strong>编辑JSON后点击保存，配置将应用到流水线中。
            </div>
            <div class="flex justify-end mb-2">
              <Button
                type="button"
                variant="outline" size="sm"
                @click="copyBuildConfigJson"
              >
                <AppIcon  name="copy" /> 复制JSON
              </Button>
            </div>
            <div class="pipeline-json-editor">
              <codemirror
                v-model="buildConfigJsonText"
                :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
                :disabled="!editingPipeline"
                :extensions="jsonEditorExtensions"
              />
            </div>
            <div v-if="buildConfigJsonError" class="rounded-md border px-3 py-2 text-sm border-red-200 bg-red-50 text-red-800 mt-2">
              <AppIcon  name="exclamation-circle" />
              {{ buildConfigJsonError }}
            </div>
          </div>
          <div class="pipeline-dialog-footer flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
            <Button
              type="button"
              variant="outline" size="sm"
              @click="closeBuildConfigJsonModal"
            >
              取消
            </Button>
            <Button
              v-if="editingPipeline"
              type="button"
              size="sm"
              @click="saveBuildConfigJson"
              :disabled="!!buildConfigJsonError"
            >
              <AppIcon  name="save" /> 保存并应用
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import { inject, watch } from "vue";
import { useRouter } from "vue-router";
import { goToPipelineList } from "@/utils/pipelineNavigation.js";
import axios from "axios";
import Button from "@/components/ui/button/Button.vue";
import { Codemirror } from "vue-codemirror";
import PipelineMultiServiceTab from "@/components/pipeline/detail/PipelineMultiServiceTab.vue";
import PipelineWebhookUrlBlock from "@/components/pipeline/detail/PipelineWebhookUrlBlock.vue";

const props = defineProps({
  section: {
    type: String,
    required: true,
  },
});

const editor = inject("pipelineEditor", null);
if (!editor) {
  throw new Error("PipelineFormEditor 需要在 pipelineEditor 上下文中使用");
}
const formData = editor.formData;

watch(
  () => props.section,
  (tab) => {
    if (tab ==="build" && editor.buildConfigJson && editor.buildConfigJsonText) {
      editor.buildConfigJsonText.value = editor.buildConfigJson.value;
      editor.buildConfigJsonError.value ="";
    }
  },
  { immediate: true }
);
const editingPipeline = editor.editingPipeline;
const gitSources = editor.gitSources;
const templates = editor.templates;
const registries = editor.registries;
const projectTypesList = editor.projectTypesList;
const branchesAndTags = editor.branchesAndTags;
const refreshingBranches = editor.refreshingBranches;
const availableDockerfiles = editor.availableDockerfiles;
const scanningDockerfiles = editor.scanningDockerfiles;
const dockerfilesError = editor.dockerfilesError;
const repoVerified = editor.repoVerified;
const services = editor.services;
const loadingServices = editor.loadingServices;
const servicesError = editor.servicesError;
const filteredTemplates = editor.filteredTemplates;
const buildConfigJson = editor.buildConfigJson;
const buildConfigJsonText = editor.buildConfigJsonText;
const buildConfigJsonError = editor.buildConfigJsonError;
const dockerfileContentText = editor.dockerfileContentText;
const loadingDockerfile = editor.loadingDockerfile;
const jsonEditorExtensions = editor.jsonEditorExtensions;
const dockerfileEditorExtensions = editor.dockerfileEditorExtensions;
const resourcePackages = editor.resourcePackages;
const showResourcePackageModal = editor.showResourcePackageModal;
const showBuildConfigJsonModal = editor.showBuildConfigJsonModal;
const isAllBranchesSelected = editor.isAllBranchesSelected;
const webhookAllowedBranchesText = editor.webhookAllowedBranchesText;
const deployTaskList = editor.deployTaskList;
const onSourceSelected = editor.onSourceSelected;
const refreshBranches = editor.refreshBranches;
const scanDockerfiles = editor.scanDockerfiles;
const onBranchChanged = editor.onBranchChanged;
const copyBuildConfigJson = editor.copyBuildConfigJson;
const resetBuildConfigJson = editor.resetBuildConfigJson;
const applyBuildConfigJson = editor.applyBuildConfigJson;
const loadDockerfileFromRepo = editor.loadDockerfileFromRepo;
const applyDockerfileContent = editor.applyDockerfileContent;
const loadServices = editor.loadServices;
const onPushModeChange = editor.onPushModeChange;
const toggleService = editor.toggleService;
const onServiceSelectionChange = editor.onServiceSelectionChange;
const selectAllServices = editor.selectAllServices;
const deselectAllServices = editor.deselectAllServices;
const removeService = editor.removeService;
const getServiceConfig = editor.getServiceConfig;
const getServiceDefaultImageName = editor.getServiceDefaultImageName;
const onServiceImageNameBlur = editor.onServiceImageNameBlur;
const resetServiceImageName = editor.resetServiceImageName;
const toggleResourcePackage = editor.toggleResourcePackage;
const isResourcePackageSelected = editor.isResourcePackageSelected;
const getResourcePackageName = editor.getResourcePackageName;
const removeResourcePackage = editor.removeResourcePackage;
const getResourcePackageConfig = editor.getResourcePackageConfig;
const updateResourcePackagePath = editor.updateResourcePackagePath;
const onDockerfileSourceChange = editor.onDockerfileSourceChange;
const onTemplateChange = editor.onTemplateChange;
const formatGitUrl = editor.formatGitUrl;
const regenerateWebhookToken = editor.regenerateWebhookToken;
const regenerateWebhookSecret = editor.regenerateWebhookSecret;
const addBranchTagMapping = editor.addBranchTagMapping;
const addPostBuildWebhook = editor.addPostBuildWebhook;
const removePostBuildWebhook = editor.removePostBuildWebhook;
const removeBranchTagMapping = editor.removeBranchTagMapping;
const toggleAllBranches = editor.toggleAllBranches;
const onPostBuildWebhookBranchesInput = editor.onPostBuildWebhookBranchesInput;
const onDeployTaskSelected = editor.onDeployTaskSelected;
const closeBuildConfigJsonModal = editor.closeBuildConfigJsonModal;
const saveBuildConfigJson = editor.saveBuildConfigJson;

const router = useRouter();

async function deletePipeline() {
  const p = editingPipeline.value;
  if (!p?.pipeline_id) return;
  if (!(await showConfirm({ message: `确定要删除流水线「${p.name}」吗？`, danger: true }))) return;
  try {
    await axios.delete(`/api/pipelines/${p.pipeline_id}`);
    await goToPipelineList(router);
    toastSuccess("流水线已删除");
  } catch (error) {
    toastApiError(error,"删除失败");
  }
}
</script>
