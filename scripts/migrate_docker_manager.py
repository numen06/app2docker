"""Migrate DockerManager.vue template to shadcn/ui."""
import re
from pathlib import Path

p = Path("frontend/src/components/DockerManager.vue")
t = p.read_text(encoding="utf-8")
tpl_start = t.index("<template>")
tpl_end = t.index("</template>") + len("</template>")
script = t[tpl_end:]

tpl = t[tpl_start:tpl_end]

# spinners
tpl = re.sub(
    r'<div class="spinner-border spinner-border-sm[^"]*"></motionless-host-manager />',
    '<i class="fas fa-spinner fa-spin text-blue-600"></i>',
    tpl,
)
tpl = tpl.replace(
    '<motionless-host-manager />',
    "",
)
tpl = re.sub(
    r'<div class="spinner-border spinner-border-sm[^"]*"></div>',
    '<i class="fas fa-spinner fa-spin text-blue-600"></i>',
    tpl,
)

# outer wrapper
tpl = tpl.replace('<motionless-host-manager />', "")
tpl = tpl.replace('class="docker-manager"', 'class="space-y-4"')

# info card shell
tpl = tpl.replace(
    '<div class="card mb-3">',
    '<Card class="mb-4 overflow-hidden">',
    1,
)
tpl = tpl.replace(
    'class="card-header bg-primary text-white flex justify-between items-center py-2"',
    'class="flex flex-wrap items-center justify-between gap-2 border-0 bg-blue-600 px-4 py-3 text-white"',
    1,
)
tpl = tpl.replace('<div class="card-body py-2">', '<CardContent class="space-y-3 p-4">', 1)

# buttons in header
tpl = tpl.replace(
    """          <button
            class="btn btn-sm btn-light"
            @click="refreshDockerInfo(false)"
            :disabled="loadingInfo"
            title="刷新（使用缓存）"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingInfo }"></i>
          </button>""",
    """          <Button
            variant="secondary"
            size="sm"
            @click="refreshDockerInfo(false)"
            :disabled="loadingInfo"
            title="刷新（使用缓存）"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingInfo }"></i>
          </Button>""",
)
tpl = tpl.replace(
    """          <button
            class="btn btn-sm btn-warning"
            @click="forceRefreshDockerInfo()"
            :disabled="loadingInfo"
            title="强制刷新（重新获取）"
          >
            <i class="fas fa-sync-alt fa-spin" v-if="loadingInfo"></i>
            <i class="fas fa-redo" v-else></i>
            <span class="ml-1 d-none d-md-inline">强制刷新</span>
          </button>""",
    """          <Button
            variant="outline"
            size="sm"
            class="border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100"
            @click="forceRefreshDockerInfo()"
            :disabled="loadingInfo"
            title="强制刷新（重新获取）"
          >
            <i class="fas fa-sync-alt fa-spin" v-if="loadingInfo"></i>
            <i class="fas fa-redo" v-else></i>
            <span class="ml-1 hidden md:inline">强制刷新</span>
          </Button>""",
)

# alert blocks
tpl = tpl.replace('class="alert alert-warning mb-0 py-2"', 'variant="warning" message="" class="!mt-0"')
# skip complex alert - use AlertBanner later

# tabs
tpl = tpl.replace(
    """      <div class="card-header bg-white py-0">
        <ul class="nav nav-tabs border-0">""",
    """      <div class="border-b border-slate-200 px-2">
        <div class="flex gap-1">""",
)
tpl = tpl.replace("<li class=\"nav-item\">", "")
tpl = tpl.replace("</li>", "")
tpl = tpl.replace(
    'class="nav-link"',
    'type="button" class="border-b-2 px-4 py-2 text-sm font-medium transition"',
)
tpl = tpl.replace(
    ":class=\"{ active: activeTab === 'containers' }\"",
    ":class=\"activeTab === 'containers' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800'\"",
)
tpl = tpl.replace(
    ":class=\"{ active: activeTab === 'images' }\"",
    ":class=\"activeTab === 'images' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-800'\"",
)
tpl = tpl.replace("</ul>", "</div>")

# second card
tpl = tpl.replace('<div class="card">', '<Card>', 1)

# loading text center
tpl = tpl.replace('class="text-center py-3"', 'class="flex items-center justify-center gap-2 py-8 text-sm text-slate-500"')
tpl = tpl.replace('class="text-center py-4"', 'class="flex flex-col items-center justify-center gap-2 py-12 text-sm text-slate-500"')

# imports in script
imp = """
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import { Badge } from "@/components/ui/badge";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
"""
if "@/components/ui/button/Button.vue" not in script:
    script = script.replace("import axios", imp + "import axios", 1)
script = re.sub(r"\n<style scoped>.*?</style>\s*$", "\n", script, flags=re.DOTALL)

p.write_text(t[:tpl_start] + tpl + script, encoding="utf-8")
print("docker manager partial migrate ok")
