#!/usr/bin/env python3
"""Safe Bootstrap utility -> Tailwind migrations for Vue templates."""
import re
import sys
from pathlib import Path

UTIL_MAP = [
    (r"\bd-flex\b", "flex"),
    (r"\bd-block\b", "block"),
    (r"\bd-grid\b", "grid"),
    (r"\bd-md-flex\b", "md:flex"),
    (r"\bflex-column\b", "flex-col"),
    (r"\bflex-wrap\b", "flex-wrap"),
    (r"\bflex-grow-1\b", "flex-1"),
    (r"\bflex-shrink-0\b", "shrink-0"),
    (r"\bjustify-content-between\b", "justify-between"),
    (r"\bjustify-content-center\b", "justify-center"),
    (r"\bjustify-content-end\b", "justify-end"),
    (r"\balign-items-center\b", "items-center"),
    (r"\balign-items-stretch\b", "items-stretch"),
    (r"\balign-items-start\b", "items-start"),
    (r"\balign-items-end\b", "items-end"),
    (r"\btext-muted\b", "text-slate-500"),
    (r"\btext-danger\b", "text-red-500"),
    (r"\btext-success\b", "text-green-600"),
    (r"\btext-primary\b", "text-blue-600"),
    (r"\btext-info\b", "text-sky-600"),
    (r"\btext-warning\b", "text-amber-600"),
    (r"\btext-dark\b", "text-slate-900"),
    (r"\btext-nowrap\b", "whitespace-nowrap"),
    (r"\btext-truncate\b", "truncate"),
    (r"\btext-break\b", "break-all"),
    (r"\btext-decoration-none\b", "no-underline"),
    (r"\bfont-monospace\b", "font-mono"),
    (r"\bw-100\b", "w-full"),
    (r"\bh-100\b", "h-full"),
    (r"\bme-1\b", "mr-1"),
    (r"\bme-2\b", "mr-2"),
    (r"\bme-3\b", "mr-3"),
    (r"\bms-1\b", "ml-1"),
    (r"\bms-2\b", "ml-2"),
    (r"\bms-3\b", "ml-3"),
    (r"\bms-4\b", "ml-4"),
    (r"\bpy-5\b", "py-12"),
    (r"\bborder-top\b", "border-t border-slate-200"),
    (r"\bborder-bottom\b", "border-b border-slate-200"),
    (r"\bposition-relative\b", "relative"),
    (r"\bfa-3x\b", "text-4xl"),
    (r'\bclass="row g-4"', 'class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"'),
    (r'\bclass="row g-3"', 'class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"'),
    (r'\bclass="col-12 col-md-6 col-xl-4"\s*', ""),
    (r"<span\s+class=\"spinner-border(?:\s+spinner-border-sm)?[^\"]*\"\s*></span>", '<i class="fas fa-spinner fa-spin"></i>'),
]


def migrate_template(tpl: str) -> str:
    for pat, repl in UTIL_MAP:
        tpl = re.sub(pat, repl, tpl)
    return tpl


def process_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(<template>)(.*?)(</template>)", text, re.DOTALL)
    if not m:
        return
    new_tpl = migrate_template(m.group(2))
    path.write_text(text[: m.start(2)] + new_tpl + text[m.end(2) :], encoding="utf-8")
    print(f"ok {path}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        process_file(Path(p))
