#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate DeployTaskManager.vue template: Bootstrap -> Tailwind + shadcn/ui."""
import re
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "DeployTaskManager.vue"

LIST_VIEW = r"""    <PageToolbar title="部署配置管理" icon="fa-rocket">
      <template #actions>
        <Button variant="outline" size="sm" @click="showImportModal = true">
          <i class="fas fa-file-import mr-1"></i> 导入配置
        </Button>
        <Button size="sm" @click="openSimpleCreateModal('standard')">
          <i class="fas fa-plus mr-1"></i>
          新建 SSH/Agent 部署
        </Button>
        <Button variant="outline" size="sm" @click="openSimpleCreateModal('portainer')">
          <i class="fas fa-cubes mr-1"></i> 新建 Portainer 部署
        </Button>
        <Button variant="secondary" size="sm" @click="showCreateModal = true">
          <i class="fas fa-code mr-1"></i> YAML创建
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
      </motion>
    </div>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState v-else-if="filteredTasks.length === 0" message="暂无符合筛选条件的部署配置" />

    <Table v-else min-width-class="min-w-[64rem]">
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
          <TableCell>{{ task.app_name || task.config?.app?.name || "-" }}</TableCell>
          <TableCell>
            <Badge v-for="(target, idx) in task.config?.targets || []" :key="idx" variant="default" class="mr-1">
              {{ target.name || target.host_name || "-" }}
            </Badge>
          </TableCell>
          <TableCell>
            <Badge variant="info" class="mr-1">
              <i class="fas fa-play-circle mr-1"></i>{{ task.execution_count || 0 }}
            </Badge>
            <Button v-if="task.execution_count > 0" variant="ghost" size="sm" class="h-auto p-0 text-xs" @click="viewExecutions(task)" title="查看执行历史">
              <i class="fas fa-external-link-alt"></i>
            </Button>
          </TableCell>
          <TableCell class="whitespace-nowrap text-sm text-slate-600">{{ formatTime(task.created_at) }}</TableCell>
          <TableCell>
            <div class="flex flex-col">
              <span class="text-sm">{{ formatTime(task.last_executed_at) || "-" }}</span>
              <span v-if="task.status?.trigger_source" class="text-xs text-slate-500">
                <span v-if="task.status.trigger_source === 'webhook'"><i class="fas fa-link text-green-600 mr-1"></i> Webhook</span>
                <span v-else-if="task.status.trigger_source === 'manual'"><i class="fas fa-user text-blue-600 mr-1"></i> 手动</span>
                <span v-else-if="task.status.trigger_source === 'cron'"><i class="fas fa-clock text-amber-600 mr-1"></i> 定时</span>
                <span v-else><i class="fas fa-question-circle text-slate-400 mr-1"></i>{{ task.status.trigger_source }}</span>
              </span>
            </div>
          </TableCell>
          <TableCell>
            <div class="flex flex-wrap gap-1">
              <Button variant="outline" size="sm" @click="viewTask(task)" title="查看详情"><i class="fas fa-eye"></i></Button>
              <Button variant="outline" size="sm" @click="executeTask(task)" title="触发部署（将创建新任务）"><i class="fas fa-play"></i> 触发</Button>
              <Button v-if="task.webhook_token" variant="outline" size="sm" @click="showWebhookUrl(task)" title="查看 Webhook URL"><i class="fas fa-link"></i></Button>
              <Button variant="outline" size="sm" @click="editTask(task)" title="编辑配置"><i class="fas fa-edit"></i></Button>
              <Button variant="outline" size="sm" @click="copyTask(task)" title="复制配置"><i class="fas fa-copy"></i></Button>
              <Button variant="destructive" size="sm" @click="deleteTask(task)" title="删除配置"><i class="fas fa-trash"></i></Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <PaginationBar
      v-if="!loading && totalTasks > pageSize"
      :page="currentPage"
      :page-size="pageSize"
      :total="totalTasks"
      :total-pages="totalPages"
      @update:page="goToPage"
    />

""".replace("</motion>", "</motion>").replace("<motion", "<motion")  # fix below

