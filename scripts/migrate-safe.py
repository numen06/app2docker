# -*- coding: utf-8 -*-
"""Safe exact-string Bootstrap -> shadcn migration."""
import re
import sys
from pathlib import Path

UI_IMPORTS = """import Button from '@/components/ui/button/Button.vue';
import FormDialog from '@/components/ui/dialog/FormDialog.vue';
import Input from '@/components/ui/input/Input.vue';
import Label from '@/components/ui/label/Label.vue';
import AlertBanner from '@/components/ui/AlertBanner.vue';
import { Badge } from '@/components/ui/badge';
import Card from '@/components/ui/card/Card.vue';
import CardHeader from '@/components/ui/card/CardHeader.vue';
import CardTitle from '@/components/ui/card/CardTitle.vue';
import CardContent from '@/components/ui/card/CardContent.vue';
import Table from '@/components/ui/table/Table.vue';
import TableHeader from '@/components/ui/table/TableHeader.vue';
import TableBody from '@/components/ui/table/TableBody.vue';
import TableRow from '@/components/ui/table/TableRow.vue';
import TableHead from '@/components/ui/table/TableHead.vue';
import TableCell from '@/components/ui/table/TableCell.vue';
import NativeSelect from '@/components/ui/select/NativeSelect.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import PageToolbar from '@/components/ui/PageToolbar.vue';
"""

BTN_OPEN = [
    ('<button class="btn btn-outline-danger"', '<Button variant="destructive" size="sm"'),
    ('<button class="btn btn-outline-success"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-outline-warning"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-outline-success"', '<Button variant="outline" size="sm"'),
    ('<button\n                class="btn btn-outline-success"', '<Button\n                variant="outline" size="sm"'),
    ('<button class="btn btn-outline-info"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-outline-primary"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-outline-secondary btn-sm"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-sm btn-outline-secondary"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-outline-secondary"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-secondary btn-sm"', '<Button variant="outline" size="sm"'),
    ('<button class="btn btn-secondary"', '<Button variant="outline"'),
    ('<button class="btn btn-primary btn-sm"', '<Button size="sm"'),
    ('<button class="btn btn-primary"', '<Button'),
    ('<button class="btn btn-info btn-sm"', '<Button size="sm"'),
    ('<button class="btn btn-success btn-sm"', '<Button size="sm"'),
    ('<button class="btn btn-danger btn-sm"', '<Button variant="destructive" size="sm"'),
    ('              <button class="btn btn-outline-info"', '              <Button variant="outline" size="sm"'),
    ('              <button class="btn btn-outline-primary"', '              <Button variant="outline" size="sm"'),
    ('              <button class="btn btn-outline-danger"', '              <Button variant="destructive" size="sm"'),
]

BADGE_OPEN = [
    ('<span class="badge bg-success"', '<Badge variant="success"'),
    ('<span class="badge bg-danger"', '<Badge variant="danger"'),
    ('<span class="badge bg-warning"', '<Badge variant="warning"'),
    ('<span class="badge bg-info"', '<Badge variant="info"'),
    ('<span class="badge bg-primary"', '<Badge variant="info"'),
    ('<span class="badge bg-secondary"', '<Badge variant="default"'),
    ('<span v-if="pipeline.enabled" class="badge bg-success"', '<Badge v-if="pipeline.enabled" variant="success"'),
    ('<span v-else class="badge bg-secondary"', '<Badge v-else variant="default"'),
]

FORM = [
    ('class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"'),
    ('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"'),
    ('class="form-label"', 'class="block text-sm font-medium text-slate-700"'),
    ('class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"'),
    ('class="form-select"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"'),
    ('class="alert alert-info', 'class="rounded-md border border-sky-200 bg-sky-50 text-sky-900 text-sm'),
    ('class="alert alert-success', 'class="rounded-md border border-green-200 bg-green-50 text-green-800 text-sm'),
    ('class="alert alert-warning', 'class="rounded-md border border-amber-200 bg-amber-50 text-amber-900 text-sm'),
    ('class="alert alert-danger', 'class="rounded-md border border-red-200 bg-red-50 text-red-800 text-sm'),
]

CARD = [
    ('class="card h-100 shadow-sm"', 'class="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm"'),
    ('class="card h-full shadow-sm"', 'class="flex h-full flex-col rounded-xl border border-slate-200 bg-white shadow-sm"'),
    ('class="card-header bg-white"', 'class="border-b border-slate-100 bg-white p-4"'),
    ('class="card-body"', 'class="p-4"'),
    ('class="card-footer bg-white"', 'class="border-t border-slate-100 bg-white p-4"'),
]


