# -*- coding: utf-8 -*-
import re
from pathlib import Path

FILES = ["AgentHostManager.vue", "PipelinePanel.vue", "StepBuildPanel.vue"]

BTN_MULTI = [
    (r"<button\s+class=\"btn btn-outline-success\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-outline-info\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-outline-primary\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-outline-danger\"", "<Button variant=\"destructive\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-outline-warning\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-outline-secondary\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-primary btn-sm\"", "<Button size=\"sm\""),
    (r"<button\s+class=\"btn btn-primary\"", "<Button"),
    (r"<button\s+class=\"btn btn-sm btn-outline-secondary\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-sm btn-outline-info\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-sm btn-outline-warning\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-sm btn-outline-success\"", "<Button variant=\"outline\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-sm btn-outline-danger\"", "<Button variant=\"destructive\" size=\"sm\""),
    (r"<button\s+class=\"btn btn-link btn-sm p-0\"", "<button class=\"text-sm text-blue-600 hover:underline p-0\""),
    (r"<button\s+class=\"btn btn-sm btn-link[^\"]*\"", "<button class=\"text-sm text-blue-600 hover:underline p-0\""),
    (r"<label\s+class=\"btn btn-outline-primary\"", "<label class=\"cursor-pointer rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50\""),
    (r"<span\s+:class=\"secret\.enabled \? 'badge bg-success' : 'badge bg-secondary'\"", "<Badge :variant=\"secret.enabled ? 'success' : 'default'\""),
    (r"<span v-if=\"host\.docker_info\.version\" class=\"badge bg-info\"", "<Badge v-if=\"host.docker_info.version\" variant=\"info\""),
    (r"<span class=\"badge bg-info ml-2\"", "<Badge variant=\"info\" class=\"ml-2\""),
    (r"<span class=\"badge bg-success\"", "<Badge variant=\"success\""),
    (r"<span class=\"spinner-border spinner-border-sm\"", "<i class=\"fas fa-spinner fa-spin\""),
    (r"<span class=\"spinner-border\"", "<i class=\"fas fa-spinner fa-spin\""),
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


def process(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
    tpl = m.group(1)
    for p, r in BTN_MULTI:
        tpl = re.sub(p, r, tpl)
    tpl = fix_btn_close(tpl)
    tpl = re.sub(r"(<Badge[^>]*>)(.*?)</span>", r"\1\2</Badge>", tpl, flags=re.DOTALL)
    path.write_text(text[: m.start(1)] + tpl + text[m.end(1) :], encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for f in FILES:
        process(base / f)
