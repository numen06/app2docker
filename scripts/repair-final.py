import re
from pathlib import Path

subs = [
    ("? 'btn-primary'", "? 'bg-blue-600 text-white'"),
    (": 'btn-primary'", ": 'bg-blue-600 text-white'"),
    ("? 'btn-outline-primary'", "? 'border border-slate-300 bg-white text-slate-900'"),
    (": 'btn-outline-primary'", ": 'border border-slate-300 bg-white text-slate-900'"),
    ('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"'),
    ('class="modal fade show d-block"', 'class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"'),
    ('class="card-body"', 'class="p-4"'),
    ('class="card mb-3"', 'class="mb-3 rounded-xl border border-slate-200 bg-white shadow-sm"'),
    ('class="btn-group w-full"', 'class="flex w-full gap-1"'),
]

for name in ["AgentHostManager.vue", "PipelinePanel.vue", "StepBuildPanel.vue"]:
    p = Path("frontend/src/components") / name
    t = p.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", t, re.DOTALL)
    tpl = m.group(1)
    for a, b in subs:
        tpl = tpl.replace(a, b)
    p.write_text(t[: m.start(1)] + tpl + t[m.end(1) :], encoding="utf-8")
    print(name)