def fix_button_closes(tpl):
    out, i = [], 0
    while True:
        idx = tpl.find("<Button", i)
        if idx < 0:
            out.append(tpl[i:])
            break
        end = tpl.find("</button>", idx)
        if end < 0:
            out.append(tpl[i:])
            break
        out.append(tpl[i:end])
        out.append("</Button>")
        i = end + len("</button>")
    return "".join(out)


def fix_badge_closes(tpl):
    out, i = [], 0
    while True:
        idx = tpl.find("<Badge", i)
        if idx < 0:
            out.append(tpl[i:])
            break
        end = tpl.find("</span>", idx)
        if end < 0:
            out.append(tpl[i:])
            break
        out.append(tpl[i:end])
        out.append("</Badge>")
        i = end + len("</span>")
    return "".join(out)


def patch_tabs_agent(tpl):
    old = """    <motion-icon>
    <div class="card mb-3">
      <div class="card-body p-2">
        <ul class="nav nav-tabs nav-tabs-custom mb-0" role="tablist">"""
    old = """    <div class="card mb-3">
      <motion-icon>
      <div class="card-body p-2">
        <ul class="nav nav-tabs nav-tabs-custom mb-0" role="tablist">"""
    old = """    <motion-icon>
    <div class="card mb-3">
      <motion-icon>
      <div class="card-body p-2">
        <ul class="nav nav-tabs nav-tabs-custom mb-0" role="tablist">"""
    # exact from file
    start = tpl.find('    <div class="card mb-3">\n      <div class="card-body p-2">\n        <ul class="nav nav-tabs')
    if start < 0:
        return tpl
    end = tpl.find('    <!-- \u4e3b\u673a\u5217\u8868\u6807\u7b7e\u9875 -->', start)
    new = """    <Card class="mb-3">
      <CardContent class="p-2">
        <div class="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1" role="tablist">
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'hosts' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'hosts'"><i class="fas fa-server mr-1"></i> \u4e3b\u673a\u5217\u8868</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'secrets' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'secrets'"><i class="fas fa-key mr-1"></i> \u5bc6\u94a5\u7ba1\u7406</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'pending' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'pending'"><i class="fas fa-clock mr-1"></i> \u5f85\u52a0\u5165\u4e3b\u673a<Badge v-if="pendingHostsCount > 0" variant="danger" class="ml-1">{{ pendingHostsCount }}</Badge></button>
        </div>
      </CardContent>
    </Card>

"""
    return tpl[:start] + new + tpl[end:]


def patch_pipeline_header(tpl):
    old = """    <div class="flex justify-between items-center mb-3">
      <h5 class="mb-0"><i class="fas fa-project-diagram"></i> \u6d41\u6c34\u7ebf\u7ba1\u7406</h5>
      <div class="flex gap-2">
        <button
          class="btn btn-outline-secondary btn-sm"
          @click="loadPipelines"
          :disabled="loading"
          title="刷新列表"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> \u5237\u65b0
        </button>
        <button class="btn btn-primary btn-sm" @click="showCreateModal">
          <i class="fas fa-plus"></i> \u65b0\u5efa\u6d41\u6c34\u7ebf
        </button>
        <button class="btn btn-info btn-sm" @click="openJsonCreateModal">
          <i class="fas fa-code"></i> \u901a\u8fc7JSON\u521b\u5efa
        </button>
      </div>
    </div>"""
    new = """    <PageToolbar title="\u6d41\u6c34\u7ebf\u7ba1\u7406" icon="fa-project-diagram">
      <template #actions>
        <Button variant="outline" size="sm" :disabled="loading" title="\u5237\u65b0\u5217\u8868" @click="loadPipelines">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> \u5237\u65b0
        </Button>
        <Button size="sm" @click="showCreateModal">
          <i class="fas fa-plus"></i> \u65b0\u5efa\u6d41\u6c34\u7ebf
        </Button>
        <Button size="sm" @click="openJsonCreateModal">
          <i class="fas fa-code"></i> \u901a\u8fc7JSON\u521b\u5efa
        </Button>
      </template>
    </PageToolbar>"""
    return tpl.replace(old, new, 1)


def migrate_modal_block(tpl, cond, close_handler, title, body_footer_split_marker="modal-footer"):
    """Simplified: strip modal wrapper classes to tailwind overlay - keep structure for now."""
    pat = rf'<div v-if="{re.escape(cond)}" class="modal fade show d-block"[^>]*>\s*<motion-icon>'
    pat = rf'<motion-icon>\s*<motion-icon>\s*<div v-if="{re.escape(cond)}" class="modal fade show d-block"[^>]*>'
    return tpl