LIST_VIEW = LIST_VIEW.replace("</motion>\n    </motion>", "</div>\n    </div>").replace(
    '<motion class="flex flex-wrap gap-1"', '<motion class="flex flex-wrap gap-1"'
)
# Fix the typo I introduced
LIST_VIEW = LIST_VIEW.replace("</motion>\n    </div>", "</div>\n    </motion>")
LIST_VIEW = LIST_VIEW.replace('<motion class="flex flex-wrap gap-1"', '<div class="flex flex-wrap gap-1"')
if "</motion>" in LIST_VIEW:
    LIST_VIEW = LIST_VIEW.replace("</motion>", "</div>")

COMPONENTS_IMPORTS = """import PageToolbar from "@/components/ui/PageToolbar.vue";
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
"""

COMPONENTS_REG = """  components: {
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
  },
"""

MODAL_HEADER_RE = re.compile(
    r"    <!-- (?P<comment>[^>]+) -->\s*"
    r'<div\s+v-if="(?P<cond>[^"]+)"\s+class="modal[^"]*"[^>]*>\s*'
    r'<div class="modal-dialog(?:\s+modal-(?P<size>lg|xl))?">\s*'
    r'<div class="modal-content">\s*'
    r'<div class="modal-header">.*?</motion>\s*'
    r'<div class="modal-body">',
    re.DOTALL,
)

# Simpler: strip modal shell via string replacements per modal type
MODAL_SHELL_START = re.compile(
    r'    <!-- .+? -->\s*<div\s+v-if="[^"]+"\s+class="modal[^"]*"[^>]*>\s*'
    r'<div class="modal-dialog[^"]*">\s*<div class="modal-content">\s*'
    r'<div class="modal-header">[\s\S]*?</div>\s*<div class="modal-body">',
    re.MULTILINE,
)

TEXTAREA_CLS = (
    "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-mono "
    "shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
)
INPUT_CLS = (
    "flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm "
    "shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
)

UTIL = [
    (r"\bd-flex\b", "flex"),
    (r"\bd-block\b", "block"),
    (r"\bflex-column\b", "flex-col"),
    (r"\bjustify-content-between\b", "justify-between"),
    (r"\bjustify-content-center\b", "justify-center"),
    (r"\balign-items-center\b", "items-center"),
    (r"\balign-items-start\b", "items-start"),
    (r"\btext-muted\b", "text-slate-500"),
    (r"\btext-danger\b", "text-red-500"),
    (r"\btext-success\b", "text-green-600"),
    (r"\btext-primary\b", "text-blue-600"),
    (r"\btext-warning\b", "text-amber-600"),
    (r"\bfont-monospace\b", "font-mono"),
    (r"\bw-100\b", "w-full"),
    (r"\bme-1\b", "mr-1"),
    (r"\bme-2\b", "mr-2"),
    (r"\bms-1\b", "ml-1"),
    (r"\bms-2\b", "ml-2"),
    (r"\bms-3\b", "ml-3"),
    (r"\bpy-5\b", "py-12"),
    (r"<span\s+class=\"spinner-border(?:\s+spinner-border-sm)?[^\"]*\"\s*></span>", '<i class="fas fa-spinner fa-spin"></i>'),
    (r'class="card mb-3"', 'class="mb-3 rounded-lg border border-slate-200 bg-white"'),
    (r'class="card-header bg-light"', 'class="border-b border-slate-200 bg-slate-50 px-4 py-3"'),
    (r'class="card-body"', 'class="p-4"'),
    (r'class="card mb-2 step-card"', 'class="mb-2 rounded-lg border border-slate-200 p-4"'),
    (r'class="alert alert-info mb-0"', 'class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900"'),
    (r'class="alert alert-info small mb-0"', 'class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900"'),
    (r'class="alert alert-danger mb-3"', 'class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 mb-3"'),
    (r'class="input-group input-group-sm"', 'class="flex gap-2"'),
    (r'class="input-group"', 'class="flex gap-2"'),
    (r'class="invalid-feedback d-block"', 'class="mt-1 text-xs text-red-500"'),
    (r'class="row"', 'class="grid grid-cols-1 gap-3 md:grid-cols-2"'),
    (r'class="col-md-6"', 'class=""'),
    (r'class="bg-dark text-light p-3 rounded"', 'class="max-h-[500px] overflow-y-auto rounded-lg bg-slate-900 p-3 text-slate-100"'),
    (r'class="log-container bg-dark text-light p-3 rounded"', 'class="max-h-[600px] overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100"'),
    (r'class="table table-sm mt-2"', 'class="mt-2 w-full border-collapse text-sm"'),
    (r'<h6 class="mb-0">', '<h6 class="text-sm font-semibold text-slate-900">'),
]


