#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components"
FILES = ["PipelinePanel.vue", "DataSourcePanel.vue", "BuildConfigEditor.vue"]


def fix(text: str) -> str:
    # @click.self="..." newline spaces <motion.div  -> add >
    text = re.sub(
        r'(@click\.self="[^"]+")\s*\n(\s*)<div',
        r'\1\n\2>\n\2<div',
        text,
    )
    return text


def main():
    for name in FILES:
        p = ROOT / name
        t = p.read_text(encoding="utf-8")
        n = fix(t)
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("fixed", name)


if __name__ == "__main__":
    main()