def apply_replacements(tpl, pairs):
    for a, b in pairs:
        tpl = tpl.replace(a, b)
    return tpl


def migrate_tpl(tpl, name):
    if name == "AgentHostManager.vue":
        tpl = patch_tabs_agent(tpl)
    if name == "PipelinePanel.vue":
        tpl = patch_pipeline_header(tpl)

    tpl = apply_replacements(tpl, BTN_OPEN)
    tpl = apply_replacements(tpl, BADGE_OPEN)
    tpl = apply_replacements(tpl, FORM)
    tpl = apply_replacements(tpl, CARD)
    tpl = fix_button_closes(tpl)
    lines = []
    for line in tpl.split("\n"):
        if "<Badge" in line and "</span>" in line:
            line = line.replace("</span>", "</Badge>", 1)
        lines.append(line)
    tpl = "\n".join(lines)

    # dropdown tailwind
    tpl = tpl.replace(
        'class="dropdown-menu dropdown-menu-end"',
        'class="absolute right-0 z-50 mt-1 min-w-[10rem] rounded-md border border-slate-200 bg-white py-1 shadow-lg"',
    )
    tpl = tpl.replace('class="dropdown-item"', 'class="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"')
    tpl = tpl.replace(
        '<button \n                type="button" \n                class="btn btn-primary btn-sm dropdown-toggle"',
        '<Button \n                type="button" \n                size="sm"',
    )
    tpl = tpl.replace('class="btn btn-primary btn-sm dropdown-toggle"', 'size="sm"')
    tpl = tpl.replace(
        '<label class="btn btn-outline-secondary btn-sm"',
        '<label class="cursor-pointer rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"',
    )
    tpl = tpl.replace('class="btn-check"', 'class="peer sr-only"')
    tpl = tpl.replace('class="btn-group"', 'class="inline-flex rounded-lg border border-slate-200 p-0.5 gap-0.5"')
    tpl = tpl.replace('class="btn-group btn-group-sm w-100"', 'class="flex w-full gap-1"')
    tpl = tpl.replace('class="btn-group btn-group-sm"', 'class="flex gap-1"')

    tpl = tpl.replace(
        'class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);"',
        'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"',
    )
    tpl = tpl.replace('class="modal-dialog modal-lg modal-dialog-scrollable"', 'class="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"')
    tpl = tpl.replace('class="modal-dialog modal-xl modal-dialog-scrollable"', 'class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"')
    tpl = tpl.replace('class="modal-dialog modal-dialog-scrollable"', 'class="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"')
    tpl = tpl.replace('class="modal-content"', 'class="flex min-h-0 flex-1 flex-col"')
    tpl = tpl.replace('class="modal-header"', 'class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3"')
    tpl = tpl.replace('class="modal-title mb-0"', 'class="text-lg font-semibold text-slate-900"')
    tpl = tpl.replace('class="btn-close"', 'class="rounded-md p-2 text-slate-500 hover:bg-slate-100" aria-label="关闭"')
    tpl = tpl.replace('class="modal-body"', 'class="min-h-0 flex-1 overflow-y-auto px-4 py-4"')
    tpl = tpl.replace('class="modal-footer"', 'class="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3"')
    return tpl


def add_imports(text, name):
    if "@/components/ui/button/Button.vue" in text:
        return text
    if name == "AgentHostManager.vue":
        text = text.replace(
            "import HostManager from './HostManager.vue';",
            "import HostManager from './HostManager.vue';\n" + UI_IMPORTS,
        )
        text = text.replace(
            "components: {\n    HostManager\n  },",
            "components: {\n    HostManager,\n    Button, FormDialog, Input, Label, AlertBanner, Badge,\n    Card, CardHeader, CardTitle, CardContent,\n    Table, TableHeader, TableBody, TableRow, TableHead, TableCell,\n    NativeSelect, EmptyState, PageToolbar,\n  },",
        )
    else:
        text = text.replace("import axios", UI_IMPORTS + "import axios", 1)
    return text


def process(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    if not m:
        return
    tpl = migrate_tpl(m.group(1), path.name)
    text = text[: m.start(1)] + tpl + text[m.end(1) :]
    text = add_imports(text, path.name)
    path.write_text(text, encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for n in sys.argv[1:]:
        process(base / n)
