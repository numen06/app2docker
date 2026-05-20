#!/usr/bin/env python3
"""Fix <Button ...\n  <i patterns missing > before children."""
import re
from pathlib import Path

def fix_tpl(tpl: str) -> str:
    # Insert > before child if Button tag spans lines without closing >
    def fix_block(m):
        block = m.group(0)
        if block.rstrip().endswith(">"):
            return block
        # insert > before first child tag
        return re.sub(r"(\n\s*)(<(?:i|span|div|strong|code|slot))", r">\1\2", block, count=1)

    return re.sub(
        r"<Button\b(?:\s[^>]*)*(?:\n\s*[^<\n]+)*",
        fix_block,
        tpl,
        flags=re.MULTILINE,
    )


def main():
    base = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
    for path in base.glob("*.vue"):
        text = path.read_text(encoding="utf-8")
        m = re.search(r"<template>(.*?)</template>", text, re.DOTALL)
        if not m:
            continue
        new_tpl = fix_tpl(m.group(1))
        if new_tpl != m.group(1):
            path.write_text(text[: m.start(1)] + new_tpl + text[m.end(1) :], encoding="utf-8")
            print("fixed", path.name)


if __name__ == "__main__":
    main()
