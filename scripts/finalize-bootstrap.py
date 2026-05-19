#!/usr/bin/env python3
"""Final cleanup for remaining bootstrap class strings."""
import re
import sys
from pathlib import Path

REPLACEMENTS = [
    ('class="btn btn-outline-primary flex-fill"', 'class="flex-1 inline-flex cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"'),
    ('class="btn btn-outline-primary"', 'class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"'),
    ('class="table table-sm table-hover"', 'class="w-full border-collapse text-sm"'),
    ('class="table table-hover table-sm mb-0"', 'class="w-full border-collapse text-sm"'),
    ('class="table table-sm"', 'class="w-full border-collapse text-sm"'),
    ('class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"'),
    ('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"'),
    ('class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"'),
    ('class="form-control-plaintext"', 'class="text-sm text-slate-700"'),
    ('class="modal fade show d-block"', 'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"'),
    ('<span class="spinner-border spinner-border-sm"></span>', '<i class="fas fa-spinner fa-spin"></i>'),
    ('<span class="spinner-border spinner-border-sm me-1"></span>', '<i class="fas fa-spinner fa-spin mr-1"></i>'),
    ('<span class="spinner-border spinner-border-sm me-2"></span>', '<i class="fas fa-spinner fa-spin mr-2"></i>'),
    ('<div class="spinner-border spinner-border-sm me-2"></motion>', '<i class="fas fa-spinner fa-spin mr-2"></i>'),
    ('<div class="spinner-border spinner-border-sm me-2"></motion>', '<i class="fas fa-spinner fa-spin mr-2"></i>'),
]

BTN_SUBS = [
    (r'<button class="btn btn-primary btn-sm"', r'<Button size="sm"'),
    (r'<button type="button" class="btn btn-secondary btn-sm"', r'<Button type="button" variant="outline" size="sm"'),
    (r'<button type="button" class="btn btn-primary btn-sm"', r'<Button type="button" size="sm"'),
    (r'<button type="button" class="btn btn-success btn-sm"', r'<Button type="button" size="sm"'),
    (r'<button class="btn btn-sm btn-outline-secondary"', r'<Button variant="outline" size="sm"'),
    (r'<button class="btn btn-sm btn-outline-primary"', r'<Button variant="outline" size="sm"'),
    (r'<button class="btn btn-sm btn-outline-secondary ms-2"', r'<Button variant="outline" size="sm" class="ml-2"'),
    (r'class="btn btn-outline-success"', 'variant="outline" size="sm" TEMP_BTN'),
    (r'class="btn btn-outline-warning"', 'variant="outline" size="sm" TEMP_BTN'),
    (r'class="btn btn-outline-info"', 'variant="outline" size="sm" TEMP_BTN'),
    (r'class="btn btn-outline-primary"', 'variant="outline" size="sm" TEMP_BTN'),
    (r'class="btn btn-outline-danger"', 'variant="destructive" size="sm" TEMP_BTN'),
    (r'class="btn btn-success btn-sm flex-fill"', 'size="sm" class="flex-1" TEMP_BTN'),
    (r'class="btn btn-danger btn-sm"', 'variant="destructive" size="sm" TEMP_BTN'),
    (r'class="btn btn-sm btn-link text-decoration-none ms-1 p-0"', 'variant="ghost" size="sm" class="ml-1 p-0" TEMP_BTN'),
]

def fix_buttons(tpl):
    for p, r in BTN_SUBS:
        if "TEMP_BTN" in r:
            tpl = tpl.replace(f'<button {p.split("class=")[1]}', f'<Button {r}')
            continue
        tpl = tpl.replace(p, r)
    # buttons with class attr in middle
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-outline-success"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-outline-warning"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-outline-info"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-outline-primary"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-outline-danger"([^>]*)>',
        r'<Button\1variant="destructive" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-success btn-sm flex-fill"([^>]*)>',
        r'<Button\1size="sm" class="flex-1"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-danger btn-sm"([^>]*)>',
        r'<Button\1variant="destructive" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-sm btn-link[^"]*"([^>]*)>',
        r'<Button\1variant="ghost" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-primary btn-sm"([^>]*)>',
        r'<Button\1size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-sm btn-outline-secondary"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button(\s+[^>]*?)class="btn btn-sm btn-outline-primary"([^>]*)>',
        r'<Button\1variant="outline" size="sm"\2>',
        tpl,
    )
    tpl = re.sub(
        r'<button type="button" class="btn btn-secondary btn-sm"([^>]*)>',
        r'<Button type="button" variant="outline" size="sm"\1>',
        tpl,
    )
    tpl = re.sub(
        r'<button type="button" class="btn btn-primary btn-sm"([^>]*)>',
        r'<Button type="button" size="sm"\1>',
        tpl,
    )
    tpl = re.sub(
        r'<button type="button" class="btn btn-success btn-sm"([^>]*)>',
        r'<Button type="button" size="sm"\1>',
        tpl,
    )
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


def process(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    if not m:
        return
    tpl = m.group(1)
    for a, b in REPLACEMENTS:
        tpl = tpl.replace(a, b)
    tpl = fix_buttons(tpl)
    text = text[: m.start(1)] + tpl + text[m.end(1) :]
    if path.name == "AgentHostManager.vue" and "Button," not in text:
        text = text.replace(
            "components: {\n    HostManager\n  },",
            """components: {
    HostManager,
    Button, Input, Label, Badge, FormDialog, BaseDialog, NativeSelect,
    PageToolbar, PaginationBar, EmptyState, AlertBanner,
    Card, CardContent,
    Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  },""",
        )
        if "import Card from" not in text:
            text = text.replace(
                'import TableCell from "@/components/ui/table/TableCell.vue";',
                'import TableCell from "@/components/ui/table/TableCell.vue";\nimport Card from "@/components/ui/card/Card.vue";\nimport CardContent from "@/components/ui/card/CardContent.vue";',
            )
    path.write_text(text, encoding="utf-8")
    print("finalize", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
