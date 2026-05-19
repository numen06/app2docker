#!/usr/bin/env python3
"""Batch Bootstrap -> Tailwind/shadcn template migrations (safe patterns only)."""
import re
import sys
from pathlib import Path

# Import utility migrator from migrate-vue-bootstrap.py
import importlib.util

_util_spec = importlib.util.spec_from_file_location(
    "migrate_vue_bootstrap",
    Path(__file__).resolve().parent / "migrate-vue-bootstrap.py",
)
_util_mod = importlib.util.module_from_spec(_util_spec)
_util_spec.loader.exec_module(_util_mod)
migrate_utils = _util_mod.migrate_template

UI_IMPORTS_SETUP = """import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
"""

BTN_PATTERNS = [
    (r'<button(\s[^>]*?)class="btn btn-outline-danger btn-sm([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-danger([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-danger([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-warning btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-warning([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-warning([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-success btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-success([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-info btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-info([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-info([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-primary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-secondary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-secondary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-secondary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-secondary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-secondary([^"]*)"', r'<Button\1variant="outline"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-primary btn-sm"', r'<Button\1size="sm"'),
    (r'<button(\s[^>]*?)class="btn btn-primary"', r'<Button\1'),
    (r'<button(\s[^>]*?)class="btn btn-info btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-success btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-success btn-lg([^"]*)"', r'<Button\1size="lg"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-light([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-primary([^"]*)"', r'<Button\1size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-link btn-sm([^"]*)"', r'<Button\1variant="ghost" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-link([^"]*)"', r'<Button\1variant="ghost" size="sm"\2"'),
    (r'<button type="button" class="btn-close btn-close-white"', r'<button type="button" class="rounded-md p-2 text-white hover:bg-white/20"'),
    (r'<button type="button" class="btn-close"', r'<button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100"'),
]

BADGE_MAP = [
    ("bg-success", "success"),
    ("bg-danger", "danger"),
    ("bg-warning", "warning"),
    ("bg-info", "info"),
    ("bg-primary", "info"),
    ("bg-secondary", "default"),
]


def migrate_badges(tpl: str) -> str:
    for bg, var in BADGE_MAP:
        tpl = re.sub(
            rf'<span(\s+[^>]*)?\s+class="badge {bg}([^"]*)"([^>]*)>',
            rf'<Badge\1 variant="{var}"\2"\3>',
            tpl,
        )
        tpl = re.sub(
            rf'<span class="badge {bg}([^"]*)"([^>]*)>',
            rf'<Badge variant="{var}"\1"\2>',
            tpl,
        )
    tpl = re.sub(
        r'<span class="badge([^"]*)"([^>]*)>',
        r'<Badge\1"\2>',
        tpl,
    )
    return tpl


def migrate_forms(tpl: str) -> str:
    tpl = tpl.replace(
        'class="form-control form-control-sm"',
        'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"',
    )
    tpl = tpl.replace(
        'class="form-control"',
        'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"',
    )
    tpl = tpl.replace('class="form-label"', 'class="block text-sm font-medium text-slate-700"')
    tpl = tpl.replace(
        'class="form-select form-select-sm"',
        'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"',
    )
    tpl = tpl.replace(
        'class="form-select"',
        'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"',
    )
    tpl = tpl.replace('class="form-check-input"', 'class="h-4 w-4 rounded border-slate-300"')
    tpl = tpl.replace('class="form-check-label"', 'class="text-sm text-slate-700"')
    tpl = tpl.replace('class="form-check mt-4"', 'class="mt-4 flex items-center gap-2"')
    tpl = tpl.replace('class="form-check mb-2"', 'class="mb-2 flex items-center gap-2"')
    tpl = tpl.replace('class="form-check"', 'class="flex items-center gap-2"')
    return tpl


