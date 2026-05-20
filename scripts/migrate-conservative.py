#!/usr/bin/env python3
"""Conservative bootstrap removal without badge migration."""
import importlib.util
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mv", Path(__file__).parent / "migrate-vue-bootstrap.py"
)
_mv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mv)

BTN = [
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-danger[^"]*"', r'<Button\1variant="destructive" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-warning[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-success[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-info[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-primary[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-outline-secondary[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-sm btn-link[^"]*"', r'<Button\1variant="ghost" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-danger[^"]*"', r'<Button\1variant="destructive" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-warning[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-success[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-info[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-primary[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-outline-secondary[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-secondary[^"]*"', r'<Button\1variant="outline" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-primary[^"]*"', r'<Button\1size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-danger[^"]*"', r'<Button\1variant="destructive" size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-info[^"]*"', r'<Button\1size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-success[^"]*"', r'<Button\1size="sm"'),
    (r'<button(\s+[^>]*)class="btn btn-link[^"]*"', r'<Button\1variant="ghost" size="sm"'),
    (r'<button type="button" class="btn btn-secondary[^"]*"', r'<Button type="button" variant="outline" size="sm"'),
    (r'<button type="button" class="btn btn-primary[^"]*"', r'<Button type="button" size="sm"'),
]


def fix_closes(tpl):
    out, i = [], 0
    while True:
        j = tpl.find("<Button", i)
        if j < 0:
            out.append(tpl[i:])
            break
        e = tpl.find("</button>", j)
        if e < 0:
            out.append(tpl[i:])
            break
        out.append(tpl[i:e])
        out.append("</Button>")
        i = e + 9
    return "".join(out)


def migrate(tpl):
    tpl = _mv.migrate_template(tpl)
    for p, r in BTN:
        tpl = re.sub(p, r, tpl)
    tpl = tpl.replace('class="form-control form-control-sm font-mono"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 font-mono text-sm"')
    tpl = tpl.replace('class="form-control form-control-sm flex-1"', 'class="flex h-9 flex-1 rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-control font-mono"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-sm"')
    tpl = tpl.replace('class="form-control mb-2"', 'class="mb-2 flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"')
    tpl = tpl.replace('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"')
    tpl = tpl.replace('class="form-control-plaintext"', 'class="text-sm text-slate-700"')
    tpl = tpl.replace('class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-select form-select-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"')
    tpl = tpl.replace('class="form-select"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"')
    tpl = tpl.replace('class="form-label"', 'class="block text-sm font-medium text-slate-700"')
    tpl = re.sub(r'<table class="table[^"]*">', '<table class="w-full border-collapse text-sm">', tpl)
    tpl = re.sub(r'<span class="spinner-border[^"]*"></span>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
    tpl = re.sub(r'<div class="spinner-border[^"]*"></motion>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
    tpl = re.sub(r'<div class="spinner-border[^"]*"></motion>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
    tpl = tpl.replace('class="modal fade show d-block"', 'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"')
    tpl = re.sub(
        r'class="modal fade show"([^>]*)',
        r'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"\1',
        tpl,
    )
    tpl = tpl.replace('class="modal-dialog modal-xl"', 'class="my-8 w-full max-w-5xl"')
    tpl = tpl.replace('class="modal-dialog modal-lg"', 'class="my-8 w-full max-w-3xl"')
    tpl = tpl.replace('class="modal-dialog"', 'class="my-8 w-full max-w-lg"')
    tpl = tpl.replace('class="modal-content"', 'class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"')
    tpl = tpl.replace('class="modal-header"', 'class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3"')
    tpl = tpl.replace('class="modal-body"', 'class="min-h-0 flex-1 overflow-y-auto px-4 py-4"')
    tpl = tpl.replace('class="modal-footer"', 'class="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3"')
    tpl = tpl.replace('class="btn-close"', 'class="rounded-md p-2 text-slate-500 hover:bg-slate-100"')
    LABEL_TOGGLE = 'class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"'
    tpl = re.sub(r'<label class="btn btn-outline-primary"([^>]*)>', rf"<label {LABEL_TOGGLE}\1>", tpl)
    tpl = re.sub(r'<label class="btn btn-outline-secondary btn-sm"([^>]*)>', rf"<label {LABEL_TOGGLE}\1>", tpl)
    tpl = fix_closes(tpl)
    return tpl


def process(path: Path):
    text = path.read_text(encoding="utf-8")
    ss = text.find("<script")
    s = text.find("<template>") + len("<template>")
    e = text.rfind("</template>", 0, ss)
    text = text[:s] + migrate(text[s:e]) + text[e:]
    if "@/components/ui/button/Button.vue" not in text:
        imp = 'import Button from "@/components/ui/button/Button.vue";\n'
        if "<script setup>" in text:
            text = text.replace("<script setup>\n", f"<script setup>\n{imp}", 1)
        else:
            text = text.replace("import axios", imp + "import axios", 1)
    path.write_text(text, encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