def extract_modal(tpl: str, comment: str) -> tuple[str, str, str] | None:
    marker = f"    <!-- {comment} -->"
    i = tpl.find(marker)
    if i < 0:
        return None
    body_start = tpl.find('<motion class="modal-body">', i)
    if body_start < 0:
        body_start = tpl.find('<div class="modal-body">', i)
    if body_start < 0:
        return None
    body_start = tpl.find(">", body_start) + 1
    footer_start = tpl.find('<div class="modal-footer">', body_start)
    has_footer = footer_start >= 0
    if has_footer:
        body = tpl[body_start:footer_start].strip()
        footer_start = tpl.find(">", footer_start) + 1
        # footer ends before closing modal divs
        footer_end = tpl.find("</div>\n        </div>\n      </div>\n    </div>", footer_start)
        if footer_end < 0:
            footer_end = tpl.find("</div>\n        </div>\n      </div>\n    </div>\n", footer_start)
        footer = tpl[footer_start:footer_end].strip() if footer_end > 0 else ""
        block_end = footer_end + len("</div>\n        </motion>\n      </div>\n    </div>")
        if block_end < footer_start:
            block_end = tpl.find("\n    <!-- ", footer_start + 10)
            if block_end < 0:
                block_end = len(tpl)
        else:
            block_end = tpl.find("\n    <!-- ", i + 20)
            if block_end < 0:
                block_end = len(tpl)
    else:
        # webhook - no footer
        body_end = tpl.find("</div>\n        </div>\n      </div>\n    </div>", body_start)
        body = tpl[body_start:body_end].strip()
        footer = ""
        block_end = body_end + len("</div>\n        </div>\n      </div>\n    </div>")
    full_block = tpl[i:block_end]
    return full_block, body, footer


def build_form_dialog(model, title, icon, size, close, body, footer="") -> str:
    title_attr = f'title="{title}"'
    if "编辑部署" in title:
        title_attr = ':title="\'编辑部署任务 - \' + editingTask.task_id.substring(0, 8)"'
    elif "任务详情" in title:
        title_attr = ':title="\'任务详情 - \' + selectedTask.task_id.substring(0, 8)"'

    footer_slot = ""
    if footer.strip():
        footer_slot = f"\n      <template #footer>\n        {footer}\n      </template>"

    return f"""    <FormDialog
      :model-value="{model}"
      {title_attr}
      icon="{icon}"
      size="{size}"
      @update:model-value="(v) => !v && ({close})"
    >
      {body}{footer_slot}
    </FormDialog>
"""


