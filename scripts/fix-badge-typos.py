#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def fix_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = re.sub(r'variant="([^"]+)""', r'variant="\1"', text)
    text = re.sub(r'(<Badge[^>]*>[^<]*)</span>', r"\1</Badge>", text)
    text = re.sub(r'variant="outline""', 'variant="outline"', text)
    text = re.sub(r'variant="default""', 'variant="default"', text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print("fixed", path.name)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        fix_file(Path(a))
