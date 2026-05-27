<template>
  <div class="min-w-0 max-w-full">
    <PageToolbar title="部署配置管理" icon="rocket">
      <template #actions>
        <Button variant="outline" size="sm" @click="showImportModal = true">
          <AppIcon  name="file-import" class="mr-1" />
          <span class="hidden sm:inline">导入配置</span>
          <span class="sm:hidden">导入</span>
        </Button>
        <Button size="sm" @click="openSimpleCreateModal('standard')">
          <AppIcon  name="plus" class="mr-1" />
          <span class="hidden sm:inline">新建 SSH/Agent 部署</span>
          <span class="sm:hidden">SSH/Agent</span>
        </Button>
        <Button variant="outline" size="sm" @click="openSimpleCreateModal('portainer')">
          <AppIcon  name="cubes" class="mr-1" />
          <span class="hidden sm:inline">新建 Portainer 部署</span>
          <span class="sm:hidden">Portainer</span>
        </Button>
        <Button variant="secondary" size="sm" @click="showCreateModal = true">
          <AppIcon  name="code" class="mr-1" />
          <span class="hidden sm:inline">YAML创建</span>
          <span class="sm:hidden">YAML</span>
        </Button>
      </template>
    </PageToolbar>

    <div class="mb-2 flex flex-wrap items-center gap-2">
      <span class="text-xs text-slate-500">快捷过滤</span>
      <div class="flex flex-wrap gap-1" role="group" aria-label="任务类型过滤">
        <Button type="button" size="sm" :variant="taskTypeFilter === 'all' ? 'default' : 'outline'" @click="filterByType('all')" title="全部类型">全部类型</Button>
        <Button type="button" size="sm" :variant="taskTypeFilter === 'agent' ? 'default' : 'outline'" @click="filterByType('agent')" title="Agent">Agent</Button>
        <Button type="button" size="sm" :variant="taskTypeFilter === 'ssh' ? 'default' : 'outline'" @click="filterByType('ssh')" title="SSH">SSH</Button>
        <Button type="button" size="sm" :variant="taskTypeFilter === 'portainer' ? 'default' : 'outline'" @click="filterByType('portainer')" title="Portainer">Portainer</Button>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <AppIcon  name="spinner" spin />
      加载中…
    </div>

    <EmptyState v-else-if="filteredTasks.length === 0" message="暂无符合筛选条件的部署配置" />

    <div v-else>
      <div class="space-y-3 md:hidden">
        <div
          v-for="task in filteredTasks"
          :key="`mobile-${task.task_id}`"
          class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
        >
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-slate-900">
                {{ task.app_name || task.config?.app?.name ||"-" }}
              </div>
              <code class="mt-1 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                {{ task.task_id.substring(0, 8) }}
              </code>
            </div>
            <Badge variant="info" class="shrink-0">
              <AppIcon  name="play-circle" class="mr-1" />{{ task.execution_count || 0 }} 次
            </Badge>
          </div>
          <div class="mt-2 flex flex-wrap gap-1">
            <Badge
              v-for="(target, idx) in task.config?.targets || []"
              :key="idx"
              variant="default"
            >
              {{ target.name || target.host_name ||"-" }}
            </Badge>
          </div>
          <dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-slate-600">
            <dt>创建</dt>
            <dd>{{ formatTime(task.created_at) }}</dd>
            <dt>最后触发</dt>
            <dd>
              {{ formatTime(task.last_executed_at) ||"—" }}
              <span v-if="task.status?.trigger_source" class="ml-1 text-slate-500">
                <span v-if="task.status.trigger_source === 'webhook'">Webhook</span>
                <span v-else-if="task.status.trigger_source === 'manual'">手动</span>
                <span v-else-if="task.status.trigger_source === 'cron'">定时</span>
                <span v-else>{{ task.status.trigger_source }}</span>
              </span>
            </dd>
          </dl>
          <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3">
            <Button variant="outline" size="sm" @click="viewTask(task)" title="查看详情">
              <AppIcon  name="eye" />
            </Button>
            <Button variant="outline" size="sm" @click="executeTask(task)" title="触发部署">
              <AppIcon  name="play" />
              <span class="ml-1">触发</span>
            </Button>
            <Button
              v-if="task.execution_count > 0"
              variant="outline"
              size="sm"
              @click="viewExecutions(task)"
              title="执行历史"
            >
              <AppIcon  name="history" />
            </Button>
            <Button
              v-if="task.webhook_token"
              variant="outline"
              size="sm"
              @click="showWebhookUrl(task)"
              title="Webhook"
            >
              <AppIcon  name="link" />
            </Button>
            <Button variant="outline" size="sm" @click="editTask(task)" title="编辑">
              <AppIcon  name="edit" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              title="成员授权"
              @click="openResourcePermission(task)"
            >
              <AppIcon  name="user-shield" />
            </Button>
            <Button variant="outline" size="sm" @click="copyTask(task)" title="复制">
              <AppIcon  name="copy" />
            </Button>
            <Button variant="destructive" size="sm" @click="deleteTask(task)" title="删除">
              <AppIcon  name="trash" />
            </Button>
          </div>
        </div>
      </div>

      <div class="hidden md:block">
        <Table min-width-class="min-w-[64rem]">
          <TableHeader>
        <TableRow>
          <TableHead class="w-[8%]">配置ID</TableHead>
          <TableHead class="w-[12%]">应用名称</TableHead>
          <TableHead class="w-[10%]">目标主机</TableHead>
          <TableHead class="w-[8%]">触发次数</TableHead>
          <TableHead class="w-[12%]">创建时间</TableHead>
          <TableHead class="w-[12%]">最后触发</TableHead>
          <TableHead class="w-[38%]">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="task in filteredTasks" :key="task.task_id">
          <TableCell>
            <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{{ task.task_id.substring(0, 8) }}</code>
          </TableCell>
          <TableCell>{{ task.app_name || task.config?.app?.name ||"-" }}</TableCell>
          <TableCell>
            <Badge v-for="(target, idx) in task.config?.targets || []" :key="idx" variant="default" class="mr-1">
              {{ target.name || target.host_name ||"-" }}
            </Badge>
          </TableCell>
          <TableCell>
            <Badge variant="info" class="mr-1">
              <AppIcon  name="play-circle" class="mr-1" />{{ task.execution_count || 0 }}
            </Badge>
            <Button v-if="task.execution_count > 0" variant="ghost" size="sm" class="h-auto p-0 text-xs" @click="viewExecutions(task)" title="查看执行历史">
              <AppIcon  name="external-link-alt" />
            </Button>
          </TableCell>
          <TableCell class="whitespace-nowrap text-sm text-slate-600">{{ formatTime(task.created_at) }}</TableCell>
          <TableCell>
            <div class="flex flex-col">
              <span class="text-sm">{{ formatTime(task.last_executed_at) ||"-" }}</span>
              <span v-if="task.status?.trigger_source" class="text-xs text-slate-500">
                <span v-if="task.status.trigger_source === 'webhook'"><AppIcon  name="link" class="text-green-600 mr-1" /> Webhook</span>
                <span v-else-if="task.status.trigger_source === 'manual'"><AppIcon  name="user" class="text-blue-600 mr-1" /> 手动</span>
                <span v-else-if="task.status.trigger_source === 'cron'"><AppIcon  name="clock" class="text-amber-600 mr-1" /> 定时</span>
                <span v-else><AppIcon  name="question-circle" class="text-slate-400 mr-1" />{{ task.status.trigger_source }}</span>
              </span>
            </div>
          </TableCell>
          <TableCell>
            <div class="flex flex-wrap gap-1">
              <Button variant="outline" size="sm" @click="viewTask(task)" title="查看详情"><AppIcon  name="eye" /></Button>
              <Button variant="outline" size="sm" @click="executeTask(task)" title="触发部署（将创建新任务）"><AppIcon  name="play" /> 触发</Button>
              <Button v-if="task.webhook_token" variant="outline" size="sm" @click="showWebhookUrl(task)" title="查看 Webhook URL"><AppIcon  name="link" /></Button>
              <Button variant="outline" size="sm" @click="editTask(task)" title="编辑配置"><AppIcon  name="edit" /></Button>
              <Button variant="outline" size="sm" title="成员授权" @click="openResourcePermission(task)"><AppIcon  name="user-shield" /></Button>
              <Button variant="outline" size="sm" @click="copyTask(task)" title="复制配置"><AppIcon  name="copy" /></Button>
              <Button variant="destructive" size="sm" @click="deleteTask(task)" title="删除配置"><AppIcon  name="trash" /></Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
        </Table>
      </div>
    </div>

    <PaginationBar
      v-if="!loading && totalTasks > pageSize"
      :page="currentPage"
      :page-size="pageSize"
      :total="totalTasks"
      :total-pages="totalPages"
      @update:page="goToPage"
    />

    <FormDialog
      :model-value="showSimpleCreateModal"
      title="快速创建部署任务"
      icon="rocket"
      size="xl"
      @update:model-value="(v) => !v && (closeSimpleCreateModal())"
    >
      <!-- 应用基本信息 -->
            <div class="mb-3">
              <Label>应用名称 <span class="text-red-500">*</span></Label>
              <Input
                v-model="simpleForm.appName"
                type="text"
                :class="{
                  'is-invalid':
                    simpleForm.appName &&
                    isAppNameDuplicate(simpleForm.appName.trim(), null),
                }"
                placeholder="my-app"
                @blur="checkAppNameDuplicate(simpleForm.appName.trim(), null)"
              />
              <div
                v-if="
                  simpleForm.appName &&
                  isAppNameDuplicate(simpleForm.appName.trim(), null)"
                class="mt-1 block text-xs text-red-500"
              >
                应用名称已存在，请使用其他名称
              </div>
            </div>

            <!-- Portainer 目标主机（前置，便于先选主机再选 Stack） -->
            <div v-if="simpleForm.deployChannel === 'portainer'" class="mb-3">
              <Label>Portainer 目标主机 <span class="text-red-500">*</span></Label>
              <NativeSelect
                v-model="simpleForm.portainerTargetHost"
              >
                <option :value="null" disabled>请选择 Portainer 主机</option>
                <option
                  v-for="host in createPortainerHosts"
                  :key="`top-portainer-${host.host_id}`"
                  :value="host.host_id"
                >
                  {{ host.name }} ({{ host.portainer_url ||"-" }})
                </option>
              </NativeSelect>
            </div>

            <!-- 统一部署配置 -->
            <div class="mb-3 rounded-lg border border-slate-200 bg-white">
              <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                <h6 class="text-sm font-semibold text-slate-900">
                  <AppIcon  name="cogs" class="mr-2" />
                  部署配置（统一配置，适用于所有目标主机）
                </h6>
              </div>
              <div class="p-4">
                <div class="mb-3">
                  <Label>发布通道 <span class="text-red-500">*</span></Label>
                  <div class="flex w-full flex-wrap gap-2" role="group">
                    <input
                      v-if="canUseCreateChannel('agent')"
                      type="radio"
                      class="choice-input"
                      id="channel-agent"
                      v-model="simpleForm.deployChannel"
                      value="agent"
                    />
                    <label
                      v-if="canUseCreateChannel('agent')"
                      class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="channel-agent"
                    >
                      Agent 发布
                    </label>
                    <input
                      v-if="canUseCreateChannel('ssh')"
                      type="radio"
                      class="choice-input"
                      id="channel-ssh"
                      v-model="simpleForm.deployChannel"
                      value="ssh"
                    />
                    <label
                      v-if="canUseCreateChannel('ssh')"
                      class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="channel-ssh"
                    >
                      SSH 发布
                    </label>
                    <input
                      v-if="canUseCreateChannel('portainer')"
                      type="radio"
                      class="choice-input"
                      id="channel-portainer"
                      v-model="simpleForm.deployChannel"
                      value="portainer"
                    />
                    <label
                      v-if="canUseCreateChannel('portainer')"
                      class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="channel-portainer"
                    >
                      Portainer 发布
                    </label>
                  </div>
                </div>

                <div v-if="simpleForm.deployChannel !== 'portainer'" class="mb-3">
                  <Label>部署方式 <span class="text-red-500">*</span></Label>
                  <div class="flex w-full flex-wrap gap-2" role="group">
                    <input
                      type="radio"
                      class="choice-input"
                      id="deploy-run"
                      v-model="simpleForm.deployMode"
                      value="docker_run"
                      checked
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="deploy-run">
                      <AppIcon  name="terminal" class="mr-1" /> Docker Run
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="deploy-compose"
                      v-model="simpleForm.deployMode"
                      value="docker_compose"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="deploy-compose">
                      <AppIcon  name="layer-group" class="mr-1" /> Docker Compose
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="deploy-multi-step"
                      v-model="simpleForm.deployMode"
                      value="multi_step"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="deploy-multi-step">
                      <AppIcon  name="list-ol" class="mr-1" /> 多步骤
                    </label>
                  </div>
                </div>


                <!-- Docker Run 命令输入 -->
                <div v-if="simpleForm.deployMode === 'docker_run'" class="mb-3">
                  <Label>Docker Run 命令 <span class="text-red-500">*</span></Label>
                  <textarea
                    v-model="simpleForm.runCommand"
                    class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    rows="6"
                    placeholder="-d --name my-app -p 8000:8000 registry.cn-hangzhou.aliyuncs.com/namespace/app:tag"
                  ></textarea>
                </div>

                <!-- Docker Compose 模式选择 -->
                <div
                  v-if="
                    simpleForm.deployMode === 'docker_compose' &&
                    simpleForm.deployChannel !== 'portainer'"
                  class="mb-3"
                >
                  <Label>Compose 部署模式 <span class="text-red-500">*</span></Label>
                  <div class="flex w-full flex-wrap gap-2" role="group">
                    <input
                      type="radio"
                      class="choice-input"
                      id="compose-mode-compose"
                      v-model="simpleForm.composeMode"
                      value="docker-compose"
                      :disabled="!isComposeModeSupported('docker-compose')"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      :class="{
                        disabled: !isComposeModeSupported('docker-compose'),
                      }"
                      for="compose-mode-compose"
                      :title="
                        !isComposeModeSupported('docker-compose')
                          ? '所选主机不支持 docker-compose 模式'
                          : ''"
                    >
                      <AppIcon  name="layer-group" class="mr-1" /> docker-compose
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="compose-mode-stack"
                      v-model="simpleForm.composeMode"
                      value="docker-stack"
                      :disabled="!isComposeModeSupported('docker-stack')"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      :class="{
                        disabled: !isComposeModeSupported('docker-stack'),
                      }"
                      for="compose-mode-stack"
                      :title="
                        !isComposeModeSupported('docker-stack')
                          ? '所选主机不支持 docker stack 模式（需要 Docker Swarm）'
                          : ''"
                    >
                      <AppIcon  name="server" class="mr-1" /> docker stack deploy
                    </label>
                  </div>
                  <small
                    v-if="
                      !isComposeModeSupported('docker-compose') &&
                      !isComposeModeSupported('docker-stack')"
                    class="text-amber-600 block mt-1"
                  >
                    <AppIcon  name="exclamation-triangle" class="mr-1" />
                    所选主机不支持任何 Compose 模式，请选择其他主机或使用 Docker
                    Run 模式
                  </small>
                </div>

                <!-- 重新发布策略选择 -->
                <div
                  v-if="simpleForm.deployMode === 'docker_compose'"
                  class="mb-3"
                >
                  <div v-if="simpleForm.deployChannel === 'portainer'" class="mb-2">
                    <Label>Stack 部署策略</Label>
                    <div class="flex w-full flex-wrap gap-2" role="group">
                      <input
                        type="radio"
                        class="choice-input"
                        id="stack-create"
                        v-model="simpleForm.stackStrategy"
                        value="create_new"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="stack-create">
                        创建新 Stack
                      </label>
                      <input
                        type="radio"
                        class="choice-input"
                        id="stack-update"
                        v-model="simpleForm.stackStrategy"
                        value="update_existing"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="stack-update">
                        更新已有 Stack
                      </label>
                    </div>
                    <div
                      v-if="simpleForm.stackStrategy === 'update_existing'"
                      class="mt-2"
                    >
                      <Label class="text-xs">选择已有 Stack</Label>
                      <div class="flex gap-2">
                        <NativeSelect
                          v-model="simpleForm.selectedStackId"
                          :disabled="
                            loadingStacks ||
                            !simpleForm.portainerTargetHost ||
                            availableStacks.length === 0"
                        >
                          <option :value="null" disabled>请选择 Stack</option>
                          <option
                            v-for="stack in availableStacks"
                            :key="stack.id"
                            :value="stack.id"
                          >
                            {{ stack.name }} (ID: {{ stack.id }})
                          </option>
                        </NativeSelect>
                        <Button
                          type="button"
                          variant="outline"
                          @click="loadAvailableStacks"
                          :disabled="loadingStacks"
                          title="刷新 Stack 列表"
                        >
                          <AppIcon
                            v-if="loadingStacks"
                            
                           name="spinner" spin />
                          <AppIcon v-else  name="sync-alt" />
                        </Button>
                      </div>
                      <small class="text-slate-500 block mt-1">
                        <span v-if="!simpleForm.portainerTargetHost">
                          请先选择 Portainer 目标主机
                        </span>
                        <span v-else>已加载 {{ availableStacks.length }} 个 Stack</span>
                      </small>
                    </div>
                    <div v-else class="mt-2">
                      <Label class="text-xs">新 Stack 名称 <span class="text-red-500">*</span></Label>
                      <Input
                        v-model="simpleForm.newStackName"
                        type="text"
                        placeholder="请输入要创建的 Stack 名称"
                      />
                    </div>
                  </div>
                  <Label v-if="simpleForm.deployChannel !== 'portainer'">重新发布策略</Label>
                  <div class="flex w-full flex-wrap gap-2" role="group">
                    <input
                      type="radio"
                      class="choice-input"
                      id="redeploy-strategy-remove"
                      v-model="simpleForm.redeployStrategy"
                      value="remove_and_redeploy"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="redeploy-strategy-remove"
                    >
                      <AppIcon  name="trash-alt" class="mr-1" /> 删除后重新部署
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="redeploy-strategy-update"
                      v-model="simpleForm.redeployStrategy"
                      value="update_existing"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="redeploy-strategy-update"
                    >
                      <AppIcon  name="sync-alt" class="mr-1" /> 直接更新
                    </label>
                  </div>
                </div>

                <!-- Docker Compose 命令输入 -->
                <div
                  v-if="
                    simpleForm.deployMode === 'docker_compose' &&
                    simpleForm.deployChannel !== 'portainer'"
                  class="mb-3"
                >
                  <Label><span v-if="simpleForm.composeMode === 'docker-compose'"
                      >Docker Compose 命令</span
                    >
                    <span v-else>Docker Stack 命令</span>
                    <span class="text-red-500">*</span>
                  </Label>
                  <Input
                    v-model="simpleForm.composeCommand"
                    type="text"
                    :placeholder="
                      simpleForm.composeMode === 'docker-compose'
                        ? 'up -d'
                        : '-c docker-compose.yml'"
                  />
                </div>

                <div
                  v-if="simpleForm.deployMode === 'docker_compose'"
                  class="mb-3"
                >
                  <Label>docker-compose.yml 内容
                    <span class="text-red-500">*</span></Label>
                  <textarea
                    v-model="simpleForm.composeContent"
                    class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    rows="15"
                    placeholder="version: '3.8'&#10;services:&#10;  app:&#10;    image: registry.cn-hangzhou.aliyuncs.com/namespace/app:tag&#10;    ports:&#10;      - '8000:8000'"
                  ></textarea>
                </div>

                <!-- 多步骤配置 -->
                <div v-if="simpleForm.deployMode === 'multi_step'" class="mb-3">
                  <div
                    class="flex justify-between items-center mb-2"
                  >
                    <div>
                      <Label class="mb-0">部署步骤 <span class="text-red-500">*</span></Label>
                    </div>
                    <Button
                      type="button"
                      variant="outline" size="sm"
                      @click="addStep"
                    >
                      <AppIcon  name="plus" class="mr-1" /> 添加步骤
                    </Button>
                  </div>

                  <div
                    v-if="simpleForm.steps.length === 0"
                    class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900"
                  >
                    <AppIcon  name="info-circle" class="mr-1" />
                    请至少添加一个部署步骤
                  </div>

                  <div v-else class="steps-list">
                    <div
                      v-for="(step, index) in simpleForm.steps"
                      :key="index"
                      class="mb-2 rounded-lg border border-slate-200 p-4"
                      :class="{ 'border-blue-300': step.name || step.command }"
                    >
                      <div class="p-4">
                        <div
                          class="flex justify-between items-start mb-2"
                        >
                          <div class="flex items-center">
                            <span
                              class="mr-2"
                              style="min-width: 60px"
                              >步骤 {{ index + 1 }}</span
                            >
                            <span v-if="step.name" class="text-slate-500 text-sm">{{
                              step.name
                            }}</span>
                            <span v-else class="text-slate-500 text-sm fst-italic"
                              >未命名步骤</span
                            >
                          </div>
                          <div class="inline-flex items-stretch text-sm">
                            <Button
                              type="button"
                              variant="outline"
                              @click="moveStep(index, -1)"
                              :disabled="index === 0"
                              title="上移"
                            >
                              <AppIcon  name="arrow-up" />
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              @click="moveStep(index, 1)"
                              :disabled="index === simpleForm.steps.length - 1"
                              title="下移"
                            >
                              <AppIcon  name="arrow-down" />
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              @click="removeStep(index)"
                              title="删除步骤"
                            >
                              <AppIcon  name="trash" />
                            </Button>
                          </div>
                        </div>
                        <div class="mb-2">
                          <Label class="mb-1 text-xs">步骤名称</Label>
                          <Input
                            v-model="step.name"
                            type="text"
                            placeholder="例如：停止旧容器、拉取镜像、启动容器"
                          />
                        </div>
                        <div>
                          <Label class="mb-1 text-xs">执行命令</Label>
                          <textarea
                            v-model="step.command"
                            class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 text-xs"
                            rows="4"
                            placeholder="docker stop my-app || true&#10;或&#10;docker pull registry.cn-hangzhou.aliyuncs.com/namespace/app:latest"
                          ></textarea>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="simpleForm.deployChannel !== 'portainer'" class="mb-0">
                  <div class="flex items-center gap-2">
                    <input
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      id="redeploySwitch"
                      v-model="simpleForm.redeploy"
                    />
                    <label class="text-sm text-slate-700" for="redeploySwitch">
                      <AppIcon  name="redo" class="mr-1" />
                      重新发布（如果主机上已存在，先停止并删除）
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <!-- 目标主机选择 -->
            <div v-if="simpleForm.deployChannel !== 'portainer'" class="mb-3 min-w-0">
              <Label>选择目标主机 <span class="text-red-500">*</span></Label>
              <div
                v-if="selectedHostEntries('simple').length > 0"
                class="mb-2 flex flex-wrap items-center gap-2"
              >
                <span
                  v-for="entry in selectedHostEntries('simple')"
                  :key="entry.id"
                  class="inline-flex max-w-full items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-sm text-blue-800"
                >
                  <span class="break-all">{{ entry.name }}</span>
                  <button
                    type="button"
                    class="inline-flex min-h-8 min-w-8 shrink-0 items-center justify-center rounded text-blue-600 hover:bg-blue-100"
                    :aria-label="`移除 ${entry.name}`"
                    @click="removeSelectedHost('simple', entry.id)"
                  >
                    <AppIcon  name="times" />
                  </button>
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  class="w-full sm:w-auto"
                  @click="clearSelectedHosts('simple')"
                >
                  清空
                </Button>
              </div>
              <div v-if="false" class="mb-2">
                <Label class="text-xs">Portainer 目标主机</Label>
                <NativeSelect
                  v-model="simpleForm.portainerTargetHost"
                >
                  <option :value="null" disabled>请选择 Portainer 主机</option>
                  <option
                    v-for="host in channelFilteredHostsByType.portainer"
                    :key="host.host_id"
                    :value="host.host_id"
                  >
                    {{ host.name }} ({{ host.portainer_url ||"-" }})
                  </option>
                </NativeSelect>
              </div>

              <!-- 主机类型筛选和搜索 -->
              <div v-if="simpleForm.deployChannel !== 'portainer'" class="mb-2">
                <div class="inline-flex items-stretch text-sm mb-2" role="group">
                  <template v-if="simpleForm.deployChannel !== 'portainer'">
                    <input
                      type="radio"
                      class="choice-input"
                      id="filter-all"
                      v-model="hostFilter"
                      value="all"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="filter-all"
                      >全部</label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="filter-agent"
                      v-model="hostFilter"
                      value="agent"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="filter-agent">
                      <AppIcon  name="network-wired" class="mr-1" /> Agent
                    </label>
                  </template>

                  <input
                    type="radio"
                    class="choice-input"
                    id="filter-portainer"
                    v-model="hostFilter"
                    value="portainer"
                    :disabled="simpleForm.deployChannel !== 'portainer'"
                  />
                  <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                    for="filter-portainer"
                    :class="{ disabled: simpleForm.deployChannel !== 'portainer' }"
                  >
                    <AppIcon  name="server" class="mr-1" /> Portainer
                  </label>

                  <template v-if="simpleForm.deployChannel !== 'portainer'">
                    <input
                      type="radio"
                      class="choice-input"
                      id="filter-ssh"
                      v-model="hostFilter"
                      value="ssh"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="filter-ssh">
                      <AppIcon  name="terminal" class="mr-1" /> SSH
                    </label>
                  </template>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex items-center gap-2">
                    <input
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      id="filter-online"
                      v-model="filterOnlineOnly"
                    />
                    <label class="text-sm text-slate-700" for="filter-online"
                      >仅在线</label>
                  </div>
                  <Input
                    type="text"
                    v-model="hostSearchKeyword"
                    placeholder="搜索主机名称..."
                  />
                </div>
              </div>

              <!-- 主机列表（按类型分组） -->
              <div
                v-if="loadingHosts"
                class="text-slate-500 text-sm text-center py-3"
              >
                <AppIcon  name="spinner" class="mr-2" spin />加载中...
              </div>
              <div
                v-else
                class="border rounded p-2"
                style="max-height: 300px; overflow-y: auto"
                v-show="simpleForm.deployChannel !== 'portainer'"
              >
                <!-- Agent 主机 -->
                <div v-if="channelFilteredHostsByType.agent.length > 0" class="mb-3">
                  <div class="font-semibold text-blue-600 mb-2">
                    <AppIcon  name="network-wired" class="mr-1" /> Agent 主机 ({{
                      channelFilteredHostsByType.agent.length
                    }})
                  </div>
                  <div
                    v-for="host in channelFilteredHostsByType.agent"
                    :key="host.host_id"
                    class="flex items-center gap-2 ml-3"
                  >
                    <input
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :checked="isHostSelected('simple', host.host_id)"
                      @change="onHostToggle('simple', host.host_id, $event)"
                    />
                    <label
                      class="text-sm text-slate-700"
                      :for="`host-${host.host_id}`"
                    >
                      {{ host.name }}
                      <Badge :variant="host.status === 'completed' ? 'success' : host.status === 'failed' ? 'danger' : host.status === 'running' ? 'info' : 'default'" class="ml-1">
                        {{ getStatusText(host.status) }}
                      </Badge>
                      <span
                        v-if="host.description"
                        class="text-slate-500 text-sm ml-1"
                        >({{ host.description }})</span
                      >
                    </label>
                  </div>
                </div>

                <!-- Portainer 主机 -->
                <div
                  v-if="channelFilteredHostsByType.portainer.length > 0"
                  class="mb-3"
                >
                  <div class="font-semibold text-info mb-2">
                    <AppIcon  name="server" class="mr-1" /> Portainer 主机 ({{
                      channelFilteredHostsByType.portainer.length
                    }})
                  </div>
                  <div
                    v-for="host in channelFilteredHostsByType.portainer"
                    :key="host.host_id"
                    class="flex items-center gap-2 ml-3"
                  >
                    <input
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :checked="isHostSelected('simple', host.host_id)"
                      @change="onHostToggle('simple', host.host_id, $event)"
                    />
                    <label
                      class="text-sm text-slate-700"
                      :for="`host-${host.host_id}`"
                    >
                      {{ host.name }}
                      <Badge :variant="host.status === 'completed' ? 'success' : host.status === 'failed' ? 'danger' : host.status === 'running' ? 'info' : 'default'" class="ml-1">
                        {{ getStatusText(host.status) }}
                      </Badge>
                      <span
                        v-if="host.portainer_url"
                        class="text-slate-500 text-sm ml-1"
                        >({{ host.portainer_url }})</span
                      >
                    </label>
                  </div>
                </div>

                <!-- SSH 主机 -->
                <div v-if="channelFilteredHostsByType.ssh.length > 0" class="mb-3">
                  <div class="font-semibold text-amber-600 mb-2">
                    <AppIcon  name="terminal" class="mr-1" /> SSH 主机 ({{
                      channelFilteredHostsByType.ssh.length
                    }})
                  </div>
                  <div
                    v-for="host in channelFilteredHostsByType.ssh"
                    :key="host.host_id"
                    class="flex items-center gap-2 ml-3"
                  >
                    <input
                      class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :checked="isHostSelected('simple', host.host_id)"
                      @change="onHostToggle('simple', host.host_id, $event)"
                    />
                    <label
                      class="text-sm text-slate-700"
                      :for="`host-${host.host_id}`"
                    >
                      {{ host.name }}
                      <Badge v-if="host.docker_enabled" variant="info" class="ml-1">Docker</Badge>
                      <span
                        v-if="host.docker_version"
                        class="text-slate-500 text-sm ml-1"
                        >({{ host.docker_version }})</span
                      >
                      <span v-if="host.host" class="text-slate-500 text-sm ml-1"
                        >@{{ host.host }}:{{ host.port || 22 }}</span
                      >
                    </label>
                  </div>
                </div>

                <div
                  v-if="filteredHosts.length === 0"
                  class="text-slate-500 text-sm text-center py-3"
                >
                  <AppIcon  name="inbox" class="mr-1" />
                  <span v-if="hostSearchKeyword">未找到匹配的主机</span>
                  <span v-else>暂无可用主机，请先在"主机管理"中添加主机</span>
                </div>
              </div>

              <p
                v-if="selectedHostEntries('simple').length > 0"
                class="mt-2 text-slate-500 text-sm"
              >
                已选择 <strong>{{ selectedHostEntries('simple').length }}</strong> 个主机（可在上方标签移除）
              </p>
            </div>
      <template #footer>
        <Button
              type="button"
              variant="secondary"
              @click="closeSimpleCreateModal"
            >
              取消
            </Button>
            <Button
              type="button"
              variant="default"
              @click="createSimpleTask"
              :disabled="creating"
            >
              <AppIcon v-if="creating"  name="spinner" class="mr-2" spin />
              创建
            </Button>
      </template>
    </FormDialog>
    <FormDialog
      :model-value="showCreateModal"
      title="YAML方式创建部署任务"
      icon="code"
      size="lg"
      @update:model-value="(v) => !v && (showCreateModal = false)"
    >
      <div class="mb-3">
              <Label>YAML 配置内容</Label>
              <textarea
                v-model="taskConfigContent"
                class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                rows="20"
                placeholder="请输入 deploy-config.yaml 格式的配置..."
              ></textarea>
            </div>
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div class="">
                <Label>镜像仓库（可选）</Label>
                <Input
                  v-model="taskRegistry"
                  type="text"
                  placeholder="docker.io"
                />
              </div>
              <div class="">
                <Label>镜像标签（可选）</Label>
                <Input
                  v-model="taskTag"
                  type="text"
                  placeholder="latest"
                />
              </div>
            </div>
      <template #footer>
        <Button
              type="button"
              variant="secondary"
              @click="showCreateModal = false"
            >
              取消
            </Button>
            <Button
              type="button"
              variant="default"
              @click="createTask"
              :disabled="creating"
            >
              <AppIcon v-if="creating"  name="spinner" class="mr-2" spin />
              创建
            </Button>
      </template>
    </FormDialog>
    <FormDialog
      :model-value="showImportModal"
      title="导入部署配置"
      icon="file-import"
      size="md"
      @update:model-value="(v) => !v && (showImportModal = false)"
    >
      <div class="mb-3">
              <Label>选择 YAML 文件</Label>
              <input
                type="file"
                class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                @change="handleFileImport"
                accept=".yaml,.yml"
              />
            </div>
      <template #footer>
        <Button
              type="button"
              variant="secondary"
              @click="showImportModal = false"
            >
              取消
            </Button>
      </template>
    </FormDialog>
    <FormDialog
      :model-value="showDetailModal && selectedTask"
      :title="'任务详情 - ' + (selectedTask?.task_id?.substring(0, 8) || '')"
      icon="info-circle"
      size="xl"
      @update:model-value="(v) => !v && (showDetailModal = false)"
    >
      <div class="mb-3 flex gap-1 border-b border-slate-200">
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="detailTab === 'config' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="detailTab = 'config'"
                >
                  <AppIcon  name="cog" class="mr-1" /> 配置信息
                </Button>
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="detailTab === 'status' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="detailTab = 'status'"
                >
                  <AppIcon  name="tasks" class="mr-1" /> 执行状态
                </Button>
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="detailTab === 'logs' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="detailTab = 'logs'"
                >
                  <AppIcon  name="file-alt" class="mr-1" /> 执行日志
                </Button>
            </div>

            <div v-if="detailTab === 'config'">
              <pre
                class="max-h-[500px] overflow-y-auto rounded-lg bg-slate-900 p-3 text-slate-100"
                style="max-height: 500px; overflow-y: auto"
              ><code>{{ selectedTask.config_content || selectedTask.task_config?.config_content || '' }}</code></pre>
            </div>

            <div v-if="detailTab === 'status'">
              <div class="mb-3">
                <strong>任务状态:</strong>
                <Badge
                  :variant="selectedTask.status === 'completed' ? 'success' : selectedTask.status === 'failed' ? 'danger' : selectedTask.status === 'running' ? 'info' : 'default'"
                  class="ml-2"
                >
                  {{ getStatusText(selectedTask.status) }}
                </Badge>
                <span
                  v-if="selectedTask.created_at"
                  class="text-slate-500 text-sm ml-3"
                >
                  创建时间: {{ formatTime(selectedTask.created_at) }}
                </span>
                <span
                  v-if="selectedTask.completed_at"
                  class="text-slate-500 text-sm ml-3"
                >
                  完成时间: {{ formatTime(selectedTask.completed_at) }}
                </span>
              </div>
              <div v-if="selectedTask.error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 mb-3">
                <strong>错误信息:</strong> {{ selectedTask.error }}
              </div>
              <div v-if="selectedTask.config?.targets" class="mb-3">
                <strong>目标主机配置:</strong>
                <table class="mt-2 w-full border-collapse text-sm">
                  <thead>
                    <tr>
                      <th>主机名称</th>
                      <th>主机类型</th>
                      <th>配置</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="target in selectedTask.config.targets"
                      :key="target.name"
                    >
                      <td>{{ target.name || target.host_name ||"-" }}</td>
                      <td>
                        <Badge variant="info">{{ target.host_type || target.mode ||"-" }}</Badge>
                      </td>
                      <td>
                        <small class="text-slate-500">{{
                          target.host_name ||
                          target.host ||
                          target.agent?.name ||"-"
                        }}</small>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- 执行日志标签页 -->
            <div v-if="detailTab === 'logs'">
              <div
                class="mb-2 flex justify-between items-center"
              >
                <strong>执行日志</strong>
                <Button
                  variant="outline" size="sm"
                  @click="refreshTask(selectedTask)"
                  title="刷新日志"
                >
                  <AppIcon  name="sync-alt" class="mr-1" /> 刷新
                </Button>
              </div>

              <div v-if="taskLogs && taskLogs.length > 0">
                <div
                  class="max-h-[600px] overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100"
                  style="
                    max-height: 600px;
                    overflow-y: auto;
                    font-size: 12px;"
                >
                  <div
                    v-for="(log, idx) in taskLogs"
                    :key="idx"
                    class="log-line mb-1"
                    :class="getLogLineClass(log)"
                  >
                    <span class="text-slate-500"
                      >[{{ formatTime(log.log_time) }}]</span
                    >
                    <span
                      class="ml-2"
                      v-html="formatLogMessage(log.log_message)"
                    ></span>
                  </div>
                </div>
              </div>

              <div v-else class="text-slate-500 text-center py-4">
                <AppIcon  name="info-circle" class="mr-1" />
                暂无执行日志
              </div>
            </div>
      <template #footer>
        <Button
              type="button"
              variant="secondary"
              @click="showDetailModal = false"
            >
              关闭
            </Button>
            <Button
              variant="outline"
              @click="editTask(selectedTask)"
            >
              <AppIcon  name="edit" class="mr-1" /> 编辑
            </Button>
            <Button
              variant="outline"
              @click="copyTask(selectedTask)"
            >
              <AppIcon  name="copy" class="mr-1" /> 复制
            </Button>
            <Button
              variant="default"
              @click="executeTask(selectedTask)"
              :disabled="selectedTask.status === 'running'"
            >
              <AppIcon  name="play" class="mr-1" />
              {{ selectedTask.status ==="running" ?"执行中..." :"执行任务" }}
            </Button>
      </template>
    </FormDialog>
    <FormDialog
      :model-value="showEditModal && editingTask"
      :title="'编辑部署任务 - ' + (editingTask?.task_id?.substring(0, 8) || '')"
      icon="edit"
      size="xl"
      @update:model-value="(v) => !v && (closeEditModal())"
    >
      <!-- 编辑方式切换标签页 -->
            <div class="mb-3 flex gap-1 border-b border-slate-200">
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="editMode === 'form' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="editMode = 'form'"
                >
                  <AppIcon  name="edit" class="mr-1" /> 表单编辑
                </Button>
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="editMode === 'yaml' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="switchToYamlMode"
                >
                  <AppIcon  name="code" class="mr-1" /> YAML编辑
                </Button>
              <Button
                  type="button"
                  variant="ghost"
                  class="rounded-none border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"
                  :class="editMode === 'webhook' ? 'border-blue-600 text-blue-600' : 'border-transparent'"
                  @click="editMode = 'webhook'"
                >
                  <AppIcon  name="link" class="mr-1" /> Webhook设置
                </Button>
            </div>

            <!-- 表单编辑模式 -->
            <div v-if="editMode === 'form'">
              <!-- 应用基本信息 -->
              <div class="mb-3">
                <Label>应用名称 <span class="text-red-500">*</span></Label>
                <Input
                  v-model="editForm.appName"
                  type="text"
                  :class="{
                    'is-invalid':
                      editForm.appName &&
                      isAppNameDuplicate(
                        editForm.appName.trim(),
                        editingTask?.task_id
                      ),
                  }"
                  placeholder="my-app"
                  @blur="
                    checkAppNameDuplicate(
                      editForm.appName.trim(),
                      editingTask?.task_id
                    )"
                />
                <div
                  v-if="
                    editForm.appName &&
                    isAppNameDuplicate(
                      editForm.appName.trim(),
                      editingTask?.task_id
                    )"
                  class="mt-1 block text-xs text-red-500"
                >
                  应用名称已存在，请使用其他名称
                </div>
              </div>

              <!-- 统一部署配置 -->
              <div class="mb-3 rounded-lg border border-slate-200 bg-white">
                <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
                  <h6 class="text-sm font-semibold text-slate-900">
                    <AppIcon  name="cogs" class="mr-2" />
                    部署配置（统一配置，适用于所有目标主机）
                  </h6>
                </div>
                <div class="p-4">
                  <div class="mb-3">
                    <Label>发布通道 <span class="text-red-500">*</span></Label>
                    <div class="flex w-full flex-wrap gap-2" role="group">
                      <input
                        v-if="canUseEditChannel('agent')"
                        type="radio"
                        class="choice-input"
                        id="edit-channel-agent"
                        v-model="editForm.deployChannel"
                        value="agent"
                      />
                      <label
                        v-if="canUseEditChannel('agent')"
                        class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-channel-agent"
                      >
                        Agent 发布
                      </label>
                      <input
                        v-if="canUseEditChannel('ssh')"
                        type="radio"
                        class="choice-input"
                        id="edit-channel-ssh"
                        v-model="editForm.deployChannel"
                        value="ssh"
                      />
                      <label
                        v-if="canUseEditChannel('ssh')"
                        class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-channel-ssh"
                      >
                        SSH 发布
                      </label>
                      <input
                        v-if="canUseEditChannel('portainer')"
                        type="radio"
                        class="choice-input"
                        id="edit-channel-portainer"
                        v-model="editForm.deployChannel"
                        value="portainer"
                      />
                      <label
                        v-if="canUseEditChannel('portainer')"
                        class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-channel-portainer"
                      >
                        Portainer 发布
                      </label>
                    </div>
                  </div>


                  <div v-if="editForm.deployChannel !== 'portainer'" class="mb-3">
                    <Label>部署方式 <span class="text-red-500">*</span></Label>
                    <div class="flex w-full flex-wrap gap-2" role="group">
                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-deploy-run"
                        v-model="editForm.deployMode"
                        value="docker_run"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-deploy-run"
                      >
                        <AppIcon  name="terminal" class="mr-1" /> Docker Run
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-deploy-compose"
                        v-model="editForm.deployMode"
                        value="docker_compose"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-deploy-compose"
                      >
                        <AppIcon  name="layer-group" class="mr-1" /> Docker Compose
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-deploy-multi-step"
                        v-model="editForm.deployMode"
                        value="multi_step"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-deploy-multi-step"
                      >
                        <AppIcon  name="list-ol" class="mr-1" /> 多步骤
                      </label>
                    </div>
                  </div>

                  <!-- Docker Run 命令输入 -->
                  <div v-if="editForm.deployMode === 'docker_run'" class="mb-3">
                    <Label>Docker Run 命令 <span class="text-red-500">*</span></Label>
                    <textarea
                      v-model="editForm.runCommand"
                      class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                      rows="6"
                      placeholder="-d --name my-app -p 8000:8000 registry.cn-hangzhou.aliyuncs.com/namespace/app:tag"
                    ></textarea>
                  </div>

                  <!-- Docker Compose 模式选择 -->
                  <div
                    v-if="
                      editForm.deployMode === 'docker_compose' &&
                      editForm.deployChannel !== 'portainer'"
                    class="mb-3"
                  >
                    <Label>Compose 部署模式
                      <span class="text-red-500">*</span></Label>
                    <div class="flex w-full flex-wrap gap-2" role="group">
                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-compose-mode-compose"
                        v-model="editForm.composeMode"
                        value="docker-compose"
                        :disabled="
                          !isEditComposeModeSupported('docker-compose')"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        :class="{
                          disabled:
                            !isEditComposeModeSupported('docker-compose'),
                        }"
                        for="edit-compose-mode-compose"
                        :title="
                          !isEditComposeModeSupported('docker-compose')
                            ? '所选主机不支持 docker-compose 模式'
                            : ''"
                      >
                        <AppIcon  name="layer-group" class="mr-1" /> docker-compose
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-compose-mode-stack"
                        v-model="editForm.composeMode"
                        value="docker-stack"
                        :disabled="!isEditComposeModeSupported('docker-stack')"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        :class="{
                          disabled: !isEditComposeModeSupported('docker-stack'),
                        }"
                        for="edit-compose-mode-stack"
                        :title="
                          !isEditComposeModeSupported('docker-stack')
                            ? '所选主机不支持 docker stack 模式（需要 Docker Swarm）'
                            : ''"
                      >
                        <AppIcon  name="server" class="mr-1" /> docker stack deploy
                      </label>
                    </div>
                    <small
                      v-if="
                        !isEditComposeModeSupported('docker-compose') &&
                        !isEditComposeModeSupported('docker-stack')"
                      class="text-amber-600 block mt-1"
                    >
                      <AppIcon  name="exclamation-triangle" class="mr-1" />
                      所选主机不支持任何 Compose 模式，请选择其他主机或使用
                      Docker Run 模式
                    </small>
                  </div>

                  <!-- 重新发布策略选择 -->
                  <div v-if="editForm.deployMode === 'docker_compose'" class="mb-3">
                    <div v-if="editForm.deployChannel === 'portainer'" class="mb-2">
                      <Label>Stack 部署策略</Label>
                      <div class="flex w-full flex-wrap gap-2" role="group">
                        <input
                          type="radio"
                          class="choice-input"
                          id="edit-stack-create"
                          v-model="editForm.stackStrategy"
                          value="create_new"
                        />
                        <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="edit-stack-create">
                          创建新 Stack
                        </label>
                        <input
                          type="radio"
                          class="choice-input"
                          id="edit-stack-update"
                          v-model="editForm.stackStrategy"
                          value="update_existing"
                        />
                        <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50" for="edit-stack-update">
                          更新已有 Stack
                        </label>
                      </div>
                      <div v-if="editForm.stackStrategy === 'update_existing'" class="mt-2">
                        <Label class="text-xs">选择已有 Stack</Label>
                        <div class="flex gap-2">
                          <NativeSelect
                            v-model="editForm.selectedStackId"
                            :disabled="
                              loadingStacks ||
                              !editForm.portainerTargetHost ||
                              availableStacks.length === 0"
                          >
                            <option :value="null" disabled>请选择 Stack</option>
                            <option
                              v-for="stack in availableStacks"
                              :key="stack.id"
                              :value="stack.id"
                            >
                              {{ stack.name }} (ID: {{ stack.id }})
                            </option>
                          </NativeSelect>
                          <Button
                            type="button"
                            variant="outline"
                            @click="loadAvailableStacksForEdit"
                            :disabled="loadingStacks"
                          >
                            <AppIcon
                              v-if="loadingStacks"
                              
                             name="spinner" spin />
                            <AppIcon v-else  name="sync-alt" />
                          </Button>
                        </div>
                      </div>
                      <div v-else class="mt-2">
                        <Label class="text-xs">新 Stack 名称 <span class="text-red-500">*</span></Label>
                        <Input
                          v-model="editForm.newStackName"
                          type="text"
                          placeholder="请输入要创建的 Stack 名称"
                        />
                      </div>
                    </div>
                    <Label v-if="editForm.deployChannel !== 'portainer'">重新发布策略</Label>
                    <div class="flex w-full flex-wrap gap-2" role="group">
                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-redeploy-strategy-remove"
                        v-model="editForm.redeployStrategy"
                        value="remove_and_redeploy"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-redeploy-strategy-remove"
                      >
                        <AppIcon  name="trash-alt" class="mr-1" /> 删除后重新部署
                      </label>

                      <input
                        type="radio"
                        class="choice-input"
                        id="edit-redeploy-strategy-update"
                        v-model="editForm.redeployStrategy"
                        value="update_existing"
                      />
                      <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                        for="edit-redeploy-strategy-update"
                      >
                        <AppIcon  name="sync-alt" class="mr-1" /> 直接更新
                      </label>
                    </div>
                    <small
                      v-if="editForm.deployChannel !== 'portainer'"
                      class="text-slate-500 block mt-1"
                    >
                      <span
                        v-if="
                          editForm.redeployStrategy === 'remove_and_redeploy'"
                      >
                        <span v-if="editForm.composeMode === 'docker-compose'"
                          >先执行 docker-compose down，然后重新部署</span
                        >
                        <span v-else>先执行 docker stack rm，然后重新部署</span>
                      </span>
                      <span v-else>
                        <span v-if="editForm.composeMode === 'docker-compose'"
                          >直接执行 docker-compose up -d（自动更新）</span
                        >
                        <span v-else
                          >直接执行 docker stack deploy（自动更新）</span
                        >
                      </span>
                    </small>
                  </div>

                  <!-- Docker Compose 命令输入 -->
                  <div
                    v-if="
                      editForm.deployMode === 'docker_compose' &&
                      editForm.deployChannel !== 'portainer'"
                    class="mb-3"
                  >
                    <Label><span v-if="editForm.composeMode === 'docker-compose'"
                        >Docker Compose 命令</span
                      >
                      <span v-else>Docker Stack 命令</span>
                      <span class="text-red-500">*</span>
                    </Label>
                    <Input
                      v-model="editForm.composeCommand"
                      type="text"
                      :placeholder="
                        editForm.composeMode === 'docker-compose'
                          ? 'up -d'
                          : '-c docker-compose.yml'"
                    />
                  </div>

                  <div
                    v-if="editForm.deployMode === 'docker_compose'"
                    class="mb-3"
                  >
                    <Label>docker-compose.yml 内容
                      <span class="text-red-500">*</span></Label>
                    <textarea
                      v-model="editForm.composeContent"
                      class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                      rows="15"
                      placeholder="version: '3.8'&#10;services:&#10;  app:&#10;    image: registry.cn-hangzhou.aliyuncs.com/namespace/app:tag&#10;    ports:&#10;      - '8000:8000'"
                    ></textarea>
                  </div>

                  <!-- 多步骤配置 -->
                  <div v-if="editForm.deployMode === 'multi_step'" class="mb-3">
                    <div
                      class="flex justify-between items-center mb-2"
                    >
                      <div>
                        <Label class="mb-0">部署步骤 <span class="text-red-500">*</span></Label>
                      </div>
                      <Button
                        type="button"
                        variant="outline" size="sm"
                        @click="addEditStep"
                      >
                        <AppIcon  name="plus" class="mr-1" /> 添加步骤
                      </Button>
                    </div>

                    <div
                      v-if="editForm.steps.length === 0"
                      class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900"
                    >
                      <AppIcon  name="info-circle" class="mr-1" />
                      请至少添加一个部署步骤
                    </div>

                    <div v-else class="steps-list">
                      <div
                        v-for="(step, index) in editForm.steps"
                        :key="index"
                        class="mb-2 rounded-lg border border-slate-200 p-4"
                        :class="{ 'border-blue-300': step.name || step.command }"
                      >
                        <div class="p-4">
                          <div
                            class="flex justify-between items-start mb-2"
                          >
                            <div class="flex items-center">
                              <span
                                class="mr-2"
                                style="min-width: 60px"
                                >步骤 {{ index + 1 }}</span
                              >
                              <span v-if="step.name" class="text-slate-500 text-sm">{{
                                step.name
                              }}</span>
                              <span v-else class="text-slate-500 text-sm fst-italic"
                                >未命名步骤</span
                              >
                            </div>
                            <div class="inline-flex items-stretch text-sm">
                              <Button
                                type="button"
                                variant="outline"
                                @click="moveEditStep(index, -1)"
                                :disabled="index === 0"
                                title="上移"
                              >
                                <AppIcon  name="arrow-up" />
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                @click="moveEditStep(index, 1)"
                                :disabled="index === editForm.steps.length - 1"
                                title="下移"
                              >
                                <AppIcon  name="arrow-down" />
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                @click="removeEditStep(index)"
                                title="删除步骤"
                              >
                                <AppIcon  name="trash" />
                              </Button>
                            </div>
                          </div>
                          <div class="mb-2">
                            <Label class="mb-1 text-xs">步骤名称</Label>
                            <Input
                              v-model="step.name"
                              type="text"
                              placeholder="例如：停止旧容器、拉取镜像、启动容器"
                            />
                          </div>
                          <div>
                            <Label class="mb-1 text-xs">执行命令</Label>
                            <textarea
                              v-model="step.command"
                              class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 text-xs"
                              rows="4"
                              placeholder="docker stop my-app || true&#10;或&#10;docker pull registry.cn-hangzhou.aliyuncs.com/namespace/app:latest"
                            ></textarea>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="editForm.deployChannel !== 'portainer'" class="mb-0">
                    <div class="flex items-center gap-2">
                      <input
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        id="edit-redeploySwitch"
                        v-model="editForm.redeploy"
                      />
                      <label class="text-sm text-slate-700" for="edit-redeploySwitch">
                        <AppIcon  name="redo" class="mr-1" />
                        重新发布（如果主机上已存在，先停止并删除）
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 目标主机选择 -->
              <div class="mb-3 min-w-0">
                <Label>选择目标主机 <span class="text-red-500">*</span></Label>
                <div
                  v-if="
                    editForm.deployChannel !== 'portainer' &&
                    selectedHostEntries('edit').length > 0"
                  class="mb-2 flex flex-wrap items-center gap-2"
                >
                  <span
                    v-for="entry in selectedHostEntries('edit')"
                    :key="entry.id"
                    class="inline-flex max-w-full items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-sm text-blue-800"
                  >
                    <span class="break-all">{{ entry.name }}</span>
                    <button
                      type="button"
                      class="inline-flex min-h-8 min-w-8 shrink-0 items-center justify-center rounded text-blue-600 hover:bg-blue-100"
                      :aria-label="`移除 ${entry.name}`"
                      @click="removeSelectedHost('edit', entry.id)"
                    >
                      <AppIcon  name="times" />
                    </button>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    class="w-full sm:w-auto"
                    @click="clearSelectedHosts('edit')"
                  >
                    清空
                  </Button>
                </div>
                <div v-if="editForm.deployChannel === 'portainer'" class="mb-2">
                  <Label class="text-xs">Portainer 目标主机</Label>
                  <NativeSelect
                    v-model="editForm.portainerTargetHost"
                  >
                    <option :value="null" disabled>请选择 Portainer 主机</option>
                    <option
                    v-for="host in editPortainerHosts"
                      :key="host.host_id"
                      :value="host.host_id"
                    >
                      {{ host.name }} ({{ host.portainer_url ||"-" }})
                    </option>
                  </NativeSelect>
                </div>

                <!-- 主机类型筛选和搜索 -->
                <div v-if="editForm.deployChannel !== 'portainer'" class="mb-2">
                  <div class="inline-flex items-stretch text-sm mb-2" role="group">
                    <input
                      type="radio"
                      class="choice-input"
                      id="edit-filter-all"
                      v-model="editHostFilter"
                      value="all"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="edit-filter-all"
                      >全部</label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="edit-filter-agent"
                      v-model="editHostFilter"
                      value="agent"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="edit-filter-agent"
                    >
                      <AppIcon  name="network-wired" class="mr-1" /> Agent
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="edit-filter-portainer"
                      v-model="editHostFilter"
                      value="portainer"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="edit-filter-portainer"
                    >
                      <AppIcon  name="server" class="mr-1" /> Portainer
                    </label>

                    <input
                      type="radio"
                      class="choice-input"
                      id="edit-filter-ssh"
                      v-model="editHostFilter"
                      value="ssh"
                    />
                    <label class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      for="edit-filter-ssh"
                    >
                      <AppIcon  name="terminal" class="mr-1" /> SSH
                    </label>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="flex items-center gap-2">
                      <input
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        id="edit-filter-online"
                        v-model="editFilterOnlineOnly"
                      />
                      <label class="text-sm text-slate-700" for="edit-filter-online"
                        >仅在线</label>
                    </div>
                    <Input
                      type="text"
                      v-model="editHostSearchKeyword"
                      placeholder="搜索主机名称..."
                    />
                  </div>
                </div>

                <!-- 主机列表（按类型分组） -->
                <div
                  v-if="loadingHosts"
                  class="text-slate-500 text-sm text-center py-3"
                >
                  <AppIcon  name="spinner" class="mr-2" spin />加载中...
                </div>
                <div
                  v-else
                  class="border rounded p-2"
                  style="max-height: 300px; overflow-y: auto"
                  v-show="editForm.deployChannel !== 'portainer'"
                >
                  <!-- Agent 主机 -->
                  <div
                    v-if="editChannelFilteredHostsByType.agent.length > 0"
                    class="mb-3"
                  >
                    <div class="font-semibold text-blue-600 mb-2">
                      <AppIcon  name="network-wired" class="mr-1" /> Agent 主机 ({{
                        editChannelFilteredHostsByType.agent.length
                      }})
                    </div>
                    <div
                      v-for="host in editChannelFilteredHostsByType.agent"
                      :key="host.host_id"
                      class="flex items-center gap-2 ml-3"
                    >
                      <input
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :checked="isHostSelected('edit', host.host_id)"
                        @change="onHostToggle('edit', host.host_id, $event)"
                      />
                      <label
                        class="text-sm text-slate-700"
                        :for="`edit-host-${host.host_id}`"
                      >
                        {{ host.name }}
                        <Badge :variant="host.status === 'completed' ? 'success' : host.status === 'failed' ? 'danger' : host.status === 'running' ? 'info' : 'default'" class="ml-1">
                          {{ getStatusText(host.status) }}
                        </Badge>
                        <span
                          v-if="host.description"
                          class="text-slate-500 text-sm ml-1"
                          >({{ host.description }})</span
                        >
                      </label>
                    </div>
                  </div>

                  <!-- Portainer 主机 -->
                  <div
                    v-if="editChannelFilteredHostsByType.portainer.length > 0"
                    class="mb-3"
                  >
                    <div class="font-semibold text-info mb-2">
                      <AppIcon  name="server" class="mr-1" /> Portainer 主机 ({{
                        editChannelFilteredHostsByType.portainer.length
                      }})
                    </div>
                    <div
                      v-for="host in editChannelFilteredHostsByType.portainer"
                      :key="host.host_id"
                      class="flex items-center gap-2 ml-3"
                    >
                      <input
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :checked="isHostSelected('edit', host.host_id)"
                        @change="onHostToggle('edit', host.host_id, $event)"
                      />
                      <label
                        class="text-sm text-slate-700"
                        :for="`edit-host-${host.host_id}`"
                      >
                        {{ host.name }}
                        <Badge :variant="host.status === 'completed' ? 'success' : host.status === 'failed' ? 'danger' : host.status === 'running' ? 'info' : 'default'" class="ml-1">
                          {{ getStatusText(host.status) }}
                        </Badge>
                        <span
                          v-if="host.portainer_url"
                          class="text-slate-500 text-sm ml-1"
                          >({{ host.portainer_url }})</span
                        >
                      </label>
                    </div>
                  </div>

                  <!-- SSH 主机 -->
                  <div
                    v-if="editChannelFilteredHostsByType.ssh.length > 0"
                    class="mb-3"
                  >
                    <div class="font-semibold text-amber-600 mb-2">
                      <AppIcon  name="terminal" class="mr-1" /> SSH 主机 ({{
                        editChannelFilteredHostsByType.ssh.length
                      }})
                    </div>
                    <div
                      v-for="host in editChannelFilteredHostsByType.ssh"
                      :key="host.host_id"
                      class="flex items-center gap-2 ml-3"
                    >
                      <input
                        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :checked="isHostSelected('edit', host.host_id)"
                        @change="onHostToggle('edit', host.host_id, $event)"
                      />
                      <label
                        class="text-sm text-slate-700"
                        :for="`edit-host-${host.host_id}`"
                      >
                        {{ host.name }}
                        <Badge v-if="host.docker_enabled" variant="info" class="ml-1">Docker</Badge>
                        <span
                          v-if="host.docker_version"
                          class="text-slate-500 text-sm ml-1"
                          >({{ host.docker_version }})</span
                        >
                        <span v-if="host.host" class="text-slate-500 text-sm ml-1"
                          >@{{ host.host }}:{{ host.port || 22 }}</span
                        >
                      </label>
                    </div>
                  </div>

                  <div
                    v-if="editFilteredHosts.length === 0"
                    class="text-slate-500 text-sm text-center py-3"
                  >
                    <AppIcon  name="inbox" class="mr-1" />
                    <span v-if="editHostSearchKeyword">未找到匹配的主机</span>
                    <span v-else>暂无可用主机，请先在"主机管理"中添加主机</span>
                  </div>
                </div>

                <p
                  v-if="
                    editForm.deployChannel !== 'portainer' &&
                    selectedHostEntries('edit').length > 0"
                  class="mt-2 text-slate-500 text-sm"
                >
                  已选择 <strong>{{ selectedHostEntries('edit').length }}</strong> 个主机（可在上方标签移除）
                </p>
              </div>
            </div>

            <!-- Webhook设置模式 -->
            <div v-if="editMode === 'webhook'">
              <div class="mb-3">
                <Label>Webhook Token（用于 URL）</Label>
                <div class="flex gap-2">
                  <Input
                    v-model="editForm.webhook_token"
                    type="text"
                    placeholder="留空自动生成"
                  />
                  <Button
                    variant="outline"
                    type="button"
                    @click="regenerateEditWebhookToken"
                    title="重新生成 Token"
                  >
                    <AppIcon  name="sync-alt" /> 重新生成
                  </Button>
                </div>
                <small class="text-slate-500"
                  >用于构建 Webhook URL，留空将自动生成 UUID</small
                >
              </div>
              <div class="mb-3">
                <Label>Webhook 密钥</Label>
                <div class="flex gap-2">
                  <Input
                    v-model="editForm.webhook_secret"
                    type="text"
                    placeholder="留空自动生成"
                  />
                  <Button
                    variant="outline"
                    type="button"
                    @click="regenerateEditWebhookSecret"
                    title="重新生成密钥"
                  >
                    <AppIcon  name="sync-alt" /> 重新生成
                  </Button>
                </div>
                <small class="text-slate-500">用于验证 Webhook 签名（可选）</small>
              </div>
              <div class="mb-3">
                <Label><strong>Webhook 分支策略</strong></Label>
                <div
                  class="inline-flex items-stretch w-full flex flex-wrap"
                  role="group"
                  style="gap: 0.25rem"
                >
                  <input
                    type="radio"
                    class="choice-input"
                    id="edit-strategy-use-push"
                    value="use_push"
                    v-model="editForm.webhook_branch_strategy"
                  />
                  <label
                    class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                    for="edit-strategy-use-push"
                    style="white-space: normal; padding: 0.5rem"
                  >
                    <AppIcon  name="code-branch" class="block mb-1" />
                    <small class="block font-semibold">使用推送分支</small>
                    <small class="text-slate-500 block" style="font-size: 0.7rem"
                      >所有分支都触发</small
                    >
                  </label>
                  <input
                    type="radio"
                    class="choice-input"
                    id="edit-strategy-filter-match"
                    value="filter_match"
                    v-model="editForm.webhook_branch_strategy"
                  />
                  <label
                    class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                    for="edit-strategy-filter-match"
                    style="white-space: normal; padding: 0.5rem"
                  >
                    <AppIcon  name="filter" class="block mb-1" />
                    <small class="block font-semibold">只允许匹配分支</small>
                    <small class="text-slate-500 block" style="font-size: 0.7rem"
                      >使用推送分支构建</small
                    >
                  </label>
                  <input
                    type="radio"
                    class="choice-input"
                    id="edit-strategy-use-configured"
                    value="use_configured"
                    v-model="editForm.webhook_branch_strategy"
                  />
                  <label
                    class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                    for="edit-strategy-use-configured"
                    style="white-space: normal; padding: 0.5rem"
                  >
                    <AppIcon  name="cog" class="block mb-1" />
                    <small class="block font-semibold">使用配置分支</small>
                    <small class="text-slate-500 block" style="font-size: 0.7rem"
                      >所有分支都触发</small
                    >
                  </label>
                  <input
                    type="radio"
                    class="choice-input"
                    id="edit-strategy-select-branches"
                    value="select_branches"
                    v-model="editForm.webhook_branch_strategy"
                  />
                  <label
                    class="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                    for="edit-strategy-select-branches"
                    style="white-space: normal; padding: 0.5rem"
                  >
                    <AppIcon  name="check-square" class="block mb-1" />
                    <small class="block font-semibold">选择分支触发</small>
                    <small class="text-slate-500 block" style="font-size: 0.7rem"
                      >仅选中的分支触发</small
                    >
                  </label>
                </div>
              </div>
              <div
                v-if="editForm.webhook_branch_strategy === 'select_branches'"
                class="mb-3"
              >
                <Label>允许触发的分支</label>
                <Input
                  v-model="editForm.webhook_allowed_branches_input"
                  type="text"
                  placeholder="输入分支名称，多个分支用逗号分隔，如：main,dev,release"
                />
                <small class="text-slate-500"
                  >输入分支名称，多个分支用逗号分隔</small
                >
              </div>
              <div class="mb-3">
                <Button
                  type="button"
                  variant="outline" size="sm"
                  @click="showEditWebhookUrl"
                >
                  <AppIcon  name="link" class="mr-1" /> 查看 Webhook URL
                </Button>
              </div>
            </div>

            <!-- YAML编辑模式 -->
            <div v-if="editMode === 'yaml' && editingTask">
              <div class="mb-3">
                <Label>YAML 配置内容</Label>
                <textarea
                  v-model="editingTask.config_content"
                  class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  rows="20"
                  placeholder="请输入 deploy-config.yaml 格式的配置..."
                ></textarea>
              </div>
              <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div class="">
                  <Label>镜像仓库（可选）</Label>
                  <Input
                    v-model="editingTask.registry"
                    type="text"
                    placeholder="docker.io"
                  />
                </div>
                <div class="">
                  <Label>镜像标签（可选）</Label>
                  <Input
                    v-model="editingTask.tag"
                    type="text"
                    placeholder="latest"
                  />
                </div>
              </div>
            </div>

      <template #footer>
        <Button
              type="button"
              variant="secondary"
              @click="closeEditModal"
            >
              取消
            </Button>
            <Button
              type="button"
              variant="default"
              @click="saveEditTask"
              :disabled="creating"
            >
              <AppIcon v-if="creating"  name="spinner" class="mr-2" spin />
              保存
            </Button>
      </template>
    </FormDialog>
    <FormDialog
      :model-value="showWebhookModal"
      title="Webhook URL"
      icon="link"
      size="md"
      @update:model-value="(v) => !v && (showWebhookModal = false)"
    >
      <div class="mb-3">
              <Label>Webhook URL</Label>
              <div class="flex gap-2">
                <Input
                  :value="webhookUrl"
                  type="text"
                  readonly
                  ref="webhookUrlInput"
                />
                <Button
                  variant="outline" size="sm"
                  @click="copyWebhookUrlFromModal"
                >
                  <AppIcon  name="copy" /> 复制
                </Button>
              </div>
            </div>
            <div class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900">
              <strong>使用说明：</strong><br />
              1. 在 Git 平台（GitHub/GitLab/Gitee）的仓库设置中添加 Webhook<br />
              2. 将上述 URL 粘贴到 Payload URL 中<br />
              3. Content Type 选择 <code>application/json</code><br />
              4. Secret 填写部署配置的 Webhook 密钥（如果有）<br />
              5. 选择触发事件（通常是 Push events）
            </div>
    </FormDialog>

    <ResourceMemberPermissionDialog
      v-model="permissionDialogOpen"
      resource-type="deploy_config"
      :resource-id="permissionTarget?.task_id || ''"
      :team-id="activeTeamId"
      :resource-name="permissionTarget?.app_name || ''"
    />
  </div>
