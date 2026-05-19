#!/usr/bin/env python3
import re
import sys
from pathlib import Path

VARIANTS = [
    ("btn-outline-danger", 'variant="destructive" size="sm"'),
    ("btn-outline-success", 'variant="outline" size="sm"'),
    ("btn-outline-warning", 'variant="outline" size="sm"'),
    ("btn-outline-info", 'variant="outline" size="sm"'),
    ("btn-outline-primary", 'variant="outline" size="sm"'),
    ("btn-outline-secondary", 'variant="outline" size="sm"'),
    ("btn-secondary", 'variant="outline" size="sm"'),
    ("btn-success", 'size="sm"'),
    ("btn-danger", 'variant="destructive" size="sm"'),
    ("btn-info", 'size="sm"'),
    ("btn-warning", 'size="sm"'),
    ("btn-primary", ""),
]


def variant_from_class(cls: str) -> str:
    for pat, repl in VARIANTS:
        if pat in cls:
            extra = []
            if "btn-sm" in cls or "btn-sm" in cls:
                if 'size="sm"' not in repl:
                    extra.append('size="sm"')
            if "w-100" in cls or "w-full" in cls:
                extra.append('class="w-full"')
            if "p-1" in cls:
                extra.append('class="h-7 px-2"')
            base = repl if repl else 'variant="default"'
            if extra:
                return base + " " + " ".join(extra)
            return base if repl else 'size="sm"'
    return 'variant="outline" size="sm"'


def process_template(tpl: str) -> str:
    # button with class containing btn
    def repl_btn(m):
        tag = m.group(0)
        cls_m = re.search(r'\bclass="([^"]*)"', tag)
        if not cls_m or "btn" not in cls_m.group(1):
            return tag
        cls = cls_m.group(1)
        variant = variant_from_class(cls)
        inner = re.sub(r'\s*class="[^"]*"', "", tag)
        inner = inner.replace("<button", f"<Button {variant}", 1)
        if not inner.rstrip().endswith(">"):
            inner = inner.rstrip() + ">"
        return inner

    tpl = re.sub(r"<button\b[^>]*>", repl_btn, tpl, flags=re.IGNORECASE | re.DOTALL)

    # :class with btn strings - common pattern
    tpl = tpl.replace("'btn btn-outline-success'", "'border-green-600 bg-green-50 text-green-700'")
    tpl = tpl.replace("'btn btn-outline-secondary'", "'border-slate-300 bg-white text-slate-700'")
    tpl = tpl.replace("'btn btn-success'", "'bg-green-600 text-white'")
    tpl = tpl.replace("'btn btn-outline-success'", "'border-green-600 text-green-700'")

    tpl = tpl.replace('class="modal fade show d-block"', 'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"')
    tpl = tpl.replace('class="modal fade show block"', 'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"')
    tpl = tpl.replace('class="modal fade show"', 'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"')
    tpl = tpl.replace('class="modal fade"', 'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"')
    tpl = tpl.replace("</button>", "</Button>")
    tpl = re.sub(r"<span class=\"spinner-border[^\"]*\"[^>]*>.*?</span>", '<i class="fas fa-spinner fa-spin"></i>', tpl, flags=re.DOTALL)
    tpl = tpl.replace('class="table table-sm table-striped', 'class="w-full text-sm')
    tpl = tpl.replace('class="table table-hover', 'class="w-full')
    tpl = tpl.replace('class="table table-sm', 'class="w-full text-sm')
    tpl = tpl.replace('class="table-light"', 'class="bg-slate-50"')
    return tpl


def main():
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    names = sys.argv[1:] or [
        "AgentHostManager.vue",
        "PipelinePanel.vue",
        "StepBuildPanel.vue",
        "DockerManager.vue",
        "HostManager.vue",
        "DataSourcePanel.vue",
        "BuildConfigEditor.vue",
        "TemplatePanel.vue",
    ]
    for name in names:
        path = base / name
        text = path.read_text(encoding="utf-8")
        m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
        if not m:
            continue
        new_tpl = process_template(m.group(1))
        path.write_text(text[: m.start(1)] + new_tpl + text[m.end(1) :], encoding="utf-8")
        print("fixed", name)


if __name__ == "__main__":
    main()