def migrate_template(tpl: str) -> str:
    list_end = tpl.find("    <!-- 简易创建任务模态框 -->")
    tpl = LIST_VIEW + tpl[list_end:]

    modals = [
        ("简易创建任务模态框", "showSimpleCreateModal", "快速创建部署任务", "fa-rocket", "xl", "closeSimpleCreateModal()"),
        ("YAML创建任务模态框", "showCreateModal", "YAML方式创建部署任务", "fa-code", "lg", "showCreateModal = false"),
        ("导入任务模态框", "showImportModal", "导入部署配置", "fa-file-import", "md", "showImportModal = false"),
        ("任务详情模态框", "showDetailModal && selectedTask", "任务详情", "fa-info-circle", "xl", "showDetailModal = false"),
        ("编辑任务模态框", "showEditModal && editingTask", "编辑部署任务", "fa-edit", "xl", "closeEditModal()"),
        ("Webhook URL 模态框", "showWebhookModal", "Webhook URL", "fa-link", "md", "showWebhookModal = false"),
    ]

    for comment, model, title, icon, size, close in modals:
        marker = f"    <!-- {comment} -->"
        pos = tpl.find(marker)
        if pos < 0:
            print(f"skip modal: {comment}")
            continue
        next_pos = len(tpl)
        for c, *_ in modals:
            if c == comment:
                continue
            p2 = tpl.find(f"    <!-- {c} -->", pos + 10)
            if p2 > pos:
                next_pos = min(next_pos, p2)
        block = tpl[pos:next_pos]
        # parse body/footer manually from block
        bs = block.find('<div class="modal-body">')
        if bs < 0:
            continue
        bs = block.find(">", bs) + 1
        fs = block.find('<div class="modal-footer">')
        if fs > 0:
            body = block[bs:fs].strip()
            fs = block.find(">", fs) + 1
            fe = block.rfind("</div>\n        </div>\n      </div>\n    </div>")
            footer = block[fs:fe].strip() if fe > fs else ""
        else:
            fe = block.rfind("</div>\n        </div>\n      </div>\n    </div>")
            body = block[bs:fe].strip()
            footer = ""
        new_block = build_form_dialog(model, title, icon, size, close, body, footer)
        tpl = tpl[:pos] + new_block + tpl[next_pos:]

    tpl = re.sub(
        r"\s*<div\s+v-if=\"showWebhookModal\"\s+class=\"modal-backdrop[^\"]*\"[^>]*></motion>\s*",
        "\n",
        tpl,
    )

    for pat, repl in UTIL:
        tpl = re.sub(pat, repl, tpl)

    # nav tabs (detail modal)
    tpl = tpl.replace('<ul class="nav nav-tabs mb-3">', '<div class="mb-3 flex gap-1 border-b border-slate-200">')
    tpl = re.sub(r"<li class=\"nav-item\">\s*", "", tpl)
    tpl = re.sub(r"\s*</li>", "", tpl)
    tpl = tpl.replace(
        'class="nav-link"',
        'type="button" class="border-b-2 border-transparent px-3 py-2 text-sm font-medium text-slate-500 hover:text-slate-700"',
    )
    tpl = tpl.replace(
        ":class=\"{ active: detailTab === 'config' }\"",
        ":class=\"detailTab === 'config' ? 'border-blue-600 text-blue-600' : 'border-transparent'\"",
    )
    tpl = tpl.replace(
        ":class=\"{ active: detailTab === 'status' }\"",
        ":class=\"detailTab === 'status' ? 'border-blue-600 text-blue-600' : 'border-transparent'\"",
    )
    tpl = tpl.replace(
        ":class=\"{ active: detailTab === 'logs' }\"",
        ":class=\"detailTab === 'logs' ? 'border-blue-600 text-blue-600' : 'border-transparent'\"",
    )
    tpl = tpl.replace("</ul>\n\n            <div v-if=\"detailTab", "</div>\n\n            <div v-if=\"detailTab")

    # labels
    tpl = tpl.replace('<label class="form-label', "<Label")
    tpl = tpl.replace('<label class="form-label small"', '<Label class="text-xs"')

    # selects
    tpl = re.sub(
        r"<select([^>]*) class=\"form-select(?: form-select-sm)?\"",
        r"<NativeSelect\1 class=\"\"",
        tpl,
    )
    tpl = tpl.replace("</select>", "</NativeSelect>")

    # textareas
    tpl = tpl.replace('class="form-control font-monospace"', f'class="{TEXTAREA_CLS}"')

    # inputs -> Input (skip file/checkbox/radio)
    def input_sub(m):
        tag = m.group(0)
        if re.search(r'type="(file|checkbox|radio)"', tag):
            return re.sub(r'class="form-control[^"]*"', f'class="{INPUT_CLS}"', tag)
        if "form-control" in tag:
            tag = tag.replace("<input", "<Input")
            tag = re.sub(r'\s*class="form-control[^"]*"', "", tag)
            tag = re.sub(r'\s*class="form-control-sm[^"]*"', ' class="text-sm"', tag)
        return tag

    tpl = re.sub(r"<input\b[^>]*>", input_sub, tpl)

    # buttons
    def btn_sub(m):
        attrs = m.group(1)
        cls = m.group(2)
        rest = m.group(3)
        variant = "default"
        sz = ' size="sm"' if "btn-sm" in cls else ""
        if "btn-secondary" in cls:
            variant = "secondary"
        elif "btn-outline" in cls:
            variant = "outline"
        elif "btn-danger" in cls:
            variant = "destructive"
        elif "btn-link" in cls:
            variant = "ghost"
        return f"<Button{attrs}variant=\"{variant}\"{sz}{rest}>"

    tpl = re.sub(r"<button(\s[^>]*?)class=\"([^\"]*btn[^\"]*)\"([^>]*)>", btn_sub, tpl, flags=re.I)
    tpl = tpl.replace("</button>", "</Button>")

    # static badges
    tpl = tpl.replace('class="badge bg-secondary me-1"', 'variant="default" class="mr-1"')
    tpl = tpl.replace("<span class=\"badge bg-info\">", "<Badge variant=\"info\">")
    tpl = tpl.replace('class="badge bg-info ms-1"', 'variant="info" class="ml-1"')
    tpl = tpl.replace('class="badge bg-primary me-2"', 'variant="default" class="mr-2"')

    # dynamic status badges
    tpl = re.sub(
        r'<span\s+:class="getStatusBadgeClass\(([^)]+)\)"\s+class="badge ms-1"\s*>',
        r'<Badge :variant="\1 === \'completed\' ? \'success\' : \1 === \'failed\' ? \'danger\' : \1 === \'running\' ? \'info\' : \'default\'" class="ml-1">',
        tpl,
    )
    tpl = re.sub(
        r'<span\s+:class="getStatusBadgeClass\(selectedTask\.status\)"\s+class="badge ms-2"\s*>',
        r'<Badge :variant="selectedTask.status === \'completed\' ? \'success\' : selectedTask.status === \'failed\' ? \'danger\' : selectedTask.status === \'running\' ? \'info\' : \'default\'" class="ml-2">',
        tpl,
    )

    # wrap static badge spans that became Badge - fix closing tags for bg-info host badges
    tpl = re.sub(r"<Badge variant=\"info\">\{\{\s*target\.host_type", "<Badge variant=\"info\">{{ target.host_type", tpl)

    return tpl


def process():
    text = TARGET.read_text(encoding="utf-8")
    m = re.search(r"<template>\s*\n(.*?)\n</template>", text, re.DOTALL)
    inner = migrate_template(m.group(1))
    text = text[: m.start(1)] + inner + text[m.end(1) :]

    if "PageToolbar" not in text:
        text = text.replace(
            'import { copyToClipboard } from "../utils/clipboard.js";',
            'import { copyToClipboard } from "../utils/clipboard.js";\n' + COMPONENTS_IMPORTS,
        )
        text = text.replace(
            '  name: "DeployTaskManager",\n  data()',
            '  name: "DeployTaskManager",\n' + COMPONENTS_REG + "  data()",
        )

    text = re.sub(r"<style scoped>\s*\.modal[^<]*</style>", "<style scoped>\n</style>", text, flags=re.DOTALL)
    TARGET.write_text(text, encoding="utf-8")
    print("done", TARGET)


if __name__ == "__main__":
    process()
