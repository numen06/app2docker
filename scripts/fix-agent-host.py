#!/usr/bin/env python3
import re
from pathlib import Path

p = Path("frontend/src/components/AgentHostManager.vue")
text = p.read_text(encoding="utf-8")
script_start = text.find("<script")
tpl_start = text.find("<template>") + len("<template>")
tpl_end = text.rfind("</template>", 0, script_start)
tpl = text[tpl_start:tpl_end]
m = type("M", (), {"start": lambda self, n: tpl_start, "end": lambda self, n: tpl_end})()

LABEL_TOGGLE = (
    'class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md '
    "border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 "
    'has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700"'
)

# Labels first (radio toggles)
tpl = re.sub(
    r'<label\s+class="btn btn-outline-primary"',
    f"<label {LABEL_TOGGLE}",
    tpl,
)

ATTR_MAP = {
    'class="btn btn-outline-info"': 'variant="outline" size="sm"',
    'class="btn btn-outline-primary"': 'variant="outline" size="sm"',
    'class="btn btn-outline-success"': 'variant="outline" size="sm"',
    'class="btn btn-outline-warning"': 'variant="outline" size="sm"',
    'class="btn btn-outline-danger"': 'variant="destructive" size="sm"',
    'class="btn btn-primary btn-sm"': 'size="sm"',
    'class="btn btn-success btn-sm flex-fill"': 'size="sm" class="flex-1"',
    'class="btn btn-danger btn-sm"': 'variant="destructive" size="sm"',
    'class="btn btn-sm btn-outline-secondary"': 'variant="outline" size="sm"',
    'class="btn btn-sm btn-outline-primary"': 'variant="outline" size="sm"',
    'class="btn btn-sm btn-outline-info"': 'variant="outline" size="sm"',
    'class="btn btn-sm btn-link text-decoration-none ms-1 p-0"': 'variant="ghost" size="sm" class="ml-1 p-0"',
    'class="btn btn-secondary btn-sm"': 'variant="outline" size="sm"',
    'class="btn btn-success btn-sm"': 'size="sm"',
    'class="btn btn-sm btn-outline-secondary ms-2"': 'variant="outline" size="sm" class="ml-2"',
}

before = tpl.count("btn btn-")
for old, new in ATTR_MAP.items():
    tpl = tpl.replace(old, new)
print(f"btn count before {before} after {tpl.count('btn btn-')}")

for a, b in [
    ('class="table table-hover table-sm mb-0"', 'class="w-full border-collapse text-sm"'),
    ('class="table table-sm"', 'class="w-full border-collapse text-sm"'),
    ('class="form-control form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"'),
    ('class="form-control"', 'class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"'),
    ('class="form-select form-control-sm"', 'class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm"'),
    ('class="form-control-plaintext"', 'class="text-sm text-slate-700"'),
]:
    tpl = tpl.replace(a, b)

tpl = tpl.replace(
    'class="modal fade show d-block"',
    'class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"',
)
tpl = re.sub(r'<span class="spinner-border[^"]*"></span>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
tpl = re.sub(r'<motion[^>]*spinner-border[^>]*></motion>', '<i class="fas fa-spinner fa-spin"></i>', tpl)
tpl = re.sub(r'<div class="spinner-border[^"]*"></div>', '<i class="fas fa-spinner fa-spin"></i>', tpl)

# button -> Button where we converted attrs
tpl = re.sub(r"<button\b", "<Button", tpl)
tpl = re.sub(r"</button>", "</Button>", tpl)
# page-link and other native buttons: revert if needed - check for page-link
tpl = tpl.replace('<Button class="page-link"', '<button class="rounded border border-slate-200 px-2 py-1 text-sm hover:bg-slate-50"')
tpl = tpl.replace("</Button>\n          </li>", "</button>\n          </li>")  # only if page-link - fragile

text = text[:tpl_start] + tpl + text[tpl_end:]
p.write_text(text, encoding="utf-8")
print("fixed AgentHostManager v2")
