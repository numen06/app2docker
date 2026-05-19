# -*- coding: utf-8 -*-
from pathlib import Path

FILES = [
    "AgentHostManager.vue",
    "PipelinePanel.vue",
    "StepBuildPanel.vue",
]

BADGE_MORE = [
    ('<span v-if="host.has_private_key" class="badge bg-info ml-1">', '<Badge v-if="host.has_private_key" variant="info" class="ml-1">'),
    ('<span v-else-if="host.has_password" class="badge bg-secondary ml-1">', '<Badge v-else-if="host.has_password" variant="default" class="ml-1">'),
    ('class="badge bg-info ml-1"', 'variant="info" class="ml-1"'),
    ('class="badge bg-primary ml-1"', 'variant="info" class="ml-1"'),
    ('class="badge bg-secondary ml-1"', 'variant="default" class="ml-1"'),
    ('class="badge bg-secondary" style', 'variant="default" style'),
    ('<span class="badge bg-secondary"', '<Badge variant="default"'),
    ('<span class="badge bg-info"', '<Badge variant="info"'),
    ('<span class="badge bg-warning"', '<Badge variant="warning"'),
    ('<span class="badge bg-success"', '<Badge variant="success"'),
    ('<span class="badge bg-danger"', '<Badge variant="danger"'),
    ('<span class="badge bg-primary"', '<Badge variant="info"'),
    ('class="spinner-border spinner-border-sm', 'class="fas fa-spinner fa-spin'),
    ('<div class="card mb-3">', '<Card class="mb-3">'),
    ('<motion-icon>', ''),
]

def fix_btn_close(tpl):
    while True:
        i = tpl.find("<Button")
        if i < 0:
            break
        e = tpl.find("</button>", i)
        if e < 0:
            break
        tpl = tpl[:e] + "</Button>" + tpl[e + 9 :]
    return tpl


def fix_badge_line_closes(tpl):
    lines = []
    for line in tpl.split("\n"):
        if "<Badge" in line and "</span>" in line:
            line = line.replace("</span>", "</Badge>")
        lines.append(line)
    return "\n".join(lines)


def process(path):
    text = path.read_text(encoding="utf-8")
    import re
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    tpl = m.group(1)
    for a, b in BADGE_MORE:
        tpl = tpl.replace(a, b)
    tpl = fix_btn_close(tpl)
    tpl = fix_badge_line_closes(tpl)
    tpl = tpl.replace('class="btn-group btn-group-sm w-full"', 'class="flex w-full gap-1"')
    tpl = tpl.replace('class="btn-group btn-group-sm"', 'class="flex gap-1"')
    tpl = tpl.replace('class="btn-group filter-dropdown-group"', 'class="relative"')
    tpl = tpl.replace('class="card-body py-2 filter-card-body"', 'class="py-2"')
    path.write_text(text[: m.start(1)] + tpl + text[m.end(1) :], encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for f in FILES:
        process(base / f)
