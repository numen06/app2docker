<template>
  <div class="pipeline-create-step-git pipeline-config-pane">
    <div class="card">
      <div class="card-header bg-light">
        <h6 class="mb-0">
          <i class="fas fa-code-branch text-blue-600"></i> Git 仓库
        </h6>
      </div>
      <div class="card-body">
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
            <div class="form-text small text-slate-500 mt-1">
              <i class="fas fa-info-circle"></i>
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
            <div class="input-group">
              <select
                v-if="repoVerified || formData.source_id || formData.git_url"
                v-model="formData.branch"
                class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                :disabled="
                  refreshingBranches ||
                  (!repoVerified && !formData.source_id && !formData.git_url)
                "
                @change="onBranchChanged"
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
                <i
                  v-if="refreshingBranches"
                  class="fas fa-spinner fa-spin"
                ></i>
                <i v-else class="fas fa-sync-alt"></i>
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
