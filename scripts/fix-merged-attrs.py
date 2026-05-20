#!/usr/bin/env python3
import re
import sys
from pathlib import Path

SUFFIX_MAP = {
    "ml-1": "ml-1",
    "ml-2": "ml-2",
    "mr-1": "mr-1",
    "mr-2": "mr-2",
    "flex-fill": "flex-1",
    "w-full": "w-full",
}


def fix(text: str) -> str:
    for suf, cls in SUFFIX_MAP.items():
        text = re.sub(
            rf'(variant="[^"]+"|size="[^"]+") {re.escape(suf)}"',
            rf'\1 class="{cls}"',
            text,
        )
    text = re.sub(
        r'class="badge bg-(\w+)(?:\s+ml-1)?"',
        lambda m: f'variant="{"success" if m.group(1)=="success" else "info" if m.group(1) in ("info","primary") else "default"}" class="ml-1"'
        if "ml-1" in m.group(0)
        else f'variant="default"',
        text,
    )
    # leftover badge classes on span
    text = text.replace('class="badge ', 'class="rounded px-2 py-0.5 text-xs ')
    return text


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        t = p.read_text(encoding="utf-8")
        n = fix(t)
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("ok", p.name)