</template>

<script>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import yaml from "js-yaml";
import { copyToClipboard } from "../utils/clipboard.js";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import { Badge } from "@/components/ui/badge";
import Table from "@/components/ui/table/Table.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";
import { useTeamStore } from "@/stores/team";
import { registerTask } from "@/composables/useTaskCompletionWatcher";


export default {
  name:"DeployTaskManager",
  components: {
    PageToolbar,
    PaginationBar,
    EmptyState,
    AlertBanner,
    Button,
    Input,
    Label,
    NativeSelect,
    FormDialog,
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    ResourceMemberPermissionDialog,
  },
  data() {
    return {
      tasks: [],
      loading: false,
      showCreateModal: false,
      showSimpleCreateModal: false,
      showImportModal: false,
      showDetailModal: false,
      showEditModal: false,
      permissionDialogOpen: false,
      permissionTarget: null,
      editingTask: null,
      selectedTask: null,
      taskLogs: [],
      detailTab:"config",
      editMode:"form", // 编辑模式：'form', 'yaml', 'webhook'
      editHostFilter:"all",
      editFilterOnlineOnly: true,
      editHostSearchKeyword:"",
      /** 解析/回填表单时屏蔽 deployChannel 等 watch 清空已选主机 */
      formHydrating: false,
      showWebhookModal: false, // Webhook URL 模态框显示状态
      webhookUrl:"", // Webhook URL
      editForm: {
        appName:"",
        selectedHosts: [],
        portainerTargetHost: null,
        deployChannel:"agent",
        deployMode:"docker_run",
        composeMode:"docker-compose",
        redeployStrategy:"update_existing",
        stackStrategy:"create_new",
        selectedStackId: null,
        newStackName:"",
        runCommand:"",
        composeCommand:"up -d", // Docker Compose 默认命令
        composeContent:"",
        redeploy: false,
        webhook_token:"",
        webhook_secret:"",
        webhook_branch_strategy:"use_push",
        webhook_allowed_branches: [],
        webhook_allowed_branches_input:"",
      },
      taskConfigContent:"",
      taskRegistry:"",
      taskTag:"",
      creating: false,
      agentHosts: [],
      sshHosts: [],
      loadingHosts: false,
      hostFilter:"all", // all, agent, portainer, ssh
      filterOnlineOnly: true,
      hostSearchKeyword:"",
      simpleForm: {
        appName:"",
        selectedHosts: [],
        portainerTargetHost: null,
        deployChannel:"agent",
        imageName:"",
        containerName:"",
        deployMode:"docker_run",
        composeMode:"docker-compose",
        redeployStrategy:"update_existing",
        stackStrategy:"create_new",
        selectedStackId: null,
        newStackName:"",
        composeCommand:"up -d", // Docker Compose 默认命令
        composeContent:"",
        ports: ["8000:8000"],
        envVars: [""],
        volumes: [""],
        restartPolicy:"always",
      },
      availableStacks: [],
      loadingStacks: false,
      selectedStackDetails: null,
      autoRefreshInterval: null, // 自动刷新定时器
      taskTypeFilter:"all",
      createTypeLock: null, // standard | portainer
      editTypeLock: null, // standard | portainer
      // 分页相关
      currentPage: 1,
      pageSize: 20,
      totalTasks: 0,
    };
  },
  computed: {
    activeTeamId() {
      return useTeamStore().activeTeamId ||"";
    },
    filteredTasks() {
      return this.tasks;
    },
    totalPages() {
      return Math.ceil(this.totalTasks / this.pageSize);
    },
    visiblePages() {
      const pages = [];
      const maxVisible = 5;
      let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
      let end = Math.min(this.totalPages, start + maxVisible - 1);
      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
      }
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },
    createPortainerHosts() {
      return (this.agentHosts || []).filter((host) => host.host_type ==="portainer");
    },
    editPortainerHosts() {
      return (this.agentHosts || []).filter((host) => host.host_type ==="portainer");
    },
    // 过滤后的主机列表
    filteredHosts() {
      let hosts = [];

      // 合并所有类型的主机
      if (
        this.hostFilter ==="all" ||
        this.hostFilter ==="agent" ||
        this.hostFilter ==="portainer"
      ) {
        hosts = hosts.concat(this.agentHosts || []);
      }
      if (this.hostFilter ==="all" || this.hostFilter ==="ssh") {
        hosts = hosts.concat(this.sshHosts || []);
      }

      // 按类型过滤
      if (this.hostFilter ==="agent") {
        hosts = hosts.filter((h) => h.host_type ==="agent");
      } else if (this.hostFilter ==="portainer") {
        hosts = hosts.filter((h) => h.host_type ==="portainer");
      } else if (this.hostFilter ==="ssh") {
        // SSH 主机没有 host_type，通过其他方式识别
        hosts = hosts.filter((h) => !h.host_type);
      }

      // 仅在线过滤
      if (this.filterOnlineOnly) {
        hosts = hosts.filter((h) => {
          if (h.host_type) {
            // Agent 或 Portainer 主机
            return h.status ==="online";
          } else {
            // SSH 主机（总是显示，因为没有状态）
            return true;
          }
        });
      }

      // 搜索过滤
      if (this.hostSearchKeyword) {
        const keyword = this.hostSearchKeyword.toLowerCase();
        hosts = hosts.filter(
          (h) =>
            h.name.toLowerCase().includes(keyword) ||
            (h.description && h.description.toLowerCase().includes(keyword)) ||
            (h.portainer_url &&
              h.portainer_url.toLowerCase().includes(keyword)) ||
            (h.host && h.host.toLowerCase().includes(keyword))
        );
      }

      return hosts;
    },
    // 按类型分组的主机
    filteredHostsByType() {
      const result = {
        agent: [],
        portainer: [],
        ssh: [],
      };

      this.filteredHosts.forEach((host) => {
        if (host.host_type ==="agent") {
          result.agent.push(host);
        } else if (host.host_type ==="portainer") {
          result.portainer.push(host);
        } else {
          result.ssh.push(host);
        }
      });

      return result;
    },
    channelFilteredHostsByType() {
      const all = this.filteredHostsByType;
      const channel = this.simpleForm.deployChannel;
      if (channel ==="portainer") {
        return { agent: [], portainer: all.portainer, ssh: [] };
      }
      if (channel ==="ssh") {
        return { agent: [], portainer: [], ssh: all.ssh };
      }
      return { agent: all.agent, portainer: [], ssh: [] };
    },
    // 编辑表单过滤后的主机列表
    editFilteredHosts() {
      let hosts = [];

      // 合并所有类型的主机
      if (
        this.editHostFilter ==="all" ||
        this.editHostFilter ==="agent" ||
        this.editHostFilter ==="portainer"
      ) {
        hosts = hosts.concat(this.agentHosts || []);
      }
      if (this.editHostFilter ==="all" || this.editHostFilter ==="ssh") {
        hosts = hosts.concat(this.sshHosts || []);
      }

      // 按类型过滤
      if (this.editHostFilter ==="agent") {
        hosts = hosts.filter((h) => h.host_type ==="agent");
      } else if (this.editHostFilter ==="portainer") {
        hosts = hosts.filter((h) => h.host_type ==="portainer");
      } else if (this.editHostFilter ==="ssh") {
        hosts = hosts.filter((h) => !h.host_type);
      }

      // 仅在线过滤
      if (this.editFilterOnlineOnly) {
        hosts = hosts.filter((h) => {
          if (h.host_type) {
            return h.status ==="online";
          } else {
            return true;
          }
        });
      }

      // 搜索过滤
      if (this.editHostSearchKeyword) {
        const keyword = this.editHostSearchKeyword.toLowerCase();
        hosts = hosts.filter(
          (h) =>
            h.name.toLowerCase().includes(keyword) ||
            (h.description && h.description.toLowerCase().includes(keyword)) ||
            (h.portainer_url &&
              h.portainer_url.toLowerCase().includes(keyword)) ||
            (h.host && h.host.toLowerCase().includes(keyword))
        );
      }

      // 已选主机始终展示，避免被「仅在线」等筛选项隐藏后无法取消勾选
      const visibleIds = new Set(hosts.map((h) => String(h.host_id)));
      const allHosts = [...(this.agentHosts || []), ...(this.sshHosts || [])];
      for (const hostId of this.editForm.selectedHosts || []) {
        const id = String(hostId);
        if (visibleIds.has(id)) continue;
        const host = allHosts.find((h) => String(h.host_id) === id);
        if (host) {
          hosts.push(host);
          visibleIds.add(id);
        }
      }

      return hosts;
    },
    // 编辑表单按类型分组的主机
    editFilteredHostsByType() {
      const result = {
        agent: [],
        portainer: [],
        ssh: [],
      };

      this.editFilteredHosts.forEach((host) => {
        if (host.host_type ==="agent") {
          result.agent.push(host);
        } else if (host.host_type ==="portainer") {
          result.portainer.push(host);
        } else {
          result.ssh.push(host);
        }
      });

      return result;
    },
    editChannelFilteredHostsByType() {
      const all = this.editFilteredHostsByType;
      const channel = this.editForm.deployChannel;
      const selectedSet = new Set(
        (this.editForm.selectedHosts || []).map((id) => String(id))
      );
      const allHosts = [...(this.agentHosts || []), ...(this.sshHosts || [])];

      const pinSelected = (list, matchFn) => {
        const inList = new Set(list.map((h) => String(h.host_id)));
        const pinned = [];
        for (const id of selectedSet) {
          if (inList.has(id)) continue;
          const host = allHosts.find(
            (h) => String(h.host_id) === id && matchFn(h)
          );
          if (host) pinned.push(host);
        }
        return pinned.length ? [...pinned, ...list] : list;
      };

      if (channel ==="portainer") {
        return {
          agent: [],
          portainer: pinSelected(
            all.portainer,
            (h) => h.host_type ==="portainer"
          ),
          ssh: [],
        };
      }
      if (channel ==="ssh") {
        return {
          agent: [],
          portainer: [],
          ssh: pinSelected(all.ssh, (h) => !h.host_type),
        };
      }
      return {
        agent: pinSelected(all.agent, (h) => h.host_type ==="agent"),
        portainer: pinSelected(all.portainer, (h) => h.host_type ==="portainer"),
        ssh: pinSelected(all.ssh, (h) => !h.host_type),
      };
    },
  },
  watch: {"simpleForm.deployChannel": {
      handler(newChannel, oldChannel) {
        if (this.formHydrating) return;
        if (oldChannel != null && newChannel === oldChannel) return;
        this.clearSelectedHosts("simple");
        this.simpleForm.portainerTargetHost = null;
        if (newChannel ==="portainer") {
          this.hostFilter ="portainer";
          this.simpleForm.deployMode ="docker_compose";
          this.simpleForm.composeMode ="docker-compose";
          this.simpleForm.stackStrategy ="create_new";
          this.loadAvailableStacks();
          if (this.simpleForm.deployMode ==="multi_step") {
            this.simpleForm.deployMode ="docker_run";
          }
        } else {
          this.hostFilter ="all";
        }
      },
    },"simpleForm.portainerTargetHost": {
      handler(newHostId) {
        if (this.simpleForm.deployChannel !=="portainer") return;
        if (newHostId) {
          this.setSelectedHosts("simple", [newHostId]);
          this.loadAvailableStacks();
        } else {
          this.setSelectedHosts("simple", []);
          this.simpleForm.selectedStackId = null;
        }
      },
    },"simpleForm.selectedStackId": {
      async handler(newStackId) {
        if (
          this.simpleForm.deployChannel !=="portainer" ||
          this.simpleForm.stackStrategy !=="update_existing" ||
          !newStackId ||
          this.simpleForm.selectedHosts.length !== 1
        ) {
          return;
        }
        await this.loadStackComposeForSimple();
      },
    },"simpleForm.stackStrategy": {
      handler(newStrategy) {
        if (this.simpleForm.deployChannel !=="portainer") return;
        if (newStrategy ==="create_new") {
          this.simpleForm.selectedStackId = null;
        } else if (newStrategy ==="update_existing") {
          this.simpleForm.newStackName ="";
        }
      },
    },
    // 监听 simpleForm.composeMode 变化，自动设置默认命令
    "simpleForm.composeMode": {
      handler(newMode, oldMode) {
        if (newMode !== oldMode && this.simpleForm.deployMode ==="docker_compose") {
          // 如果命令为空，设置默认值
          if (!this.simpleForm.composeCommand.trim()) {
            if (newMode ==="docker-stack") {
              this.simpleForm.composeCommand ="-c docker-compose.yml";
            } else if (newMode ==="docker-compose") {
              this.simpleForm.composeCommand ="up -d";
            }
          }
        }
      },
    },
    // 监听编辑表单的主机选择变化，自动调整 Compose 模式
    "editForm.deployChannel": {
      handler(newChannel, oldChannel) {
        if (this.formHydrating) return;
        if (oldChannel != null && newChannel === oldChannel) return;
        this.clearSelectedHosts("edit");
        this.editForm.portainerTargetHost = null;
        if (newChannel ==="portainer") {
          this.editHostFilter ="portainer";
          this.editForm.deployMode ="docker_compose";
          this.editForm.composeMode ="docker-compose";
          this.editForm.stackStrategy ="create_new";
          this.loadAvailableStacksForEdit();
        } else {
          this.editHostFilter ="all";
        }
      },
    },"editForm.portainerTargetHost": {
      handler(newHostId) {
        if (this.editForm.deployChannel !=="portainer") return;
        if (newHostId) {
          this.setSelectedHosts("edit", [newHostId]);
          this.loadAvailableStacksForEdit();
        } else {
          this.setSelectedHosts("edit", []);
          this.editForm.selectedStackId = null;
        }
      },
    },"editForm.selectedStackId": {
      async handler(newStackId) {
        if (
          this.editForm.deployChannel !=="portainer" ||
          this.editForm.stackStrategy !=="update_existing" ||
          !newStackId ||
          this.editForm.selectedHosts.length !== 1
        ) {
          return;
        }
        await this.loadStackComposeForEdit();
      },
    },"editForm.stackStrategy": {
      handler(newStrategy) {
        if (this.editForm.deployChannel !=="portainer") return;
        if (newStrategy ==="create_new") {
          this.editForm.selectedStackId = null;
        } else if (newStrategy ==="update_existing") {
          this.editForm.newStackName ="";
        }
      },
    },
    // 监听 editForm.composeMode 变化，自动设置默认命令
    "editForm.composeMode": {
      handler(newMode, oldMode) {
        if (newMode !== oldMode && this.editForm.deployMode ==="docker_compose") {
          // 如果命令为空，设置默认值
          if (!this.editForm.composeCommand.trim()) {
            if (newMode ==="docker-stack") {
              this.editForm.composeCommand ="-c docker-compose.yml";
            } else if (newMode ==="docker-compose") {
              this.editForm.composeCommand ="up -d";
            }
          }
        }
      },
    },
  },
  mounted() {
    this.loadTasks();
    this.loadAgentHosts();
    this.loadSSHHosts();
  },
  beforeUnmount() {
    // 清理资源（如果有自动刷新定时器，在这里清理）
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval);
      this.autoRefreshInterval = null;
    }
  },
  methods: {
    goToPage(page) {
      if (page < 1 || page > this.totalPages) return;
      this.loadTasks(page);
    },
    filterByType(type) {
      this.taskTypeFilter = type;
      this.currentPage = 1;
      this.loadTasks(1);
    },
    normalizeCompareValue(value) {
      return String(value ??"")
        .trim()
        .toLowerCase();
    },
    findHostIdFromTarget(target) {
      const allHosts = [...this.agentHosts, ...this.sshHosts];
      if (!allHosts.length || !target) return null;

      // 1) 如果配置里带 host_id，直接匹配
      if (target.host_id) {
        const hostById = allHosts.find(
          (h) => String(h.host_id) === String(target.host_id)
        );
        if (hostById?.host_id != null && hostById.host_id !=="") {
          return String(hostById.host_id);
        }
      }

      // 2) 按 host_name/name/历史 name-deploy 匹配
      const candidates = [];
      if (target.host_name) candidates.push(target.host_name);
      if (target.name) {
        candidates.push(target.name);
        candidates.push(String(target.name).replace(/-deploy$/,""));
      }
      if (target.mode ==="agent" && target.agent?.name) {
        candidates.push(target.agent.name);
      }
      if (target.mode ==="ssh" && target.host) {
        candidates.push(target.host);
      }

      const normalizedCandidates = candidates
        .map((item) => this.normalizeCompareValue(item))
        .filter(Boolean);
      if (!normalizedCandidates.length) return null;

      const host = allHosts.find((h) => {
        const hostName = this.normalizeCompareValue(h.name);
        return normalizedCandidates.includes(hostName);
      });
      const id = host?.host_id;
      return id != null && id !=="" ? String(id) : null;
    },
    normalizeHostId(hostId) {
      return hostId == null || hostId ==="" ?"" : String(hostId);
    },
    getHostForm(formKind) {
      return formKind ==="edit" ? this.editForm : this.simpleForm;
    },
    selectedHostEntries(formKind) {
      const form = this.getHostForm(formKind);
      const allHosts = [...(this.agentHosts || []), ...(this.sshHosts || [])];
      return (form.selectedHosts || [])
        .map((id) => this.normalizeHostId(id))
        .filter(Boolean)
        .map((id) => {
          const host = allHosts.find((h) => this.normalizeHostId(h.host_id) === id);
          return {
            id,
            name: host?.name || `主机 ${id.slice(0, 8)}…`,
          };
        });
    },
    isHostSelected(formKind, hostId) {
      const id = this.normalizeHostId(hostId);
      return this.getHostForm(formKind).selectedHosts.includes(id);
    },
    setSelectedHosts(formKind, hostIds) {
      const form = this.getHostForm(formKind);
      form.selectedHosts = [
        ...new Set((hostIds || []).map((x) => this.normalizeHostId(x)).filter(Boolean)),
      ];
    },
    clearSelectedHosts(formKind) {
      this.setSelectedHosts(formKind, []);
      this.syncComposeModeFromHosts(formKind);
      if (formKind ==="edit" && this.editForm.deployChannel ==="portainer") {
        this.loadAvailableStacksForEdit();
      } else if (
        formKind ==="simple" &&
        this.simpleForm.deployChannel ==="portainer"
      ) {
        this.loadAvailableStacks();
      }
    },
    removeSelectedHost(formKind, hostId) {
      const id = this.normalizeHostId(hostId);
      const form = this.getHostForm(formKind);
      form.selectedHosts = form.selectedHosts.filter((x) => x !== id);
      this.syncComposeModeFromHosts(formKind);
      if (formKind ==="edit" && this.editForm.deployChannel ==="portainer") {
        this.loadAvailableStacksForEdit();
      } else if (
        formKind ==="simple" &&
        this.simpleForm.deployChannel ==="portainer"
      ) {
        this.loadAvailableStacks();
      }
    },
    onHostToggle(formKind, hostId, event) {
      const checked = event.target.checked;
      const id = this.normalizeHostId(hostId);
      const form = this.getHostForm(formKind);
      let next = [...form.selectedHosts];
      if (checked) {
        if (!next.includes(id)) next.push(id);
      } else {
        next = next.filter((x) => x !== id);
      }
      form.selectedHosts = next;
      this.syncComposeModeFromHosts(formKind);
      if (formKind ==="edit" && this.editForm.deployChannel ==="portainer") {
        this.loadAvailableStacksForEdit();
      } else if (
        formKind ==="simple" &&
        this.simpleForm.deployChannel ==="portainer"
      ) {
        this.loadAvailableStacks();
      }
    },
    syncComposeModeFromHosts(formKind) {
      const form = this.getHostForm(formKind);
      const isSupported =
        formKind ==="edit"
          ? (mode) => this.isEditComposeModeSupported(mode)
          : (mode) => this.isComposeModeSupported(mode);
      if (
        form.deployMode !=="docker_compose" ||
        form.deployChannel ==="portainer" ||
        form.selectedHosts.length === 0
      ) {
        return;
      }
      if (
        form.composeMode ==="docker-compose" &&
        !isSupported("docker-compose")
      ) {
        if (isSupported("docker-stack")) {
          form.composeMode ="docker-stack";
        }
      } else if (
        form.composeMode ==="docker-stack" &&
        !isSupported("docker-stack")
      ) {
        if (isSupported("docker-compose")) {
          form.composeMode ="docker-compose";
        }
      }
    },
    canUseCreateChannel(channel) {
      if (this.createTypeLock ==="portainer") return channel ==="portainer";
      if (this.createTypeLock ==="standard") return channel !=="portainer";
      return true;
    },
    canUseEditChannel(channel) {
      if (this.editTypeLock ==="portainer") return channel ==="portainer";
      if (this.editTypeLock ==="standard") return channel !=="portainer";
      return true;
    },
    closeSimpleCreateModal() {
      this.showSimpleCreateModal = false;
      this.createTypeLock = null;
    },
    closeEditModal() {
      this.showEditModal = false;
      this.editTypeLock = null;
      this.formHydrating = false;
      this.editFilterOnlineOnly = true;
      this.editHostSearchKeyword ="";
    },
    resolveDeployChannel(task) {
      const deployChannel = task?.config?.deploy?.channel;
      if (deployChannel) {
        return deployChannel;
      }
      const firstTarget = task?.config?.targets?.[0];
      if (firstTarget?.host_type) {
        return firstTarget.host_type;
      }
      return"agent";
    },
    stopAutoRefresh() {
      // 停止自动刷新（兼容性方法）
      if (this.autoRefreshInterval) {
        clearInterval(this.autoRefreshInterval);
        this.autoRefreshInterval = null;
      }
    },
    async loadTasks(page) {
      if (page !== undefined) {
        this.currentPage = page;
      }
      this.loading = true;
      try {
        const res = await axios.get("/api/deploy-tasks", {
          params: {
            page: this.currentPage,
            page_size: this.pageSize,
            task_type_filter: this.taskTypeFilter ==="all" ? undefined : this.taskTypeFilter,
          },
        });
        this.totalTasks = res.data.total || 0;
        this.tasks = (res.data.tasks || []).map((task) => {
          const appName = task.app_name || task.config?.app?.name ||"";
          return {
            ...task,
            status: task.status?.status || task.status ||"pending",
            config: task.config || task.task_config?.config || {},
            config_content:
              task.config_content || task.task_config?.config_content ||"",
            execution_count: task.execution_count || 0,
            last_executed_at: task.last_executed_at || null,
            app_name: appName,
          };
        });
      } catch (error) {
        console.error("加载部署任务失败:", error);
        toastError("加载部署任务失败:" + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },
    async createTask() {
      if (!this.taskConfigContent.trim()) {
        toastError("请输入配置内容");
        return;
      }

      // 检查YAML中的应用名称是否重复
      try {
        const config = yaml.load(this.taskConfigContent);
        const appName = config?.app?.name;
        if (appName) {
          if (this.isAppNameDuplicate(appName.trim(), null)) {
            toastError(`应用名称"${appName}" 已存在，请使用其他名称`);
            return;
          }
        }
      } catch (e) {
        console.error("解析YAML失败:", e);
        // YAML解析失败时继续，让后端验证
      }

      this.creating = true;
      try {
        await axios.post("/api/deploy-tasks", {
          config_content: this.taskConfigContent,
          registry: this.taskRegistry || null,
          tag: this.taskTag || null,
        });
        toastSuccess("创建成功");
        this.showCreateModal = false;
        this.taskConfigContent ="";
        this.taskRegistry ="";
        this.taskTag ="";
        this.loadTasks();
      } catch (error) {
        console.error("创建部署任务失败:", error);
        toastError("创建部署任务失败:" + (error.response?.data?.detail || error.message));
      } finally {
        this.creating = false;
      }
    },
    async handleFileImport(event) {
      const file = event.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const content = e.target.result;
          const formData = new FormData();
          formData.append("file", file);

          await axios.post("/api/deploy-tasks/import", formData, {
            headers: {"Content-Type":"multipart/form-data",
            },
          });
          toastSuccess("导入成功");
          this.showImportModal = false;
          this.loadTasks();
        } catch (error) {
          console.error("导入部署任务失败:", error);
          toastError("导入部署任务失败:" +
              (error.response?.data?.detail || error.message));
        }
      };
      reader.readAsText(file);
    },
    async executeTask(task) {
      if (!(await showConfirm({ message: '确定要触发此部署配置吗？\n\n触发后将创建新的部署任务，可在"任务管理"页面查看执行情况。' }))) {
        return;
      }

      try {
        // 注意：task.task_id 实际是 config_id（配置ID），用于执行配置
        const res = await axios.post(
          `/api/deploy-tasks/${task.task_id}/execute`
        );
        const newTaskId = res.data.task_id;
        if (newTaskId) {
          registerTask(newTaskId, {
            task_type:"deploy",
            image: task.name || task.config?.name,
          });
        }
        toastInfo(`部署配置已触发！\n\n新任务ID: ${newTaskId.substring(
            0,
            8
          )}\n可在"任务管理"页面查看执行情况。`);
        this.loadTasks();
        if (this.showDetailModal) {
          this.viewTask(task);
        }
      } catch (error) {
        console.error("触发部署配置失败:", error);
        toastError("触发部署配置失败:" + (error.response?.data?.detail || error.message));
      }
    },
    viewExecutions(task) {
      // 跳转到任务管理页面，筛选该配置的任务
      const configId = task.task_id;
      sessionStorage.setItem("deployConfigFilter", configId);
      window.dispatchEvent(new CustomEvent("navigate", { detail: { tab:"tasks" } }));
    },
    async deleteTask(task) {
      if (!(await showConfirm({ message:"确定要删除此部署配置吗？", danger: true }))) return;

      try {
        // 注意：task.task_id 实际是 config_id（配置ID），用于删除配置
        await axios.delete(`/api/deploy-tasks/${task.task_id}`);
        toastSuccess("删除成功");
        this.loadTasks();
        if (
          this.showDetailModal &&
          this.selectedTask?.task_id === task.task_id
        ) {
          this.showDetailModal = false;
        }
      } catch (error) {
        console.error("删除部署任务失败:", error);
        toastError("删除部署任务失败:" + (error.response?.data?.detail || error.message));
      }
    },
    async exportTask(task) {
      try {
        const res = await axios.get(
          `/api/deploy-tasks/${task.task_id}/export`,
          {
            responseType:"blob",
          }
        );
        const blob = new Blob([res.data], { type:"application/x-yaml" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `deploy-task-${task.task_id}.yaml`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error("导出部署任务失败:", error);
        toastError("导出部署任务失败:" + (error.response?.data?.detail || error.message));
      }
    },
    async viewTask(task) {
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`);
        const taskData = res.data.task;
        // 适配新的数据结构
        this.selectedTask = {
          ...taskData,
          status: taskData.status?.status || taskData.status ||"pending",
          config: taskData.config || taskData.task_config?.config || {},
          config_content:
            taskData.config_content ||
            taskData.task_config?.config_content ||"",
          created_at: taskData.created_at || taskData.status?.created_at,
          completed_at: taskData.completed_at || taskData.status?.completed_at,
          error: taskData.error,
        };
        this.detailTab ="config";
        this.showDetailModal = true;

        // 加载任务日志
        await this.loadTaskLogs(task.task_id);
      } catch (error) {
        console.error("获取任务详情失败:", error);
        toastError("获取任务详情失败:" + (error.response?.data?.detail || error.message));
      }
    },
    async loadTaskLogs(taskId) {
      try {
        // 从任务管理API获取日志（部署任务现在也使用统一的任务管理）
        const res = await axios.get(`/api/tasks/${taskId}`);
        this.taskLogs = res.data.logs || [];
      } catch (error) {
        console.error("加载任务日志失败:", error);
        this.taskLogs = [];
      }
    },
    getStatusBadgeClass(status) {
      const map = {
        pending:"bg-slate-500 text-white",
        running:"bg-blue-600 text-white",
        completed:"bg-green-600 text-white",
        failed:"bg-red-600 text-white",
      };
      return map[status] ||"bg-slate-500 text-white";
    },
    // 检查主机是否支持指定的 Compose 模式
    isComposeModeSupported(mode) {
      // 如果没有选择主机，返回 true（允许选择）
      if (this.simpleForm.selectedHosts.length === 0) {
        return true;
      }

      // 检查所有选中的主机是否都支持该模式
      const allHosts = [...this.agentHosts, ...this.sshHosts];
      return this.simpleForm.selectedHosts.every((hostId) => {
        const host = allHosts.find(
          (h) => this.normalizeHostId(h.host_id) === this.normalizeHostId(hostId)
        );
        if (!host) return false;

        const dockerInfo = host.docker_info || {};

        if (mode ==="docker-compose") {
          // 支持 docker-compose（true）或不明确（null/undefined）都允许
          return dockerInfo.compose_supported !== false;
        } else if (mode ==="docker-stack") {
          // 必须明确支持 stack（true）
          return dockerInfo.stack_supported === true;
        }

        return false;
      });
    },
    // 编辑表单：检查主机是否支持指定的 Compose 模式
    isEditComposeModeSupported(mode) {
      // 如果没有选择主机，返回 true（允许选择）
      if (this.editForm.selectedHosts.length === 0) {
        return true;
      }

      // 检查所有选中的主机是否都支持该模式
      const allHosts = [...this.agentHosts, ...this.sshHosts];
      return this.editForm.selectedHosts.every((hostId) => {
        const host = allHosts.find(
          (h) => this.normalizeHostId(h.host_id) === this.normalizeHostId(hostId)
        );
        if (!host) return false;

        const dockerInfo = host.docker_info || {};

        if (mode ==="docker-compose") {
          // 支持 docker-compose（true）或不明确（null/undefined）都允许
          return dockerInfo.compose_supported !== false;
        } else if (mode ==="docker-stack") {
          // 必须明确支持 stack（true）
          return dockerInfo.stack_supported === true;
        }

        return false;
      });
    },
    getStatusText(status) {
      const map = {
        pending:"待执行",
        running:"执行中",
        completed:"已完成",
        failed:"失败",
      };
      return map[status] || status ||"未知";
    },
    formatTime(time) {
      if (!time) return"-";
      return new Date(time).toLocaleString("zh-CN");
    },
    isAppNameDuplicate(appName, excludeTaskId) {
      if (!appName) return false;
      return this.tasks.some((task) => {
        const taskAppName = task.config?.app?.name;
        return (
          taskAppName &&
          taskAppName === appName &&
          task.task_id !== excludeTaskId
        );
      });
    },
    checkAppNameDuplicate(appName, excludeTaskId) {
      if (!appName) return;
      if (this.isAppNameDuplicate(appName, excludeTaskId)) {
        // 应用名称重复，已经在模板中显示错误提示
      }
    },
    async loadAgentHosts() {
      this.loadingHosts = true;
      try {
        const res = await axios.get("/api/agent-hosts");
        this.agentHosts = res.data.hosts || [];
      } catch (error) {
        console.error("加载Agent主机列表失败:", error);
      } finally {
        this.loadingHosts = false;
      }
    },
    async loadSSHHosts() {
      try {
        const res = await axios.get("/api/hosts");
        this.sshHosts = res.data.hosts || [];
      } catch (error) {
        console.error("加载 SSH 主机列表失败:", error);
        // SSH 主机加载失败不影响使用
      }
    },
    async createSimpleTask() {
      if (
        this.createTypeLock ==="portainer" &&
        this.simpleForm.deployChannel !=="portainer"
      ) {
        toastError("当前为 Portainer 新建流程，不能切换到 SSH/Agent 类型");
        return;
      }
      if (
        this.createTypeLock ==="standard" &&
        this.simpleForm.deployChannel ==="portainer"
      ) {
        toastError("当前为 SSH/Agent 新建流程，不能切换到 Portainer 类型");
        return;
      }
      // 验证必填字段
      if (!this.simpleForm.appName.trim()) {
        toastError("请输入应用名称");
        return;
      }

      // 检查应用名称是否已存在
      const appName = this.simpleForm.appName.trim();
      const existingTask = this.tasks.find((task) => {
        const taskAppName = task.config?.app?.name;
        return taskAppName && taskAppName === appName;
      });
      if (existingTask) {
        toastError(`应用名称"${appName}" 已存在，请使用其他名称`);
        return;
      }
      if (this.simpleForm.selectedHosts.length === 0) {
        toastError("请至少选择一个目标主机");
        return;
      }
      if (
        this.simpleForm.deployChannel ==="portainer" &&
        this.simpleForm.selectedHosts.length !== 1
      ) {
        toastError("Portainer 发布必须选择一个目标主机");
        return;
      }
      if (
        this.simpleForm.deployChannel ==="portainer" &&
        this.simpleForm.deployMode ==="multi_step"
      ) {
        toastError("Portainer 发布暂不支持多步骤模式");
        return;
      }
      if (
        this.simpleForm.deployChannel ==="portainer" &&
        this.simpleForm.deployMode !=="docker_compose"
      ) {
        toastInfo("Portainer 发布仅支持 Docker Compose/Stack");
        return;
      }
      if (
        this.simpleForm.deployMode ==="docker_run" &&
        !this.simpleForm.runCommand.trim()
      ) {
        toastError("请输入 Docker Run 命令");
        return;
      }
      if (this.simpleForm.deployMode ==="docker_compose") {
        if (
          this.simpleForm.deployChannel ==="portainer" &&
          this.simpleForm.stackStrategy ==="update_existing" &&
          !this.simpleForm.selectedStackId
        ) {
          toastError("请选择要更新的 Stack");
          return;
        }
        if (
          this.simpleForm.deployChannel ==="portainer" &&
          this.simpleForm.stackStrategy ==="create_new" &&
          !this.simpleForm.newStackName?.trim()
        ) {
          toastError("请输入新 Stack 名称");
          return;
        }
        if (!this.simpleForm.composeCommand.trim()) {
          // 如果命令为空，设置默认值
          if (this.simpleForm.composeMode ==="docker-stack") {
            this.simpleForm.composeCommand ="-c docker-compose.yml";
          } else {
            this.simpleForm.composeCommand ="up -d";
          }
        }
        if (!this.simpleForm.composeContent.trim()) {
          toastError("请输入 docker-compose.yml 内容");
          return;
        }
      }

      // 将命令转换为统一的YAML配置格式（新格式）
      // 新格式：统一的deploy配置 + targets列表
      const targets = [];
      for (const hostId of this.simpleForm.selectedHosts) {
        // 在所有主机列表中查找（包括 Agent、Portainer 和 SSH）
        const host = [...this.agentHosts, ...this.sshHosts].find(
          (h) =>
            this.normalizeHostId(h.host_id) === this.normalizeHostId(hostId)
        );
        if (!host) continue;

        // 确定主机类型
        let hostType ="agent";
        if (host.host_type ==="portainer") {
          hostType ="portainer";
        } else if (host.host_type ==="agent") {
          hostType ="agent";
        } else {
          hostType ="ssh";
        }

        targets.push({
          name: `${host.name}-deploy`,
          host_type: hostType,
          host_name: host.name,
        });
      }

      // 构建统一的deploy配置
      let deployConfig = {};

      if (this.simpleForm.deployMode ==="multi_step") {
        // 多步骤模式
        deployConfig = {
          steps: this.simpleForm.steps.map((step) => ({
            name: step.name.trim(),
            command: step.command.trim(),
          })),
        };
      } else {
        // 单命令模式
        deployConfig = {
          channel: this.simpleForm.deployChannel,
          type:
            this.simpleForm.deployMode ==="docker_compose"
              ?"docker_compose"
              :"docker_run",
          command:
            this.simpleForm.deployMode ==="docker_run"
              ? this.simpleForm.runCommand.trim()
              : this.simpleForm.composeCommand.trim(),
        };

        if (this.simpleForm.deployMode ==="docker_compose") {
          deployConfig.compose_content = this.simpleForm.composeContent.trim();
          // 添加 compose_mode 和 redeploy_strategy
          if (
            this.simpleForm.deployChannel !=="portainer" &&
            this.simpleForm.composeMode
          ) {
            deployConfig.compose_mode = this.simpleForm.composeMode;
          }
          if (this.simpleForm.redeployStrategy) {
            deployConfig.redeploy_strategy = this.simpleForm.redeployStrategy;
          }
          if (this.simpleForm.deployChannel ==="portainer") {
            deployConfig.stack_strategy = this.simpleForm.stackStrategy;
            if (this.simpleForm.selectedStackId) {
              deployConfig.stack_id = this.simpleForm.selectedStackId;
            }
            if (this.simpleForm.newStackName?.trim()) {
              deployConfig.stack_name = this.simpleForm.newStackName.trim();
            }
          }
        }
      }

      if (this.simpleForm.redeploy) {
        deployConfig.redeploy = true;
      }

      const yamlConfig = {
        version:"1.0",
        app: {
          name: this.simpleForm.appName,
        },
        deploy: deployConfig,
        targets: targets,
      };

      // 转换为YAML字符串（统一格式，与直接输入YAML的方式一致）
      const yamlContent = yaml.dump(yamlConfig, {
        defaultFlowStyle: false,
        allowUnicode: true,
      });

      // 创建任务（统一调用后端API，后端会解析YAML并保存）
      this.creating = true;
      try {
        await axios.post("/api/deploy-tasks", {
          config_content: yamlContent,
          registry: null,
          tag: null,
        });
        toastSuccess("创建成功");
        this.closeSimpleCreateModal();
        this.resetSimpleForm();
        this.loadTasks();
      } catch (error) {
        console.error("创建部署任务失败:", error);
        toastError("创建部署任务失败:" + (error.response?.data?.detail || error.message));
      } finally {
        this.creating = false;
      }
    },
    resetSimpleForm() {
      this.simpleForm = {
        appName:"",
        selectedHosts: [],
        portainerTargetHost: null,
        deployChannel:"agent",
        deployMode:"docker_run",
        composeMode:"docker-compose",
        redeployStrategy:"update_existing",
        stackStrategy:"create_new",
        selectedStackId: null,
        newStackName:"",
        runCommand:"",
        composeCommand:"up -d", // Docker Compose 默认命令
        composeContent:"",
        redeploy: false,
        steps: [],
      };
    },
    async loadAvailableStacks() {
      if (
        this.simpleForm.deployChannel !=="portainer" ||
        this.simpleForm.selectedHosts.length !== 1
      ) {
        this.availableStacks = [];
        return;
      }
      const hostId = this.simpleForm.selectedHosts[0];
      this.loadingStacks = true;
      try {
        const res = await axios.get(`/api/agent-hosts/${hostId}/stacks`);
        this.availableStacks = res.data.stacks || [];
      } catch (error) {
        this.availableStacks = [];
      } finally {
        this.loadingStacks = false;
      }
    },
    async loadStackComposeForSimple() {
      const hostId = this.simpleForm.selectedHosts[0];
      const stackId = this.simpleForm.selectedStackId;
      if (!hostId || !stackId) return;
      try {
        const res = await axios.get(`/api/agent-hosts/${hostId}/stacks/${stackId}`);
        const compose = res.data?.stack?.compose_content;
        if (compose && compose.trim()) {
          this.simpleForm.composeContent = compose;
        }
      } catch (error) {
        toastError("加载 Stack 配置失败:" + (error.response?.data?.detail || error.message));
      }
    },
    async loadAvailableStacksForEdit() {
      if (
        this.editForm.deployChannel !=="portainer" ||
        this.editForm.selectedHosts.length !== 1
      ) {
        this.availableStacks = [];
        return;
      }
      const hostId = this.editForm.selectedHosts[0];
      this.loadingStacks = true;
      try {
        const res = await axios.get(`/api/agent-hosts/${hostId}/stacks`);
        this.availableStacks = res.data.stacks || [];
      } catch (error) {
        this.availableStacks = [];
      } finally {
        this.loadingStacks = false;
      }
    },
    async loadStackComposeForEdit() {
      const hostId = this.editForm.selectedHosts[0];
      const stackId = this.editForm.selectedStackId;
      if (!hostId || !stackId) return;
      try {
        const res = await axios.get(`/api/agent-hosts/${hostId}/stacks/${stackId}`);
        const compose = res.data?.stack?.compose_content;
        if (compose && compose.trim()) {
          this.editForm.composeContent = compose;
        }
      } catch (error) {
        toastError("加载 Stack 配置失败:" + (error.response?.data?.detail || error.message));
      }
    },
    addStep() {
      this.simpleForm.steps.push({
        name:"",
        command:"",
      });
    },
    removeStep(index) {
      this.simpleForm.steps.splice(index, 1);
    },
    moveStep(index, direction) {
      // direction: -1 上移, 1 下移
      if (direction === -1 && index > 0) {
        const temp = this.simpleForm.steps[index];
        this.simpleForm.steps[index] = this.simpleForm.steps[index - 1];
        this.simpleForm.steps[index - 1] = temp;
      } else if (direction === 1 && index < this.simpleForm.steps.length - 1) {
        const temp = this.simpleForm.steps[index];
        this.simpleForm.steps[index] = this.simpleForm.steps[index + 1];
        this.simpleForm.steps[index + 1] = temp;
      }
    },
    addEditStep() {
      this.editForm.steps.push({
        name:"",
        command:"",
      });
    },
    async removeEditStep(index) {
      if (await showConfirm({ message: `确定要删除步骤 ${index + 1} 吗？`, danger: true })) {
        this.editForm.steps.splice(index, 1);
      }
    },
    moveEditStep(index, direction) {
      // direction: -1 上移, 1 下移
      if (direction === -1 && index > 0) {
        const temp = this.editForm.steps[index];
        this.editForm.steps[index] = this.editForm.steps[index - 1];
        this.editForm.steps[index - 1] = temp;
      } else if (direction === 1 && index < this.editForm.steps.length - 1) {
        const temp = this.editForm.steps[index];
        this.editForm.steps[index] = this.editForm.steps[index + 1];
        this.editForm.steps[index + 1] = temp;
      }
    },
    switchToYamlMode() {
      // 切换到YAML模式时，确保 editingTask 有正确的数据
      if (!this.editingTask) {
        return;
      }
      // 确保 registry 和 tag 字段存在
      if (
        this.editingTask.registry === undefined ||
        this.editingTask.registry === null
      ) {
        this.editingTask.registry ="";
      }
      if (this.editingTask.tag === undefined || this.editingTask.tag === null) {
        this.editingTask.tag ="";
      }
      this.editMode ="yaml";
    },
    openSimpleCreateModal(createType ="standard") {
      this.resetSimpleForm();
      this.createTypeLock = createType;
      if (createType ==="portainer") {
        this.simpleForm.deployChannel ="portainer";
        this.simpleForm.deployMode ="docker_compose";
        this.simpleForm.composeMode ="docker-compose";
        this.simpleForm.stackStrategy ="create_new";
        this.hostFilter ="portainer";
      } else {
        this.simpleForm.deployChannel ="agent";
        this.hostFilter ="all";
      }
      this.loadAgentHosts();
      this.showSimpleCreateModal = true;
    },
    openResourcePermission(task) {
      this.permissionTarget = task;
      this.permissionDialogOpen = true;
    },
    async editTask(task) {
      try {
        this.editTypeLock = null;
        // 编辑时默认不过滤在线状态，避免已绑定离线主机看起来“未反选”
        this.editFilterOnlineOnly = false;
        this.editHostFilter ="all";
        // 注意：task.task_id 实际是 config_id（配置ID），用于查询和更新配置
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`);
        const taskData = res.data.task;
        // 确保 editingTask 对象完整初始化，包括 registry 和 tag
        // 后端返回的数据结构：task.config_content 或 task.task_config.config_content
        const configContent =
          taskData.config_content ||
          (taskData.task_config && taskData.task_config.config_content) ||"";
        const taskConfig = taskData.task_config || {};
        this.editingTask = {
          task_id: taskData.task_id,
          config_content: configContent,
          registry:
            (taskData.status && taskData.status.registry) ||
            taskConfig.registry ||"",
          tag: (taskData.status && taskData.status.tag) || taskConfig.tag ||"",
          webhook_token: taskData.webhook_token ||"",
          webhook_secret: taskData.webhook_secret ||"",
          webhook_branch_strategy:
            taskData.webhook_branch_strategy ||"use_push",
          webhook_allowed_branches: taskData.webhook_allowed_branches || [],
        };

        // 先加载主机列表（解析表单时需要主机列表）
        await this.loadAgentHosts();
        await this.loadSSHHosts();

        // 先保存webhook配置（因为parseYamlToForm会重置editForm）
        const savedWebhookToken = taskData.webhook_token ||"";
        const savedWebhookSecret = taskData.webhook_secret ||"";
        const savedWebhookBranchStrategy =
          taskData.webhook_branch_strategy ||"use_push";
        const savedWebhookAllowedBranches =
          taskData.webhook_allowed_branches || [];

        // 解析YAML配置到表单
        const config = taskData.config || taskConfig.config || {};
        this.parseYamlToForm(configContent, config);
        this.editTypeLock =
          this.editForm.deployChannel ==="portainer" ?"portainer" :"standard";

        // 恢复webhook配置（必须在parseYamlToForm之后）
        this.editForm.webhook_token = savedWebhookToken;
        this.editForm.webhook_secret = savedWebhookSecret;
        this.editForm.webhook_branch_strategy = savedWebhookBranchStrategy;
        this.editForm.webhook_allowed_branches = savedWebhookAllowedBranches;
        this.editForm.webhook_allowed_branches_input =
          savedWebhookAllowedBranches.join(",");

        console.log("加载webhook配置:", {
          webhook_token: savedWebhookToken
            ? savedWebhookToken.substring(0, 8) +"..."
            :"(空)",
          webhook_secret: savedWebhookSecret ?"***" :"(空)",
          webhook_branch_strategy: savedWebhookBranchStrategy,
          webhook_allowed_branches: savedWebhookAllowedBranches,
        });

        this.showEditModal = true;
        this.editMode ="form"; // 默认使用表单编辑
        // 如果详情模态框打开，先关闭它
        if (this.showDetailModal) {
          this.showDetailModal = false;
        }
      } catch (error) {
        console.error("获取任务详情失败:", error);
        toastError("获取任务详情失败:" + (error.response?.data?.detail || error.message));
      }
    },
    parseYamlToForm(configContent, config) {
      this.formHydrating = true;
      try {
      // 重置表单
      this.editForm = {
        appName:"",
        selectedHosts: [],
        portainerTargetHost: null,
        deployChannel:"agent",
        deployMode:"docker_run",
        composeMode:"docker-compose",
        redeployStrategy:"update_existing",
        stackStrategy:"create_new",
        selectedStackId: null,
        newStackName:"",
        runCommand:"",
        composeCommand:"up -d", // Docker Compose 默认命令
        composeContent:"",
        redeploy: false,
        steps: [],
        webhook_token:"",
        webhook_secret:"",
        webhook_branch_strategy:"use_push",
        webhook_allowed_branches: [],
        webhook_allowed_branches_input:"",
      };

      if (!config) {
        try {
          config = yaml.load(configContent);
        } catch (e) {
          console.error("解析YAML失败:", e);
          return;
        }
      }
      if (!config) return;

      // 解析应用名称
      if (config.app && config.app.name) {
        this.editForm.appName = config.app.name;
      }

      // 解析部署配置（新格式优先，向后兼容旧格式）
      let deployConfig = config.deploy;
      if (!deployConfig) {
        // 旧格式：从第一个target的docker配置提取
        const targets = config.targets || [];
        if (targets.length > 0) {
          const firstTarget = targets[0];
          const dockerConfig = firstTarget.docker || {};
          const deployMode = dockerConfig.deploy_mode ||"docker_run";
          deployConfig = {
            type:
              deployMode ==="docker_compose" ?"docker_compose" :"docker_run",
            command: dockerConfig.command ||"",
          };
          if (deployMode ==="docker_compose") {
            deployConfig.compose_content = dockerConfig.compose_content ||"";
          }
          if (dockerConfig.redeploy) {
            deployConfig.redeploy = true;
          }
        }
      }

      if (deployConfig) {
        const targetHostType =
          (config.targets &&
            config.targets[0] &&
            (config.targets[0].host_type ||
              (config.targets[0].mode ==="ssh" ?"ssh" :"agent"))) ||"agent";
        this.editForm.deployChannel = deployConfig.channel || targetHostType;
        // 判断是否为多步骤模式
        if (deployConfig.steps && Array.isArray(deployConfig.steps)) {
          // 多步骤模式
          this.editForm.deployMode ="multi_step";
          this.editForm.steps = deployConfig.steps.map((step) => ({
            name: step.name ||"",
            command: step.command ||"",
          }));
        } else {
          // 单命令模式
          this.editForm.deployMode =
            deployConfig.type ==="docker_compose"
              ?"docker_compose"
              :"docker_run";
          this.editForm.deployChannel = deployConfig.channel || targetHostType;

          // 解析部署命令和内容
          if (this.editForm.deployMode ==="docker_run") {
            this.editForm.runCommand = deployConfig.command ||"";
          } else {
            // 解析 compose_mode 和 redeploy_strategy
            this.editForm.composeMode =
              deployConfig.compose_mode ||"docker-compose";
            // 根据 compose_mode 设置默认命令
            if (deployConfig.command) {
              this.editForm.composeCommand = deployConfig.command;
            } else {
              // 设置默认命令
              if (this.editForm.composeMode ==="docker-stack") {
                this.editForm.composeCommand ="-c docker-compose.yml";
              } else {
                this.editForm.composeCommand ="up -d";
              }
            }
            this.editForm.composeContent = deployConfig.compose_content ||"";
            this.editForm.redeployStrategy =
              deployConfig.redeploy_strategy ||"update_existing";
            this.editForm.stackStrategy =
              deployConfig.stack_strategy ||"create_new";
            this.editForm.selectedStackId = deployConfig.stack_id || null;
            this.editForm.newStackName = deployConfig.stack_name ||"";
          }
        }

        this.editForm.redeploy = deployConfig.redeploy || false;
      }

      // 解析目标主机
      const targets = config.targets || [];
      const selectedHostIds = [];
      for (const target of targets) {
        const hostId = this.findHostIdFromTarget(target);
        if (hostId) selectedHostIds.push(String(hostId));
      }
      this.setSelectedHosts("edit", selectedHostIds);
      this.syncComposeModeFromHosts("edit");
      if (
        this.editForm.deployChannel ==="portainer" &&
        this.editForm.selectedHosts.length > 0
      ) {
        this.editForm.portainerTargetHost = this.editForm.selectedHosts[0];
        this.loadAvailableStacksForEdit();
      }
      } finally {
        this.$nextTick(() => {
          this.formHydrating = false;
        });
      }
    },
    async saveEditTask() {
      if (
        this.editTypeLock ==="portainer" &&
        this.editForm.deployChannel !=="portainer"
      ) {
        toastError("Portainer 任务不允许切换为 SSH/Agent 类型");
        return;
      }
      if (
        this.editTypeLock ==="standard" &&
        this.editForm.deployChannel ==="portainer"
      ) {
        toastError("SSH/Agent 任务不允许切换为 Portainer 类型");
        return;
      }
      let yamlContent ="";
      const registry = this.editingTask.registry || null;
      const tag = this.editingTask.tag || null;

      if (this.editMode ==="form") {
        // 表单模式：验证并转换为YAML
        if (!this.editForm.appName.trim()) {
          toastError("请输入应用名称");
          return;
        }

        // 检查应用名称是否已存在（排除当前任务）
        const appName = this.editForm.appName.trim();
        if (this.isAppNameDuplicate(appName, this.editingTask?.task_id)) {
          toastError(`应用名称"${appName}" 已存在，请使用其他名称`);
          return;
        }

        if (this.editForm.selectedHosts.length === 0) {
          toastError("请至少选择一个目标主机");
          return;
        }
        if (
          this.editForm.deployChannel ==="portainer" &&
          this.editForm.selectedHosts.length !== 1
        ) {
          toastError("Portainer 发布必须选择一个目标主机");
          return;
        }
        if (
          this.editForm.deployChannel ==="portainer" &&
          this.editForm.deployMode !=="docker_compose"
        ) {
          toastInfo("Portainer 发布仅支持 Docker Compose/Stack");
          return;
        }
        if (
          this.editForm.deployMode ==="docker_run" &&
          !this.editForm.runCommand.trim()
        ) {
          toastError("请输入 Docker Run 命令");
          return;
        }
        if (this.editForm.deployMode ==="docker_compose") {
          if (
            this.editForm.deployChannel ==="portainer" &&
            this.editForm.stackStrategy ==="update_existing" &&
            !this.editForm.selectedStackId
          ) {
            toastError("请选择要更新的 Stack");
            return;
          }
          if (
            this.editForm.deployChannel ==="portainer" &&
            this.editForm.stackStrategy ==="create_new" &&
            !this.editForm.newStackName?.trim()
          ) {
            toastError("请输入新 Stack 名称");
            return;
          }
          if (!this.editForm.composeCommand.trim()) {
            // 如果命令为空，设置默认值
            if (this.editForm.composeMode ==="docker-stack") {
              this.editForm.composeCommand ="-c docker-compose.yml";
            } else {
              this.editForm.composeCommand ="up -d";
            }
          }
          if (!this.editForm.composeContent.trim()) {
            toastError("请输入 docker-compose.yml 内容");
            return;
          }
        }
        if (this.editForm.deployMode ==="multi_step") {
          if (this.editForm.steps.length === 0) {
            toastError("请至少添加一个部署步骤");
            return;
          }
          for (let i = 0; i < this.editForm.steps.length; i++) {
            const step = this.editForm.steps[i];
            if (!step.name || !step.name.trim()) {
              toastError(`步骤 ${i + 1} 的名称不能为空`);
              return;
            }
            if (!step.command || !step.command.trim()) {
              toastError(`步骤 ${i + 1} 的命令不能为空`);
              return;
            }
          }
        }

        // 将表单数据转换为YAML
        yamlContent = this.formToYaml(this.editForm);
      } else {
        // YAML模式：直接使用YAML内容
        if (
          !this.editingTask.config_content ||
          !this.editingTask.config_content.trim()
        ) {
          toastError("YAML 配置内容不能为空");
          return;
        }
        yamlContent = this.editingTask.config_content;

        // 检查YAML中的应用名称是否重复
        try {
          const config = yaml.load(yamlContent);
          const appName = config?.app?.name;
          if (appName) {
            if (
              this.isAppNameDuplicate(appName.trim(), this.editingTask?.task_id)
            ) {
              toastError(`应用名称"${appName}" 已存在，请使用其他名称`);
              return;
            }
          }
        } catch (e) {
          console.error("解析YAML失败:", e);
          // YAML解析失败时继续，让后端验证
        }
      }

      if (!(await showConfirm({ message:"确定要保存修改吗？" }))) {
        return;
      }

      this.creating = true;
      try {
        // 处理webhook允许的分支列表
        let webhook_allowed_branches = [];
        if (
          this.editForm.webhook_branch_strategy ==="select_branches" &&
          this.editForm.webhook_allowed_branches_input
        ) {
          webhook_allowed_branches =
            this.editForm.webhook_allowed_branches_input
              .split(",")
              .map((b) => b.trim())
              .filter((b) => b);
        }

        // 更新现有任务
        // 处理webhook字段：editForm中已经加载了webhook配置，直接使用
        // 确保webhook_token不为undefined，如果为空字符串则让后端生成新token
        const webhookToken =
          this.editForm.webhook_token !== undefined &&
          this.editForm.webhook_token !== null
            ? this.editForm.webhook_token
            :"";
        const webhookSecret =
          this.editForm.webhook_secret !== undefined &&
          this.editForm.webhook_secret !== null
            ? this.editForm.webhook_secret
            :"";
        const webhookBranchStrategy =
          this.editForm.webhook_branch_strategy ||"use_push";

        console.log("保存webhook配置:", {
          webhook_token: webhookToken
            ? webhookToken.substring(0, 8) +"..."
            :"(空，将生成)",
          webhook_secret: webhookSecret ?"***" :"(空)",
          webhook_branch_strategy: webhookBranchStrategy,
          webhook_allowed_branches: webhook_allowed_branches,
        });

        // 注意：this.editingTask.task_id 实际是 config_id（配置ID），用于更新配置
        await axios.put(`/api/deploy-tasks/${this.editingTask.task_id}`, {
          config_content: yamlContent,
          registry: registry,
          tag: tag,
          webhook_token: webhookToken,
          webhook_secret: webhookSecret,
          webhook_branch_strategy: webhookBranchStrategy,
          webhook_allowed_branches:
            webhook_allowed_branches.length > 0
              ? webhook_allowed_branches
              : webhookBranchStrategy ==="select_branches"
              ? []
              : null,
        });

        toastSuccess("保存成功");
        this.closeEditModal();
        this.editingTask = null;
        this.loadTasks();
      } catch (error) {
        console.error("保存任务失败:", error);
        toastError("保存任务失败:" + (error.response?.data?.detail || error.message));
      } finally {
        this.creating = false;
      }
    },
    formToYaml(form) {
      // 将表单数据转换为YAML配置（新格式）
      const targets = [];
      for (const hostId of form.selectedHosts) {
        const host = [...this.agentHosts, ...this.sshHosts].find(
          (h) =>
            this.normalizeHostId(h.host_id) === this.normalizeHostId(hostId)
        );
        if (!host) continue;

        // 确定主机类型
        let hostType ="agent";
        if (host.host_type ==="portainer") {
          hostType ="portainer";
        } else if (host.host_type ==="agent") {
          hostType ="agent";
        } else {
          hostType ="ssh";
        }

        targets.push({
          name: `${host.name}-deploy`,
          host_type: hostType,
          host_name: host.name,
        });
      }

      // 构建统一的deploy配置
      let deployConfig = {};

      if (form.deployMode ==="multi_step") {
        // 多步骤模式
        deployConfig = {
          steps: form.steps.map((step) => ({
            name: step.name.trim(),
            command: step.command.trim(),
          })),
        };
      } else {
        // 单命令模式
        deployConfig = {
          channel: form.deployChannel ||"agent",
          type:
            form.deployMode ==="docker_compose"
              ?"docker_compose"
              :"docker_run",
          command:
            form.deployMode ==="docker_run"
              ? form.runCommand.trim()
              : form.composeCommand.trim(),
        };

        if (form.deployMode ==="docker_compose") {
          deployConfig.compose_content = form.composeContent.trim();
          // 添加 compose_mode 和 redeploy_strategy
          if (form.deployChannel !=="portainer" && form.composeMode) {
            deployConfig.compose_mode = form.composeMode;
          }
          if (form.redeployStrategy) {
            deployConfig.redeploy_strategy = form.redeployStrategy;
          }
          if (form.deployChannel ==="portainer") {
            deployConfig.stack_strategy = form.stackStrategy ||"create_new";
            if (form.selectedStackId) {
              deployConfig.stack_id = form.selectedStackId;
            }
            if (form.newStackName && form.newStackName.trim()) {
              deployConfig.stack_name = form.newStackName.trim();
            }
          }
        }
      }

      if (form.redeploy) {
        deployConfig.redeploy = true;
      }

      const yamlConfig = {
        version:"1.0",
        app: {
          name: form.appName,
        },
        deploy: deployConfig,
        targets: targets,
      };

      return yaml.dump(yamlConfig, {
        defaultFlowStyle: false,
        allowUnicode: true,
      });
    },
    async copyTask(task) {
      // 显示确认提示
      // 尝试多种方式获取应用名称
      let appName ="未知任务";
      if (task.app_name) {
        appName = task.app_name;
      } else if (task.config && task.config.app && task.config.app.name) {
        appName = task.config.app.name;
      } else if (task.status && task.status.app_name) {
        appName = task.status.app_name;
      } else if (task.task_id) {
        appName = `任务 ${task.task_id.substring(0, 8)}`;
      }

      // 显示确认对话框
      const confirmed = await showConfirm({ message: `确定要克隆部署任务"${appName}" 吗？\n\n` +
          `克隆后将创建一个新的任务，使用相同的配置。\n\n` +
          `点击"确定"继续，点击"取消"放弃。` });

      if (!confirmed) {
        return;
      }

      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`);
        const taskData = res.data.task;

        // 创建新任务（使用相同的配置）
        let configContent =
          taskData.config_content ||
          (taskData.task_config && taskData.task_config.config_content) ||"";
        const taskConfig = taskData.task_config || {};
        // 部署配置的 app 名全局唯一，克隆时必须改名，否则后端会报「应用名称已存在」
        try {
          const cfg = yaml.load(configContent);
          if (cfg && typeof cfg ==="object") {
            const base =
              (cfg.app && typeof cfg.app ==="object" && cfg.app.name) ||
              cfg.app_name ||"app";
            const suffix =
              typeof crypto !=="undefined" && crypto.randomUUID
                ? crypto.randomUUID().replace(/-/g,"").slice(0, 8)
                : String(Date.now());
            const newAppName = `${base}-clone-${suffix}`;
            if (!cfg.app || typeof cfg.app !=="object") {
              cfg.app = {};
            }
            cfg.app.name = newAppName;
            configContent = yaml.dump(cfg, {
              defaultFlowStyle: false,
              allowUnicode: true,
            });
          }
        } catch (e) {
          console.warn("克隆时无法改写应用名称，将使用原始配置:", e);
        }
        const createRes = await axios.post("/api/deploy-tasks", {
          config_content: configContent,
          registry:
            (taskData.status && taskData.status.registry) ||
            taskConfig.registry ||
            null,
          tag:
            (taskData.status && taskData.status.tag) || taskConfig.tag || null,
        });

        toastSuccess("任务克隆成功！\n\n已创建新的部署任务，您可以对其进行编辑和执行。");
        this.loadTasks();

        // 如果详情模态框打开，刷新显示
        if (
          this.showDetailModal &&
          this.selectedTask?.task_id === task.task_id
        ) {
          // 可以选择打开新任务或保持当前任务
        }
      } catch (error) {
        console.error("复制任务失败:", error);
        toastError("克隆任务失败:" + (error.response?.data?.detail || error.message));
      }
    },
    async refreshTask(task) {
      // 刷新任务状态
      await this.loadTasks();
      // 如果详情模态框打开，重新加载任务详情和日志
      if (this.showDetailModal && this.selectedTask?.task_id === task.task_id) {
        await this.viewTask(task);
      }
    },
    formatLogMessage(message) {
      // 格式化日志消息，支持简单的HTML标记
      if (!message) return"";
      // 转义HTML，但保留换行
      return message
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/\n/g,"<br>");
    },
    getLogLineClass(log) {
      // 根据日志消息内容返回样式类
      // log可能是字符串或对象
      const message =
        typeof log ==="string" ? log : log.log_message || log.message ||"";
      if (!message) return"";
      const msg = message.toLowerCase();
      if (
        msg.includes("错误") ||
        msg.includes("error") ||
        msg.includes("失败") ||
        msg.includes("failed") ||
        msg.includes("❌")
      ) {
        return"text-danger";
      }
      if (
        msg.includes("成功") ||
        msg.includes("success") ||
        msg.includes("完成") ||
        msg.includes("completed") ||
        msg.includes("✅")
      ) {
        return"text-green-600";
      }
      if (
        msg.includes("警告") ||
        msg.includes("warning") ||
        msg.includes("⚠️")
      ) {
        return"text-amber-600";
      }
      if (
        msg.includes("信息") ||
        msg.includes("info") ||
        msg.includes("📦") ||
        msg.includes("🚀")
      ) {
        return"text-info";
      }
      return"text-light";
    },
    generateUUID() {
      return"xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
        /[xy]/g,
        function (c) {
          const r = (Math.random() * 16) | 0;
          const v = c ==="x" ? r : (r & 0x3) | 0x8;
          return v.toString(16);
        }
      );
    },
    async regenerateEditWebhookToken() {
      if (await showConfirm({ message:"确定要重新生成 Webhook Token 吗？重新生成后需要更新外部系统的 Webhook URL。" })) {
        this.editForm.webhook_token = this.generateUUID();
      }
    },
    async regenerateEditWebhookSecret() {
      if (await showConfirm({ message:"确定要重新生成 Webhook Secret 吗？重新生成后需要更新外部系统的 Webhook Secret。" })) {
        this.editForm.webhook_secret = this.generateUUID();
      }
    },
    showEditWebhookUrl() {
      const token = this.editForm.webhook_token ||"未设置";
      const baseUrl = window.location.origin
        .replace(":3000",":8000")
        .replace(":5173",":8000");
      this.webhookUrl =
        token !=="未设置"
          ? `${baseUrl}/api/webhook/deploy/${token}`
          :"请先设置 Webhook Token";
      this.showWebhookModal = true;
    },
    getWebhookUrl(task) {
      const token = task.webhook_token;
      if (!token) return"";
      // 使用后端API的URL（通常是8000端口），而不是前端开发服务器的URL
      // 如果前端和后端在同一域名下，使用window.location.origin
      // 否则需要配置后端URL
      const baseUrl = window.location.origin
        .replace(":3000",":8000")
        .replace(":5173",":8000");
      return `${baseUrl}/api/webhook/deploy/${token}`;
    },
    showWebhookUrl(task) {
      const url = this.getWebhookUrl(task);
      if (!url) {
        toastError('Webhook URL 未配置，请在编辑配置的"Webhook设置"tab中配置。');
        return;
      }
      this.webhookUrl = url;
      this.showWebhookModal = true;
    },
    async copyWebhookUrlFromModal() {
      if (this.$refs.webhookUrlInput) {
        const success = await copyToClipboard(this.$refs.webhookUrlInput.value);
        if (success) {
          toastSuccess("Webhook URL 已复制到剪贴板");
        } else {
          toastError("复制失败，请手动选择文本复制");
        }
      }
    },
  },
};
</script>

<style scoped>
</style>
