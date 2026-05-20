#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fix(tpl: str) -> str:
    tpl = re.sub(r">([^<\n]+)</span\s*\n\s*>", r">\1</Badge>", tpl)
    tpl = re.sub(r">([^<\n]+)</span\s*>", r">\1</Badge>", tpl)
    tpl = re.sub(r"</span\s*\n\s*>", "</Badge>", tpl)
    return tpl


def process(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    script_start = text.find("<script")
    tpl_start = text.find("<template>") + len("<template>")
    tpl_end = text.rfind("</template>", 0, script_start)
    tpl = fix(text[tpl_start:tpl_end])
    path.write_text(text[:tpl_start] + tpl + text[tpl_end:], encoding="utf-8")
    print("ok", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
