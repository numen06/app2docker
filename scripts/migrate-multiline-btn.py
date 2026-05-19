#!/usr/bin/env python3
"""Replace multiline bootstrap buttons with Button component."""
import re
import sys
from pathlib import Path

BTN_MAP = [
    (r"btn-outline-danger", 'variant="destructive" size="sm"'),
    (r"btn-outline-success", 'variant="outline" size="sm"'),
    (r"btn-outline-warning", 'variant="outline" size="sm"'),
    (r"btn-outline-info", 'variant="outline" size="sm"'),
    (r"btn-outline-primary", 'variant="outline" size="sm"'),
    (r"btn-outline-secondary", 'variant="outline" size="sm"'),
    (r"btn-secondary", 'variant="outline" size="sm"'),
    (r"btn-success", 'size="sm"'),
    (r"btn-danger", 'variant="destructive" size="sm"'),
    (r"btn-info", 'size="sm"'),
    (r"btn-warning", 'size="sm"'),
    (r"btn-primary", ""),
    (r"btn-sm btn-outline-secondary", 'variant="outline" size="sm"'),
    (r"btn-outline-secondary btn-sm", 'variant="outline" size="sm"'),
]


def btn_variant(cls: str) -> str:
    for pat, repl in BTN_MAP:
        if pat in cls:
            return repl
    return 'variant="outline" size="sm"'


def process(text: str) -> str:
    # multiline: <button ... \n class="btn ...
    def repl_multiline(m):
        attrs = m.group(1) or ""
        cls = m.group(2) or ""
        rest = m.group(3) or ""
        variant = btn_variant(cls)
        return f"<Button {attrs}\n  {variant} {rest}".replace("  \n", "\n  ")

    text = re.sub(
        r"<button([^>]*)\n\s*class=\"([^\"]*btn[^\"]*)\"([^>]*)>",
        repl_multiline,
        text,
        flags=re.MULTILINE,
    )

    # single line remaining
    for pat, repl in BTN_MAP:
        text = re.sub(
            rf'<button([^>]*)\s+class="btn {pat}([^"]*)"([^>]*)>',
            rf'<Button\1 {repl}\3>',
            text,
        )
        text = re.sub(
            rf'<button\s+class="btn {pat}([^"]*)"([^>]*)>',
            rf'<Button {repl}\2>',
            text,
        )

    text = text.replace("</button>", "</Button>")
    text = re.sub(r"<span class=\"spinner-border[^\"]*\"[^>]*></span>", '<i class="fas fa-spinner fa-spin"></i>', text)
    text = re.sub(r'class="nav nav-pills[^"]*"', 'class="mb-4 inline-flex w-full rounded-lg border border-slate-200 bg-slate-50 p-1"', text)
    text = re.sub(
        r'class="nav-link(?:\s+active)?"',
        lambda m: 'class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition"',
        text,
    )
    text = text.replace('class="row g-3 mb-3"', 'class="grid grid-cols-1 gap-3 mb-3 md:grid-cols-12"')
    text = text.replace('class="col-md-12"', 'class="md:col-span-12"')
    text = text.replace('class="col-md-6"', 'class="md:col-span-6"')
    text = text.replace('class="col-md-3"', 'class="md:col-span-3"')
    text = text.replace('class="form-text small"', 'class="text-xs text-slate-500 mt-1"')
    text = text.replace('class="form-check-input"', 'class="h-4 w-4 rounded border-slate-300"')
    text = text.replace('class="form-check-label"', 'class="text-sm text-slate-700"')
    return text


def main():
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for name in sys.argv[1:]:
        path = base / name
        text = path.read_text(encoding="utf-8")
        m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
        if not m:
            continue
        new_tpl = process(m.group(1))
        path.write_text(text[: m.start(1)] + new_tpl + text[m.end(1) :], encoding="utf-8")
        print("ok", name)


if __name__ == "__main__":
    main()
