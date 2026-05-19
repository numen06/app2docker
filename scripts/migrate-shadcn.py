# -*- coding: utf-8 -*-
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

UI_COMPONENTS = """    Button, FormDialog, Input, Label, AlertBanner, Badge,
    Card, CardHeader, CardTitle, CardContent,
    Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
    NativeSelect, EmptyState, PageToolbar,"""


def migrate_buttons(tpl):
    patterns = [
        (r'<button(\s[^>]*?)class="btn btn-outline-danger([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-success([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-warning([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-info([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-secondary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-outline-secondary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-secondary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-secondary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-secondary([^"]*)"', r'<Button\1variant="outline"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-primary btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-primary([^"]*)"', r'<Button\1\2"'),
        (r'<button(\s[^>]*?)class="btn btn-info btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-success btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
        (r'<button(\s[^>]*?)class="btn btn-danger btn-sm([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    ]
    for p, r in patterns:
        tpl = re.sub(p, r, tpl)
    return tpl


def migrate_badges(tpl):
    for bg, var in [
        ("bg-success", "success"), ("bg-danger", "danger"), ("bg-warning", "warning"),
        ("bg-info", "info"), ("bg-primary", "info"), ("bg-secondary", "default"),
    ]:
        tpl = re.sub(
            rf'<span(\s+v-if="[^"]+")?\s+class="badge {bg}([^"]*)"([^>]*)>',
            rf'<Badge\1 variant="{var}"\2"\3>',
            tpl,
        )
    return tpl


def migrate_forms_cards(tpl):
    tpl = tpl.replace('class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"')
    tpl = tpl.replace('class="form-label"', 'class="block text-sm font-medium text-slate-700"')
    tpl = tpl.replace('class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-select"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"')
    tpl = tpl.replace('class="alert alert-info', 'class="rounded-md border border-sky-200 bg-sky-50 text-sky-900 text-sm')
    tpl = tpl.replace('class="alert alert-success', 'class="rounded-md border border-green-200 bg-green-50 text-green-800 text-sm')
    tpl = tpl.replace('class="alert alert-warning', 'class="rounded-md border border-amber-200 bg-amber-50 text-amber-900 text-sm')
    tpl = tpl.replace('class="alert alert-danger', 'class="rounded-md border border-red-200 bg-red-50 text-red-800 text-sm')
    return tpl


def close_buttons(tpl):
    # only close tags that follow Button opens - simple: replace </button> after migration
    # risky for nav-link; convert nav-link buttons first
    tpl = tpl.replace('class="nav-link"', 'class="rounded-md px-4 py-2 text-sm font-medium transition"')
    return tpl


def patch_agent_tabs(tpl):
    ul = '        <ul class="nav nav-tabs nav-tabs-custom mb-0"'
    s = tpl.find(ul)
    if s < 0:
        return tpl
    s = tpl.rfind('    <div class="card mb-3">', 0, s)
    e = tpl.find('    <!-- 主机列表标签页 -->', s)
    new = """    <Card class="mb-3">
      <CardContent class="p-2">
        <div class="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1" role="tablist">
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'hosts' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'hosts'"><i class="fas fa-server mr-1"></i> 主机列表</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'secrets' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'secrets'"><i class="fas fa-key mr-1"></i> 密钥管理</button>
          <button type="button" class="rounded-md px-4 py-2 text-sm font-medium transition" :class="activeTab === 'pending' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'" @click="activeTab = 'pending'"><i class="fas fa-clock mr-1"></i> 待加入主机<Badge v-if="pendingHostsCount > 0" variant="danger" class="ml-1">{{ pendingHostsCount }}</Badge></button>
        </div>
      </CardContent>
    </Card>

"""
    return tpl[:s] + new + tpl[e:]


def fix_button_closes(tpl):
    out = []
    i = 0
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


def process(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    if not m:
        return
    tpl = fix_button_closes(migrate_forms_cards(migrate_badges(migrate_buttons(m.group(1)))))
    if path.name == "AgentHostManager.vue":
        tpl = patch_agent_tabs(tpl)
    text = text[: m.start(1)] + tpl + text[m.end(1) :]

    if "@/components/ui/button/Button.vue" not in text:
        if path.name == "AgentHostManager.vue":
            text = text.replace(
                "import HostManager from './HostManager.vue';",
                "import HostManager from './HostManager.vue';\n" + UI_IMPORTS,
            )
            text = text.replace(
                "components: {\n    HostManager\n  },",
                f"components: {{\n    HostManager,\n{UI_COMPONENTS}\n  }},",
            )
        else:
            text = text.replace("import axios", UI_IMPORTS + "import axios", 1)

    path.write_text(text, encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for n in sys.argv[1:]:
        process(base / n)
