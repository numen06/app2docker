from pathlib import Path

p = Path("frontend/src/components/DataSourcePanel.vue")
t = p.read_text(encoding="utf-8")
start = t.index('      <div v-for="source in sources"')
end = t.index("\n\n    <!-- 创建/编辑数据源模态框 -->", start)

new = r'''      <Card
        v-for="source in sources"
        :key="source.source_id"
        class="flex h-full flex-col transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <CardHeader class="space-y-3 border-b border-slate-100 pb-3">
          <div>
            <CardTitle class="text-base">{{ source.name }}</CardTitle>
            <p v-if="source.description" class="mt-1 text-sm text-slate-500">
              {{ source.description }}
            </p>
          </div>
          <div class="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              class="flex-1"
              :disabled="refreshing === source.source_id"
              title="刷新分支和标签"
              @click="refreshSource(source)"
            >
              <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshing === source.source_id }"></i>
            </Button>
            <Button variant="outline" size="sm" class="flex-1" title="编辑" @click="editSource(source)">
              <i class="fas fa-edit"></i>
            </Button>
            <Button variant="destructive" size="sm" class="flex-1" title="删除" @click="deleteSource(source)">
              <i class="fas fa-trash"></i>
            </Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-3 p-4 text-sm">
          <div class="flex gap-2 text-slate-600">
            <i class="fas fa-code-branch mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <code class="truncate font-mono text-xs text-slate-800" :title="source.git_url">{{
              formatGitUrl(source.git_url)
            }}</code>
          </div>
          <div class="space-y-1 text-slate-600">
            <div class="flex gap-2">
              <i class="fas fa-code-branch mt-0.5 w-4 shrink-0 text-slate-400"></i>
              <span>分支：{{ source.branches?.length || 0 }} 个</span>
            </div>
            <div class="flex gap-2">
              <i class="fas fa-tag mt-0.5 w-4 shrink-0 text-slate-400"></i>
              <span>标签：{{ source.tags?.length || 0 }} 个</span>
            </div>
            <div v-if="source.default_branch" class="flex gap-2">
              <i class="fas fa-check-circle mt-0.5 w-4 shrink-0 text-green-600"></i>
              <span>默认分支：{{ source.default_branch }}</span>
            </div>
            <div class="flex gap-2">
              <i class="fab fa-docker mt-0.5 w-4 shrink-0 text-sky-500"></i>
              <span
                >Dockerfile：{{
                  (source.dockerfiles && Object.keys(source.dockerfiles).length) || 0
                }}
                个</span
              >
            </div>
          </div>
          <Button variant="outline" size="sm" class="w-full" @click="manageDockerfiles(source)">
            <i class="fab fa-docker"></i> 管理 Dockerfile
          </Button>
          <div class="border-t border-slate-200 pt-2 text-xs text-slate-500">
            <div>创建时间：{{ formatDateTime(source.created_at) }}</motionless-host-manager />
            <div v-if="source.updated_at !== source.created_at">
              更新时间：{{ formatDateTime(source.updated_at) }}
            </div>
          </div>
        </CardContent>
      </Card>
'''

# strip erroneous placeholders
bad = "motionless-host-manager"
new = new.replace(f"<{bad} />", "")
new = new.replace(f"</{bad} />", "</div>")
new = new.replace(f"            <{bad} />", "")

t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
print("patched cards")
