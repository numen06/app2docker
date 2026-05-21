#!/usr/bin/env python3
"""Fix broken toastApiError from bad regex replace."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"

# toastApiError(err, data?.detail || "msg") -> toastApiError(err, "msg")
PAT = re.compile(
    r"toastApiError\((\w+),\s*data\?\.\w+\s*\|\|\s*"
)


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "toastApiError(" not in text or "data?." not in text:
        return False

    def replacer(m):
        start = m.start()
        # find opening paren of toastApiError
        i = m.end()
        depth = 0
        args_start = text.find("(", start) + 1
        err_var = m.group(1)
        # parse from after err_var comma
        i = text.find(",", start) + 1
        depth = 0
        in_str = None
        escape = False
        fallback_parts = []
        while i < len(text):
            c = text[i]
            if in_str:
                fallback_parts.append(c)
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == in_str:
                    in_str = None
                i += 1
                continue
            if c in ("'", '"', "`"):
                in_str = c
                fallback_parts.append(c)
                i += 1
                continue
            if c == "(":
                depth += 1
                fallback_parts.append(c)
            elif c == ")":
                if depth == 0:
                    fallback = "".join(fallback_parts).strip()
                    # strip leading data?.xxx ||
                    fallback = re.sub(
                        r"^data\?\.\w+\s*\|\|\s*",
                        "",
                        fallback,
                    )
                    return f"toastApiError({err_var}, {fallback})"
                depth -= 1
                fallback_parts.append(c)
            else:
                fallback_parts.append(c)
            i += 1
        return m.group(0)

    # Simpler: replace known broken prefix
    new = re.sub(
        r"toastApiError\((\w+),\s*data\?\.\w+\s*\|\|\s*",
        r"toastApiError(\1, ",
        text,
    )
    # TeamSettings hack
    new = new.replace(
        'toastApiError({ response: { data: { detail } } }, "转移所有权失败")',
        'toastError(typeof detail === "string" ? detail : "转移所有权失败")',
    )
    # TemplateEditorModal - simplify second arg
    new = re.sub(
        r'toastApiError\(error, data\?\.detail \|\| error\.response\?\.data\?\.error \|\| error\.message \|\| "保存失败"\)',
        'toastApiError(error, "保存失败")',
        new,
    )
    new = re.sub(
        r'toastApiError\(err, data\?\.error \|\| err\.message \|\| "([^"]+)"\)',
        r'toastApiError(err, "\1")',
        new,
    )
    new = re.sub(
        r'toastApiError\(err, data\?\.detail \|\| err\.message \|\| "([^"]+)"\)',
        r'toastApiError(err, "\1")',
        new,
    )

    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main():
    for path in ROOT.rglob("*"):
        if path.suffix in (".vue", ".js") and fix_file(path):
            print(path.relative_to(ROOT.parent))


if __name__ == "__main__":
    main()
