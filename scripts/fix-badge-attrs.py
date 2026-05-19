#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fix_badges(text: str) -> str:
    # variant="x" mr-1 mb-1" -> variant="x" class="mr-1 mb-1"
    text = re.sub(
        r'(<Badge\b[^>]*?\bvariant="[^"]+")\s+((?:mr|ml|mb|mt|text|flex)[-\w\s]*)(?="?\s*>)',
        lambda m: f'{m.group(1)} class="{m.group(2).strip()}"',
        text,
    )
    # unclosed class on Badge (missing closing quote before >)
    text = re.sub(
        r'(<Badge[^>]*class="[^"]*)\s*>',
        r'\1">',
        text,
    )
    return text


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        t = p.read_text(encoding="utf-8")
        n = fix_badges(t)
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("ok", p.name)
