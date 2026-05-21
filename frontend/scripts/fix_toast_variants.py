#!/usr/bin/env python3
"""Fix misclassified toastInfo after migrate_alerts.py."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"

REPLACEMENTS = [
    (r"toastInfo\(error\.response\?\.", "toastApiError(error, "),
    (r"toastInfo\(err\.response\?\.", "toastApiError(err, "),
    (r"toastInfo\(e\.response\?\.", "toastApiError(e, "),
    (r'toastInfo\(this\.editingHost \? "主机更新成功" : "主机添加成功"\)', 'toastSuccess(this.editingHost ? "主机更新成功" : "主机添加成功")'),
    (r"toastInfo\(this\.editingHost \? '主机更新成功' : '主机创建成功'\)", "toastSuccess(this.editingHost ? '主机更新成功' : '主机创建成功')"),
]

# toastInfo("...失败...") -> toastError - only when literal starts with failure context
FAILURE_LITERAL = re.compile(
    r'toastInfo\((["\`])([^"\`]*失败[^"\`]*)\1\)'
)


def ensure_api_error_import(content: str) -> str:
    if "toastApiError(" not in content:
        return content
    imp = 'import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";'
    old = 'import { toastSuccess, toastError, toastInfo } from "@/utils/notify";'
    if old in content:
        return content.replace(old, imp)
    if imp not in content and "from \"@/utils/notify\"" in content:
        content = re.sub(
            r'import \{([^}]+)\} from "@/utils/notify";',
            lambda m: imp if "toastApiError" not in m.group(1) else m.group(0),
            content,
            count=1,
        )
    return content


def main():
    for path in ROOT.rglob("*"):
        if path.suffix not in (".vue", ".js"):
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for pat, repl in REPLACEMENTS:
            text = re.sub(pat, repl, text)

        def fail_repl(m):
            return f"toastError({m.group(1)}{m.group(2)}{m.group(1)})"

        text = FAILURE_LITERAL.sub(fail_repl, text)

        # ternary copy ok/fail
        text = text.replace(
            'toastInfo(ok ? "Webhook URL 已复制" : "复制失败")',
            'ok ? toastSuccess("Webhook URL 已复制") : toastError("复制失败")',
        )
        text = text.replace(
            'toastInfo(success ? "日志已复制到剪贴板" : "复制失败，请手动选择文本复制")',
            'success ? toastSuccess("日志已复制到剪贴板") : toastError("复制失败，请手动选择文本复制")',
        )
        text = text.replace(
            "toastInfo(typeof detail === \"string\" ? detail : \"转移所有权失败\")",
            "toastApiError({ response: { data: { detail } } }, \"转移所有权失败\")",
        )
        # simpler for typeof detail patterns
        for msg in (
            "转移所有权失败", "保存失败", "更新角色失败", "移除失败",
        ):
            text = text.replace(
                f'toastInfo(typeof detail === "string" ? detail : "{msg}")',
                f'toastError(typeof detail === "string" ? detail : "{msg}")',
            )

        text = ensure_api_error_import(text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            print(path.relative_to(ROOT.parent))


if __name__ == "__main__":
    main()
