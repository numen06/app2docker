# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

FILES = [
    "AgentHostManager.vue",
    "PipelinePanel.vue",
    "StepBuildPanel.vue",
]


def repair(tpl):
    # double quotes after variant
    tpl = re.sub(r'variant="(\w+)""', r'variant="\1"', tpl)
    tpl = re.sub(r'variant="outline""', 'variant="outline"', tpl)

    # orphan variant on elements (broken badge migration)
    tpl = re.sub(
        r'(\s+)(v-if="[^"]+")\s+variant="(\w+)"(\s*")?',
        r'\1<Badge \2 variant="\3"\4>',
        tpl,
    )

    # Badge with extra attrs like ml-1 outside class
    tpl = re.sub(
        r'<Badge([^>]*?) variant="(\w+)"\s+(ml-\d+|mr-\d+)"',
        r'<Badge\1 variant="\2" class="\3"',
        tpl,
    )

    # </span> after Badge content - fix paired
    tpl = re.sub(r"(<Badge[^>]*>[\s\S]*?)</span>", r"\1</Badge>", tpl)

    # remaining badge spans
    for bg, var in [
        ("bg-success", "success"), ("bg-danger", "danger"), ("bg-warning", "warning"),
        ("bg-info", "info"), ("bg-primary", "info"), ("bg-secondary", "default"),
    ]:
        tpl = re.sub(
            rf'<span([^>]*)class="badge {bg}([^"]*)"([^>]*)>',
            rf'<Badge\1variant="{var}"\2\3>',
            tpl,
        )

    # broken Button from btn-primary btn-sm
    tpl = tpl.replace('size="sm" dropdown-toggle"', 'size="sm"')
    tpl = re.sub(
        r'<Button\s+type="button"\s+size="sm"\s*:class',
        '<Button type="button" size="sm" :class',
        tpl,
    )

    # label buttons for filter -> tailwind segmented
    tpl = tpl.replace('class="btn btn-outline-secondary btn-sm"', 'class="cursor-pointer rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"')

    return tpl


def process(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    if not m:
        return
    tpl = repair(m.group(1))
    path.write_text(text[: m.start(1)] + tpl + text[m.end(1) :], encoding="utf-8")
    print("repaired", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for n in FILES:
        process(base / n)
