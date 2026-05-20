#!/usr/bin/env python3
"""Second pass: remaining bootstrap patterns."""
import re
import sys
from pathlib import Path

EXTRA_BTN = [
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-success([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-warning([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-secondary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-info([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-danger([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-link([^"]*)"', r'<Button\1variant="ghost" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-primary flex-fill([^"]*)"', r'<Button\1class="flex-1" variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-success ml-2([^"]*)"', r'<Button\1variant="outline" size="sm" class="ml-2"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-sm btn-outline-success([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-success btn-sm flex-fill([^"]*)"', r'<Button\1size="sm" class="flex-1"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-danger btn-sm([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-primary btn-sm([^"]*)"', r'<Button\1size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-success([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-info([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-primary([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-warning([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-outline-danger([^"]*)"', r'<Button\1variant="destructive" size="sm"\2"'),
    (r'<button(\s[^>]*?)class="btn btn-secondary btn-sm([^"]*)"', r'<Button\1variant="outline" size="sm"\2"'),
    (r'<button type="button" class="btn btn-secondary btn-sm([^"]*)"', r'<Button type="button" variant="outline" size="sm"\1"'),
    (r'<button type="button" class="btn btn-primary btn-sm([^"]*)"', r'<Button type="button" size="sm"\1"'),
    (r'<button type="button" class="btn btn-success btn-sm([^"]*)"', r'<Button type="button" size="sm"\1"'),
]

LABEL_BTN = r'''<label class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"'''


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


def process_tpl(tpl):
    for p, r in EXTRA_BTN:
        tpl = re.sub(p, r, tpl)
    tpl = re.sub(
        r'<label class="btn btn-outline-primary([^"]*)"([^>]*)>',
        LABEL_BTN + r"\2>",
        tpl,
    )
    tpl = re.sub(
        r'<label class="btn btn-outline-secondary btn-sm([^"]*)"([^>]*)>',
        r'<label class="inline-flex cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"\2>',
        tpl,
    )
    tpl = re.sub(r'class="form-control form-control-sm font-mono"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 font-mono text-sm"', tpl)
    tpl = re.sub(r'class="form-control font-mono"', 'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-sm"', tpl)
    tpl = re.sub(r'class="form-control mb-2"', 'class="mb-2 flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"', tpl)
    tpl = re.sub(r'class="form-control form-control-sm flex-1"', 'class="flex h-9 flex-1 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"', tpl)
    tpl = re.sub(r'class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"', tpl)
    tpl = re.sub(r'class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"', tpl)
    tpl = re.sub(r'class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"', tpl)
    tpl = re.sub(r'class="form-control-plaintext"', 'class="text-sm text-slate-700"', tpl)
    tpl = re.sub(r'<table class="table table-sm table-hover">', '<table class="w-full border-collapse text-sm">', tpl)
    tpl = re.sub(r'<table class="table table-hover table-sm mb-0">', '<table class="w-full border-collapse text-sm">', tpl)
    tpl = re.sub(r'<table class="table table-sm">', '<table class="w-full border-collapse text-sm">', tpl)
    tpl = re.sub(r'class="spinner-border spinner-border-sm[^"]*"', 'class="fas fa-spinner fa-spin inline-block"', tpl)
    tpl = re.sub(r'<span class="spinner-border[^"]*"></span>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
    tpl = tpl.replace('class="modal fade show d-block"', 'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"')
    tpl = tpl.replace('class="modal fade show block"', 'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"')
    tpl = re.sub(
        r'class="modal fade show"([^>]*)',
        r'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"\1',
        tpl,
    )
    tpl = tpl.replace('class="modal-dialog modal-lg"', 'class="my-8 w-full max-w-3xl"')
    tpl = tpl.replace('class="modal-dialog modal-xl"', 'class="my-8 w-full max-w-5xl"')
    tpl = tpl.replace('class="modal-dialog"', 'class="my-8 w-full max-w-lg"')
    tpl = tpl.replace('class="modal-content"', 'class="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"')
    tpl = tpl.replace('class="modal-header"', 'class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3"')
    tpl = tpl.replace('class="modal-header bg-info text-white"', 'class="flex shrink-0 items-center justify-between border-b border-sky-600 bg-sky-600 px-4 py-3 text-white"')
    tpl = tpl.replace('class="modal-body"', 'class="min-h-0 flex-1 overflow-y-auto px-4 py-4"')
    tpl = tpl.replace('class="modal-footer"', 'class="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3"')
    tpl = tpl.replace('<motion[^>]*modal-backdrop[^>]*>', '')
    tpl = re.sub(r'<div v-if="[^"]+" class="modal-backdrop[^"]*"></div>', '', tpl)
    tpl = fix_button_closes(tpl)
    tpl = tpl.replace('size="sm""', 'size="sm"')
    tpl = re.sub(
        r'(<button class="page-link"[^>]*>[\s\S]*?)</Button>',
        r"\1</button>",
        tpl,
    )
    return tpl


def process(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    if not m:
        return
    text = text[: m.start(1)] + process_tpl(m.group(1)) + text[m.end(1) :]
    path.write_text(text, encoding="utf-8")
    print("pass2", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