def migrate_tables_spinners(tpl: str) -> str:
    tpl = re.sub(
        r'<table class="table table-sm table-bordered(?: table-hover)?">',
        '<table class="w-full border-collapse text-sm border border-slate-200">',
        tpl,
    )
    tpl = re.sub(
        r'<table class="table table-sm table-bordered table-hover">',
        '<table class="w-full border-collapse text-sm border border-slate-200">',
        tpl,
    )
    tpl = re.sub(
        r'<table class="table table-hover table-sm mb-0">',
        '<table class="w-full border-collapse text-sm">',
        tpl,
    )
    tpl = re.sub(
        r'<table class="table table-sm table-hover">',
        '<table class="w-full border-collapse text-sm">',
        tpl,
    )
    tpl = re.sub(
        r'<table class="table table-hover align-middle mb-0">',
        '<table class="w-full border-collapse text-sm">',
        tpl,
    )
    tpl = re.sub(
        r'<table class="table table-sm table-borderless mb-0">',
        '<table class="w-full border-collapse text-sm">',
        tpl,
    )
    tpl = tpl.replace('<thead class="table-light">', '<thead class="bg-slate-50 text-slate-700">')
    tpl = re.sub(
        r'<span class="spinner-border spinner-border-sm[^"]*"></span>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<motion[^>]*spinner-border[^>]*>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<motion[^>]*spinner-border[^>]*>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<div class="spinner-border spinner-border-sm[^"]*"></motion>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<div class="spinner-border spinner-border-sm[^"]*"></motion>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<div class="spinner-border spinner-border-sm[^"]*"></div>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    tpl = re.sub(
        r'<div class="spinner-border spinner-border-sm"></div>',
        '<i class="fas fa-spinner fa-spin"></i>',
        tpl,
    )
    return tpl


def migrate_alerts_nav(tpl: str) -> str:
    tpl = tpl.replace(
        'class="alert alert-info',
        'class="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900',
    )
    tpl = tpl.replace(
        'class="alert alert-success',
        'class="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800',
    )
    tpl = tpl.replace(
        'class="alert alert-warning',
        'class="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900',
    )
    tpl = tpl.replace(
        'class="alert alert-danger',
        'class="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800',
    )
    tpl = tpl.replace('class="nav-link"', 'class="rounded-md px-4 py-2 text-sm font-medium transition"')
    tpl = tpl.replace('bg-light', 'bg-slate-50')
    return tpl


def fix_button_closes(tpl: str) -> str:
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


def fix_attr_typos(tpl: str) -> str:
    tpl = tpl.replace('size="sm""', 'size="sm"')
    tpl = tpl.replace('size="lg""', 'size="lg"')
    tpl = re.sub(
        r'(<button class="page-link"[^>]*>[\s\S]*?)</Button>',
        r"\1</button>",
        tpl,
    )
    return tpl


def migrate_template(tpl: str) -> str:
    tpl = migrate_utils(tpl)
    for p, r in BTN_PATTERNS:
        tpl = re.sub(p, r, tpl)
    tpl = migrate_badges(tpl)
    tpl = migrate_forms(tpl)
    tpl = migrate_tables_spinners(tpl)
    tpl = migrate_alerts_nav(tpl)
    tpl = fix_button_closes(tpl)
    tpl = fix_attr_typos(tpl)
    return tpl


def add_imports_if_needed(text: str, is_options_api: bool) -> str:
    if "@/components/ui/button/Button.vue" in text:
        return text
    if is_options_api:
        if "components: {" in text:
            text = text.replace(
                "import axios",
                UI_IMPORTS_SETUP + "\nimport axios",
                1,
            )
    else:
        text = text.replace("import axios", UI_IMPORTS_SETUP + "import axios", 1)
    return text


def process(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(<template>)(.*?)(</template>)", text, re.DOTALL)
    if not m:
        print("skip (no template)", path.name)
        return
    new_tpl = migrate_template(m.group(2))
    text = text[: m.start(2)] + new_tpl + text[m.end(2) :]
    is_options = "export default {" in text and "<script setup>" not in text
    text = add_imports_if_needed(text, is_options)
    path.write_text(encoding="utf-8", data=text)
    print("ok", path.name)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        process(Path(arg))
