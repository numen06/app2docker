#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fix_template(tpl: str) -> str:
    tpl = re.sub(r"(<Badge[\s\S]*?)</span>", r"\1</Badge>", tpl)
    tpl = re.sub(
        r"<span\s+(v-[^>]*)\s+variant=\"([^\"]+)\"([^>]*)>",
        r'<Badge \1 variant="\2"\3>',
        tpl,
    )
    tpl = tpl.replace('class="badge"', 'variant="default"')
    tpl = re.sub(r':class="getProjectTypeBadgeClass[^"]*"', "", tpl)
    return tpl


def process(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    script_start = text.find("<script")
    tpl_start = text.find("<template>") + len("<template>")
    tpl_end = text.rfind("</template>", 0, script_start)
    tpl = fix_template(text[tpl_start:tpl_end])
    path.write_text(text[:tpl_start] + tpl + text[tpl_end:], encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
