#!/usr/bin/env python3
"""Fix common migration HTML typos in Vue templates."""
import re
import sys
from pathlib import Path

FIXES = [
    (r"</motion>", "</div>"),
    (r"<motion\b", "<div"),
    (r'(<Badge\b[^>]*>[\s\S]*?)</span>', r"\1</Badge>"),
    (r'variant="info" class="ml-1">\s*\n\s*(\{\{)', r'variant="info" class="ml-1">\n                  \1"),
]


def process(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    for pat, repl in FIXES:
        text = re.sub(pat, repl, text)
    # span with variant= attr (broken badge migration)
    text = re.sub(
        r"<span\s+v-else-if=\"([^\"]+)\"\s+variant=\"([^\"]+)\" class=\"([^\"]+)\"\s*>",
        r'<Badge v-else-if="\1" variant="\2" class="\3">',
        text,
    )
    text = re.sub(
        r"</span>\s*\n\s*<Badge",
        "</Badge>\n                  <Badge",
        text,
    )
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print("fixed", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        process(Path(a))
