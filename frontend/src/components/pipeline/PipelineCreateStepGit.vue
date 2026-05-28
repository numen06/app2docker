<template>
  <div class="pipeline-create-step-git pipeline-config-pane">
    <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <h6 class="mb-0">
          <AppIcon  name="code-branch" class="text-blue-600" /> Git 仓库
        </h6>
      </div>
      <div class="p-4">
        <div class="pipeline-field-grid pipeline-field-grid--2">
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
                {{ source.name }} ({{ formatGitUrl(source.git_url) }})
              </option>
            </select>
            <div class="text-xs text-slate-500 text-sm mt-1">
              <AppIcon  name="info-circle" />
              可从已保存的数据源选择，或手动输入仓库地址
            </div>
          </div>
          <div class="pipeline-field">
            <label class="block text-sm font-medium text-slate-700">
              Git 仓库地址 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formData.git_url"
              type="text"
              class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
              placeholder="https://github.com/user/repo.git"
            />
          </div>
          <div class="pipeline-field pipeline-field--full">
            <label class="block text-sm font-medium text-slate-700">分支名称</label>
            <div class="flex w-full">
              <select
                v-if="repoVerified || formData.source_id || formData.git_url"
                v-model="formData.branch"
                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                :disabled="
                  refreshingBranches ||
                  (!repoVerified && !formData.source_id && !formData.git_url)"
                @change="onBranchChanged"
              >
                <option value="">
                  使用默认分支 ({{ branchesAndTags.default_branch ||"main" }})
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
                  <option v-for="tag in branchesAndTags.tags" :key="tag" :value="tag">
                    {{ tag }}
                  </option>
                </optgroup>
              </select>
              <input
                v-else
                type="text"
                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                placeholder="请先选择数据源或填写仓库地址"
                disabled
              />
              <Button
                v-if="formData.source_id || formData.git_url"
                variant="outline"
                size="sm"
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
              <span v-if="refreshingBranches">正在刷新分支列表…</span>
              <span
                v-else-if="repoVerified && branchesAndTags.branches.length > 0"
              >
                已加载 {{ branchesAndTags.branches.length }} 个分支
              </span>
              <span v-else-if="formData.source_id || formData.git_url">
                点击刷新加载分支，或留空使用默认分支
              </span>
              <span v-else>请先填写 Git 信息</span>
            </small>
          </div>
          <div class="pipeline-field pipeline-field--full">
            <div class="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              <input
                v-model="formData.tag_build_enabled"
                class="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                type="checkbox"
                id="createGitTagBuildEnabled"
              />
              <div>
                <label class="text-sm font-medium text-slate-700" for="createGitTagBuildEnabled">
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
</template>

<script setup>
import { inject } from "vue";
import Button from "@/components/ui/button/Button.vue";

const editor = inject("pipelineEditor");

const {
  formData,
  gitSources,
  branchesAndTags,
  refreshingBranches,
  repoVerified,
  onSourceSelected,
  refreshBranches,
  onBranchChanged,
  formatGitUrl,
} = editor;
</script>
